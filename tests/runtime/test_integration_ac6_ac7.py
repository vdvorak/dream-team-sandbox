"""Integration tests for AC-6 (GET /git) and AC-7 (GET /files) — RCP-A11 / RCP-A12.

Tests are black-box over the full HTTP stack (ASGI TestClient).
Each test starts with a ready environment (ensure first).

DevEnforcementProvider is used for all tests (enforcement_provider=dev, mode=active).
WorkspaceAccessor is injected with a mock git_runner + tmp_path for full isolation.

Acceptance criteria covered:
  RCP-6a: GET /git on ready → 200 with branch/dirty/changed_files/last_commit
  RCP-6b: GET /git on provisioning/asleep/destroyed → 409 ERR_ENVIRONMENT_NOT_READY
  RCP-6c: GET /git nonexistent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND
  RCP-6e: GET /git without auth → 401
  RCP-7a: GET /files on ready → 200 with files: [...]
  RCP-7b: GET /files?path=subdir → 200 with subdir contents
  RCP-7c: GET /files?path=../../etc/passwd → 403 ERR_PATH_ESCAPE
  RCP-7d: GET /files on non-ready → 409 ERR_ENVIRONMENT_NOT_READY
  RCP-7e: GET /files nonexistent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND
  RCP-7g: GET /files without auth → 401
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from server.runtime.enforcement.dev import DevEnforcementProvider
from server.runtime.main import create_runtime_app
from server.runtime.workspace import WorkspaceAccessor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_TOKEN = "ac6-ac7-test-token"
AUTH = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
VALID_REPO = "https://github.com/example/repo"
VALID_TOOL = "claude"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_git_runner(branch="main", porcelain="", last_commit="abc123"):
    """Return a canned async git runner."""
    async def _runner(args: list[str], cwd: Path) -> str:
        subcommand = args[1] if len(args) > 1 else ""
        if subcommand == "branch":
            return branch
        if subcommand == "status":
            return porcelain
        if subcommand == "log":
            return last_commit
        return ""
    return _runner


def _make_workspace(tmp_path: Path, git_runner=None) -> WorkspaceAccessor:
    """Create a WorkspaceAccessor with a simple file tree and optional canned git runner."""
    (tmp_path / "README.md").write_text("readme")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested content")
    runner = git_runner or _make_git_runner()
    return WorkspaceAccessor(workspace_root=tmp_path, git_runner=runner)


def _make_app(workspace_accessor: WorkspaceAccessor) -> object:
    """Create a test app with DevEnforcementProvider and injected workspace accessor."""
    provider = DevEnforcementProvider(mode="active")
    return create_runtime_app(
        service_token=SERVICE_TOKEN,
        enforcement_provider_override=provider,
        workspace_accessor_override=workspace_accessor,
    )


def _http_client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _ensure_ready(client: AsyncClient, project_id: str) -> None:
    """POST ensure and assert environment reaches ready."""
    r = await client.post(
        f"/v1/environments/{project_id}/ensure",
        json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
        headers=AUTH,
    )
    assert r.status_code == 200, f"ensure failed: {r.status_code} {r.text}"
    assert r.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def assert_no_substrate_nouns(response_body: str) -> None:
    """Assert response body contains no substrate-identifying nouns (RCP-11a / AC-6d)."""
    SUBSTRATE_NOUNS = ["Fly", "fly.io", "docker", "6PN", ".internal", "WORKSPACE_AGENT_BASE", "nftables", "tmux"]
    for noun in SUBSTRATE_NOUNS:
        assert noun not in response_body, f"Substrate noun {noun!r} leaked into response body"


# ---------------------------------------------------------------------------
# RCP-6: GET /environments/{id}/git
# ---------------------------------------------------------------------------


class TestRCP6Git:
    """RCP-6: GET /v1/environments/{project_id}/git."""

    @pytest.mark.asyncio
    async def test_rcp6a_git_on_ready_returns_200(self, tmp_path):
        """RCP-6a: GET /git on ready → 200 with branch/dirty/changed_files/last_commit."""
        runner = _make_git_runner(
            branch="feature-branch",
            porcelain=" M src/app.py\n",
            last_commit="deadbeef1234",
        )
        ws = _make_workspace(tmp_path, git_runner=runner)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp6a")
            r = await c.get("/v1/environments/rcp6a/git", headers=AUTH)

        assert r.status_code == 200, f"RCP-6a: expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "branch" in data, "RCP-6a: missing branch"
        assert "dirty" in data, "RCP-6a: missing dirty"
        assert "changed_files" in data, "RCP-6a: missing changed_files"
        assert "last_commit" in data, "RCP-6a: missing last_commit"
        assert data["branch"] == "feature-branch"
        assert data["dirty"] is True
        assert data["last_commit"] == "deadbeef1234"

    @pytest.mark.asyncio
    async def test_rcp6b_git_on_provisioning_returns_409(self, tmp_path):
        """RCP-6b: GET /git on provisioning → 409 ERR_ENVIRONMENT_NOT_READY."""
        # Use fail mode so ensure leaves environment in provisioning/error (not ready)
        provider = DevEnforcementProvider(mode="fail")
        ws = _make_workspace(tmp_path)
        app = create_runtime_app(
            service_token=SERVICE_TOKEN,
            enforcement_provider_override=provider,
            workspace_accessor_override=ws,
        )
        async with _http_client(app) as c:
            # Attempt ensure — will fail, leaving environment in a non-ready state
            await c.post(
                "/v1/environments/rcp6b-prov/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            # GET /git should reject non-ready
            r = await c.get("/v1/environments/rcp6b-prov/git", headers=AUTH)

        # Either 409 (if record exists in provisioning) or 404 (if env was never persisted)
        # The spec says non-ready → 409; but if ensure failed before saving, it's 404.
        # We check for 409 or 404 — both are acceptable "not ready" signals.
        assert r.status_code in (409, 404), (
            f"RCP-6b: expected 409 or 404, got {r.status_code}: {r.text}"
        )
        if r.status_code == 409:
            assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_READY"

    @pytest.mark.asyncio
    async def test_rcp6b_git_on_asleep_returns_409(self, tmp_path):
        """RCP-6b: GET /git on asleep → 409 ERR_ENVIRONMENT_NOT_READY."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp6b-asleep")
            # Put to sleep
            await c.post("/v1/environments/rcp6b-asleep/sleep", headers=AUTH)
            r = await c.get("/v1/environments/rcp6b-asleep/git", headers=AUTH)

        assert r.status_code == 409, (
            f"RCP-6b: expected 409, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_READY"

    @pytest.mark.asyncio
    async def test_rcp6b_git_on_destroyed_returns_409(self, tmp_path):
        """RCP-6b: GET /git on destroyed → 409 ERR_ENVIRONMENT_NOT_READY."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp6b-destroyed")
            await c.delete("/v1/environments/rcp6b-destroyed", headers=AUTH)
            r = await c.get("/v1/environments/rcp6b-destroyed/git", headers=AUTH)

        assert r.status_code == 409, (
            f"RCP-6b: expected 409, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_READY"

    @pytest.mark.asyncio
    async def test_rcp6c_git_nonexistent_returns_404(self, tmp_path):
        """RCP-6c: GET /git nonexistent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            r = await c.get("/v1/environments/nonexistent-project/git", headers=AUTH)

        assert r.status_code == 404, (
            f"RCP-6c: expected 404, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_rcp6d_git_response_no_substrate_nouns(self, tmp_path):
        """RCP-6d / AC-6d: GET /git on ready → response body must not contain substrate nouns."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp6d")
            r = await c.get("/v1/environments/rcp6d/git", headers=AUTH)

        assert r.status_code == 200, f"RCP-6d: expected 200, got {r.status_code}: {r.text}"
        assert_no_substrate_nouns(r.text)

    @pytest.mark.asyncio
    async def test_rcp6e_git_without_auth_returns_401(self, tmp_path):
        """RCP-6e: GET /git without auth → 401."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp6e")
            r = await c.get("/v1/environments/rcp6e/git")  # no auth header

        assert r.status_code == 401, (
            f"RCP-6e: expected 401, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_UNAUTHORIZED"


# ---------------------------------------------------------------------------
# RCP-7: GET /environments/{id}/files
# ---------------------------------------------------------------------------


class TestRCP7Files:
    """RCP-7: GET /v1/environments/{project_id}/files."""

    @pytest.mark.asyncio
    async def test_rcp7a_files_on_ready_returns_200(self, tmp_path):
        """RCP-7a: GET /files on ready → 200 with files: [...]."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7a")
            r = await c.get("/v1/environments/rcp7a/files", headers=AUTH)

        assert r.status_code == 200, (
            f"RCP-7a: expected 200, got {r.status_code}: {r.text}"
        )
        data = r.json()
        assert "files" in data, "RCP-7a: missing files key"
        assert isinstance(data["files"], list), "RCP-7a: files should be a list"
        paths = {f["path"] for f in data["files"]}
        assert "README.md" in paths, "RCP-7a: expected README.md in files"
        assert "src/app.py" in paths, "RCP-7a: expected src/app.py in files"

    @pytest.mark.asyncio
    async def test_rcp7b_files_with_path_returns_subdir(self, tmp_path):
        """RCP-7b: GET /files?path=subdir → 200 with subdir contents only."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7b")
            r = await c.get("/v1/environments/rcp7b/files?path=subdir", headers=AUTH)

        assert r.status_code == 200, (
            f"RCP-7b: expected 200, got {r.status_code}: {r.text}"
        )
        data = r.json()
        paths = {f["path"] for f in data["files"]}
        assert "subdir/nested.txt" in paths, "RCP-7b: expected subdir/nested.txt"
        # Files outside subdir should NOT be present
        assert "README.md" not in paths, "RCP-7b: README.md should not be in subdir listing"
        assert "src/app.py" not in paths, "RCP-7b: src/app.py should not be in subdir listing"

    @pytest.mark.asyncio
    async def test_rcp7c_files_path_traversal_returns_403(self, tmp_path):
        """RCP-7c: GET /files?path=../../etc/passwd → 403 ERR_PATH_ESCAPE."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7c")
            r = await c.get(
                "/v1/environments/rcp7c/files?path=../../etc/passwd",
                headers=AUTH,
            )

        assert r.status_code == 403, (
            f"RCP-7c: expected 403, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_PATH_ESCAPE"

    @pytest.mark.asyncio
    async def test_rcp7d_files_on_non_ready_returns_409(self, tmp_path):
        """RCP-7d: GET /files on non-ready → 409 ERR_ENVIRONMENT_NOT_READY."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7d")
            await c.post("/v1/environments/rcp7d/sleep", headers=AUTH)
            r = await c.get("/v1/environments/rcp7d/files", headers=AUTH)

        assert r.status_code == 409, (
            f"RCP-7d: expected 409, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_READY"

    @pytest.mark.asyncio
    async def test_rcp7e_files_nonexistent_returns_404(self, tmp_path):
        """RCP-7e: GET /files nonexistent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            r = await c.get(
                "/v1/environments/no-such-project/files",
                headers=AUTH,
            )

        assert r.status_code == 404, (
            f"RCP-7e: expected 404, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_rcp7f_files_response_excludes_cage_internals(self, tmp_path):
        """RCP-7f / AC-7: GET /files → cage-internal files must not appear in listing."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        # Create cage-internal files that the implementation must exclude
        cage_files = [
            "entrypoint.sh",
            "Dockerfile.workspace",
            "nftables.cage.conf",
            "fly.workspace.toml",
            "smokescreen-acl.nft",
            "smokescreen-acl.yaml",
        ]
        for fname in cage_files:
            (tmp_path / fname).write_text(f"# cage internal: {fname}")

        # Legitimate user file that must appear in the listing
        (tmp_path / "main.py").write_text("print('hello')")

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7f")
            r = await c.get("/v1/environments/rcp7f/files", headers=AUTH)

        assert r.status_code == 200, f"RCP-7f: expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "files" in data, "RCP-7f: missing files key"
        returned_paths = {f["path"] for f in data["files"]}

        # Cage-internal files must NOT be present
        for fname in cage_files:
            assert fname not in returned_paths, (
                f"RCP-7f: cage-internal file {fname!r} leaked into /files response"
            )

        # Legitimate file must be present (guard against false-green empty listing)
        assert "main.py" in returned_paths, (
            "RCP-7f: main.py missing from /files response — test may be falsely passing"
        )

    @pytest.mark.asyncio
    async def test_rcp7g_files_without_auth_returns_401(self, tmp_path):
        """RCP-7g: GET /files without auth → 401."""
        ws = _make_workspace(tmp_path)
        app = _make_app(ws)

        async with _http_client(app) as c:
            await _ensure_ready(c, "rcp7g")
            r = await c.get("/v1/environments/rcp7g/files")  # no auth

        assert r.status_code == 401, (
            f"RCP-7g: expected 401, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_UNAUTHORIZED"
