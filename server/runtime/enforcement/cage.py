"""CageEnforcementProvider — STUB for slice 1.

Real cage integration is OUT of scope for slice 1.

WHY this stub exists: the Protocol boundary is defined and the attachment point
is documented so that the slice 2 implementor knows exactly where to wire in the
real cage calls without touching service.py or any other layer.

Integration notes for the implementor of the real provider:
  - Import CageError hierarchy from server.cage.errors (read-only per RCP-A2 / reuse decision).
  - Translate each CageError subclass to EnforcementFailed with the appropriate kind:
      - Network/availability errors → FailureKind.provider_unreachable
      - Policy/enforcement errors   → FailureKind.provider_error
  - Pass e.code as internal_code (kept server-side, NEVER forwarded to client per RCP-A5).
  - The service layer translates kind → app-facing error code; it never sees internal_code.
"""

from __future__ import annotations

from .provider import EnforcementOutcome, ProviderHealth, RepoSpec


class CageEnforcementProvider:
    """Stub — cage enforcement provider attachment point (slice 1 placeholder).

    Replace this NotImplementedError body with real cage calls in the next wave.
    See module docstring for integration notes.
    """

    async def ensure_active(
        self,
        project_id: str,
        repo: RepoSpec,
        tool: str,
    ) -> EnforcementOutcome:
        # TODO(slice-2): wire in real cage operations here.
        # Pattern:
        #   try:
        #       result = await cage_deploy.ensure_workspace(project_id, repo.url, repo.ref, tool)
        #       handle = ConnectionHandle(control_url=result.control_url, terminal_url=result.terminal_url)
        #       return EnforcementActive(handle=handle)
        #   except ProxyDownError as e:
        #       return EnforcementFailed(FailureKind.provider_unreachable, internal_code=e.code)
        #   except CageError as e:
        #       return EnforcementFailed(FailureKind.provider_error, internal_code=e.code)
        raise NotImplementedError(
            "CageEnforcementProvider is a stub. Real cage integration is deferred to slice 2. "
            "See server/runtime/enforcement/cage.py docstring for wiring instructions."
        )

    async def health(self) -> ProviderHealth:
        # TODO(slice-2): query cage health endpoint and translate to ProviderHealth.
        raise NotImplementedError(
            "CageEnforcementProvider.health() is a stub. Deferred to slice 2."
        )
