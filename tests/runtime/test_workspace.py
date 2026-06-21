"""Unit tests for WorkspaceAccessor (RCP-A11, RCP-A12).

Tests use injectable git_runner (no real subprocess) and tmp_path (no real FS paths needed).

Coverage:
  - git_status() calls git subprocess and parses output correctly
  - list_files() returns files, excludes cage internals
  - list_files("../../etc") → PathEscape (403)
  - list_files("valid/subdir") → returns files in subdir only
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from server.runtime.errors import ERR_PATH_ESCAPE, RuntimeApiError
from server.runtime.workspace import GitStatus, WorkspaceAccessor, _CAGE_INTERNALS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_git_runner(outputs: dict[tuple, str]):
    """Return a fake async git runner that returns pre-canned outputs.

    outputs maps (first_arg_after_git,) → str output.
    E.g. {("branch",): "main", ("status",): ""}
    """
    async def _runner(args: list[str], cwd: Path) -> str:
        # Match on the git subcommand (second element, first is "git")
        subcommand = args[1] if len(args) > 1 else ""
        return outputs.get((subcommand,), "")
    return _runner


# ---------------------------------------------------------------------------
# git_status() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_status_parses_clean(tmp_path):
    """git_status() returns correct GitStatus for a clean repo."""
    runner = _make_git_runner({
        ("branch",): "main",
        ("status",): "",
        ("log",): "abc123def456",
    })
    accessor = WorkspaceAccessor(workspace_root=tmp_path, git_runner=runner)

    status = await accessor.git_status()

    assert status.branch == "main"
    assert status.dirty is False
    assert status.changed_files == []
    assert status.last_commit == "abc123def456"


@pytest.mark.asyncio
async def test_git_status_parses_dirty(tmp_path):
    """git_status() returns dirty=True and changed_files when there are modifications."""
    runner = _make_git_runner({
        ("branch",): "feature/x",
        ("status",): " M src/app.py\n?? newfile.txt\n",
        ("log",): "deadbeef1234",
    })
    accessor = WorkspaceAccessor(workspace_root=tmp_path, git_runner=runner)

    status = await accessor.git_status()

    assert status.branch == "feature/x"
    assert status.dirty is True
    assert "src/app.py" in status.changed_files
    assert "newfile.txt" in status.changed_files
    assert status.last_commit == "deadbeef1234"


@pytest.mark.asyncio
async def test_git_status_no_commit(tmp_path):
    """git_status() handles empty last_commit (new repo)."""
    runner = _make_git_runner({
        ("branch",): "main",
        ("status",): "",
        ("log",): "",
    })
    accessor = WorkspaceAccessor(workspace_root=tmp_path, git_runner=runner)

    status = await accessor.git_status()

    assert status.last_commit is None


@pytest.mark.asyncio
async def test_git_status_empty_branch(tmp_path):
    """git_status() handles empty branch gracefully (detached HEAD)."""
    runner = _make_git_runner({
        ("branch",): "",
        ("status",): "",
        ("log",): "abc",
    })
    accessor = WorkspaceAccessor(workspace_root=tmp_path, git_runner=runner)

    status = await accessor.git_status()

    assert status.branch == ""
    assert isinstance(status, GitStatus)


# ---------------------------------------------------------------------------
# list_files() tests
# ---------------------------------------------------------------------------


def _setup_workspace(root: Path):
    """Create a simple workspace structure for file listing tests."""
    (root / "README.md").write_text("readme")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("app")
    (root / "src" / "utils.py").write_text("utils")
    (root / "subdir").mkdir()
    (root / "subdir" / "nested.txt").write_text("nested")
    (root / "subdir" / "deep").mkdir()
    (root / "subdir" / "deep" / "file.py").write_text("deep")
    # Cage internals — should be excluded
    for internal in _CAGE_INTERNALS:
        (root / internal).write_text("internal")


def test_list_files_returns_all(tmp_path):
    """list_files() returns all files (no cage internals)."""
    _setup_workspace(tmp_path)
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    entries = accessor.list_files()
    paths = {e["path"] for e in entries}

    assert "README.md" in paths
    assert "src/app.py" in paths
    assert "src/utils.py" in paths
    assert "subdir/nested.txt" in paths


def test_list_files_excludes_cage_internals(tmp_path):
    """list_files() never returns cage internal files."""
    _setup_workspace(tmp_path)
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    entries = accessor.list_files()
    paths = {e["path"] for e in entries}

    for internal in _CAGE_INTERNALS:
        assert internal not in paths, f"Cage internal {internal!r} leaked into listing"


def test_list_files_subdir(tmp_path):
    """list_files("subdir") returns only files under subdir."""
    _setup_workspace(tmp_path)
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    entries = accessor.list_files(prefix="subdir")
    paths = {e["path"] for e in entries}

    assert "subdir/nested.txt" in paths
    assert "subdir/deep/file.py" in paths
    # Files outside subdir should NOT be present
    assert "README.md" not in paths
    assert "src/app.py" not in paths


def test_list_files_suffix_filter(tmp_path):
    """list_files(suffix='.py') returns only .py files."""
    _setup_workspace(tmp_path)
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    entries = accessor.list_files(suffix=".py")
    paths = {e["path"] for e in entries}

    assert "src/app.py" in paths
    assert "src/utils.py" in paths
    assert "subdir/deep/file.py" in paths
    # Non-.py files should not be present
    assert "README.md" not in paths
    assert "subdir/nested.txt" not in paths


def test_list_files_path_escape_raises_403(tmp_path):
    """list_files('../../etc') → RuntimeApiError with ERR_PATH_ESCAPE and http_status=403."""
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    with pytest.raises(RuntimeApiError) as exc_info:
        accessor.list_files(prefix="../../etc")

    assert exc_info.value.code == ERR_PATH_ESCAPE
    assert exc_info.value.http_status == 403


def test_list_files_path_escape_absolute_raises_403(tmp_path):
    """list_files('/etc/passwd') → RuntimeApiError with ERR_PATH_ESCAPE."""
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    with pytest.raises(RuntimeApiError) as exc_info:
        # On most systems, Path(tmp_path) / Path("/etc") resolves to /etc
        accessor.list_files(prefix="/etc/passwd")

    assert exc_info.value.code == ERR_PATH_ESCAPE
    assert exc_info.value.http_status == 403


def test_list_files_valid_subdir_ok(tmp_path):
    """list_files("src") → returns files in src, no error."""
    _setup_workspace(tmp_path)
    accessor = WorkspaceAccessor(workspace_root=tmp_path)

    entries = accessor.list_files(prefix="src")
    paths = {e["path"] for e in entries}

    assert "src/app.py" in paths
    assert "src/utils.py" in paths
    # No path escape error
    assert all(e["path"].startswith("src") for e in entries)


def test_list_files_kind_field(tmp_path):
    """list_files() includes kind='file' and kind='dir' correctly."""
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir" / "afile.txt").write_text("x")

    accessor = WorkspaceAccessor(workspace_root=tmp_path)
    entries = accessor.list_files()

    kinds = {e["path"]: e["kind"] for e in entries}
    assert kinds.get("adir") == "dir"
    assert kinds.get("adir/afile.txt") == "file"
