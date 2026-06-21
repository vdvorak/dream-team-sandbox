"""WorkspaceAccessor — git subprocess helper + file accessor (RCP-A11, RCP-A12).

Responsibilities:
  - git_status(): runs git subprocesses, returns GitStatus (no absolute paths in output).
  - list_files(): sandboxed directory listing, filters cage internals.

Security invariants (load-bearing):
  - Path sandbox check in list_files: resolved path MUST be relative to workspace_root.
    Path traversal → 403 ERR_PATH_ESCAPE (NEVER 5xx).
  - Cage internals blacklist: specific files are NEVER returned to callers.

Testability:
  - git_runner is injectable (default uses real subprocess); tests pass a mock callable
    that returns pre-canned output without touching the filesystem.
  - workspace_root is injectable (tests pass a tmp_path).

WHY no absolute paths in response (RCP-A11):
  WorkspaceAccessor returns relative paths only. Callers (service → router) forward
  these unchanged. Absolute paths would reveal workspace layout (substrát-noun, RCP-A5).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ERR_PATH_ESCAPE, RuntimeApiError

logger = logging.getLogger(__name__)

# Cage internals: files that MUST be excluded from list_files results (RCP-A12).
# These are substrate-specific config/bootstrap files — exposing them leaks cage internals.
_CAGE_INTERNALS: frozenset[str] = frozenset(
    {
        "Dockerfile.workspace",
        "entrypoint.sh",
        "nftables.cage.conf",
        "fly.workspace.toml",
        "smokescreen-acl.nft",
        "smokescreen-acl.yaml",
    }
)


@dataclass
class GitStatus:
    """Result of a git status check (RCP-A11).

    All paths are relative — no absolute paths (substrát-noun leak prevention).
    """

    branch: str
    dirty: bool
    changed_files: list[str] = field(default_factory=list)
    last_commit: str | None = None


async def _default_git_runner(args: list[str], cwd: Path) -> str:
    """Run a git command as a subprocess and return stdout.

    WHY async: keeps the service layer non-blocking (asyncio-friendly).
    """
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd),
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.debug(
            "git command failed: %s returncode=%d stderr=%s",
            args,
            proc.returncode,
            stderr.decode(errors="replace").strip(),
        )
        return ""
    return stdout.decode(errors="replace").strip()


class WorkspaceAccessor:
    """Accesses git status and file listings inside a workspace root.

    Args:
        workspace_root: Absolute path to the workspace directory.
        git_runner: Async callable (args, cwd) → str. Defaults to real subprocess.
            Inject a mock for testing without filesystem/network.
    """

    def __init__(
        self,
        workspace_root: Path,
        git_runner=None,
    ) -> None:
        self._root = workspace_root.resolve()
        self._git = git_runner or _default_git_runner

    async def git_status(self) -> GitStatus:
        """Run git commands and return a GitStatus (RCP-A11).

        Uses three git commands:
          - git branch --show-current  → branch name
          - git status --porcelain     → dirty flag + changed files
          - git log -1 --format=%H     → last commit hash

        Returns best-effort results: if git is not installed or repo doesn't exist,
        returns sensible defaults (empty branch, not dirty, no commit).
        No absolute paths are included in the result.
        """
        branch = await self._git(
            ["git", "branch", "--show-current"], self._root
        )

        porcelain = await self._git(
            ["git", "status", "--porcelain"], self._root
        )

        last_commit_raw = await self._git(
            ["git", "log", "-1", "--format=%H"], self._root
        )

        # Parse porcelain output: each non-empty line = one changed file.
        changed_files: list[str] = []
        for line in porcelain.splitlines():
            line = line.strip()
            if not line:
                continue
            # porcelain format: "XY filename" — take the filename (after first space)
            parts = line.split(None, 1)
            if len(parts) == 2:
                changed_files.append(parts[1])

        dirty = len(changed_files) > 0
        last_commit = last_commit_raw if last_commit_raw else None

        return GitStatus(
            branch=branch or "",
            dirty=dirty,
            changed_files=changed_files,
            last_commit=last_commit,
        )

    def list_files(self, prefix: str = "", suffix: str = "") -> list[dict]:
        """List files under workspace_root/prefix, filtered by suffix.

        Path sandbox check (LOAD-BEARING security invariant, RCP-A12):
          Any resolved path that escapes workspace_root raises RuntimeApiError(403).
          This MUST remain — removing it would allow directory traversal attacks.

        Cage internals blacklist: files in _CAGE_INTERNALS are excluded from results
        regardless of where they appear in the tree.

        Returns a list of {"path": <relative>, "kind": "file"|"dir"} dicts.
        Paths are relative to workspace_root (no absolute paths — RCP-A11/A12).
        """
        # --- Path sandbox check (load-bearing) ---
        try:
            target = (self._root / Path(prefix)).resolve()
        except Exception as exc:
            raise RuntimeApiError(
                code=ERR_PATH_ESCAPE,
                message="Invalid path",
                http_status=403,
            ) from exc

        if not target.is_relative_to(self._root):
            raise RuntimeApiError(
                code=ERR_PATH_ESCAPE,
                message="Path traversal detected",
                http_status=403,
            )

        # --- Collect entries ---
        results: list[dict] = []

        if not target.exists():
            return results

        if target.is_file():
            # prefix points directly to a file
            rel = target.relative_to(self._root)
            name = rel.name
            if name not in _CAGE_INTERNALS:
                if not suffix or str(rel).endswith(suffix):
                    results.append({"path": str(rel), "kind": "file"})
            return results

        # target is a directory — walk it
        for item in sorted(target.rglob("*")):
            # Sandbox check for each item (defensive, shouldn't be needed but safe).
            try:
                resolved_item = item.resolve()
            except Exception:
                continue
            if not resolved_item.is_relative_to(self._root):
                continue

            rel = item.relative_to(self._root)
            name = item.name

            # Exclude cage internals (by filename, regardless of directory).
            if name in _CAGE_INTERNALS:
                continue

            # Apply suffix filter.
            if suffix and not str(rel).endswith(suffix):
                continue

            kind = "dir" if item.is_dir() else "file"
            results.append({"path": str(rel), "kind": kind})

        return results
