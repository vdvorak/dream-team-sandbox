"""Provider-agnostic cage runtime layer — CageRuntimeProvider Protocol + types (RCP-A9).

WHY a separate Protocol here and not reuse EnforcementProvider:
  EnforcementProvider is the *control-plane* boundary (ensures enforcement is active,
  returns typed results). CageRuntimeProvider is the *substrate* boundary (start/stop
  workspaces on a concrete backing service). The two concerns are kept separate so that:
    - EnforcementProvider remains substrate-blind (it gets a WorkspaceHandle, never a
      Fly machine ID or any substrate noun — RCP-A6 E).
    - CageRuntimeProvider implementations can be swapped without touching enforcement logic.

ProviderHealth is imported from enforcement/provider.py to avoid duplication — it is the
same health concept used at both layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from server.runtime.enforcement.provider import ProviderHealth


class WorkspaceStatus(str, Enum):
    """Lifecycle state of a workspace as seen by the runtime layer."""

    starting = "starting"
    ready = "ready"
    stopped = "stopped"
    unknown = "unknown"


@dataclass(frozen=True)
class WorkspaceHandle:
    """Opaque URLs produced by CageRuntimeProvider — no substrate nouns (RCP-A6 E).

    Both URLs must be opaque: they MUST NOT contain any of the following substrings:
    Fly, fly, docker, 6PN, .internal, :808x, or any machine/container identifier.
    """

    control_url: str   # opaque; typically https://
    terminal_url: str  # opaque; typically wss://


class CageRuntimeProvider(Protocol):
    """Protocol for substrate-specific workspace lifecycle management (RCP-A9).

    Implementations: FlyProvider (Fly.io Machines API).
    Callers: CageEnforcementProvider (enforcement layer).

    All substrate specifics (machine IDs, Fly API tokens, 6PN addresses …) MUST stay
    inside the implementing class and MUST NOT be exposed through this interface.
    """

    async def start(
        self,
        project_id: str,
        repo_url: str,
        ref: str | None,
        tool: str,
    ) -> WorkspaceHandle:
        """Start (or resume) a workspace for the given project.

        Returns an opaque WorkspaceHandle with no substrate identifiers.
        Raises CageError subclasses on failure (see server/cage/errors.py).
        """
        ...

    async def stop(self, project_id: str) -> None:
        """Stop (sleep) the workspace for the given project.

        Idempotent — stopping an already-stopped workspace MUST NOT raise.
        """
        ...

    async def status(self, project_id: str) -> WorkspaceStatus:
        """Return the current workspace lifecycle status."""
        ...

    async def health(self) -> ProviderHealth:
        """Report current provider health (for healthz delegation)."""
        ...
