"""CageEnforcementProvider — real implementation via CageRuntimeProvider (RCP-A10).

This provider bridges the EnforcementProvider contract and the substrate-specific
CageRuntimeProvider (e.g. FlyProvider). It is substrate-blind: it only calls the
CageRuntimeProvider interface and translates results to the typed EnforcementOutcome.

WHY substrate-blind (RCP-A10):
  - internal_code goes only to logs — NEVER into app-facing responses (RCP-A5).
  - This class does not import FlyProvider or any Fly-specific type.
  - Unexpected exceptions (not CageError subclasses) propagate upward; the service
    layer translates them to 503 ERR_RUNTIME_UNAVAILABLE.

Wiring (main.py / config):
  cage_runtime = FlyProvider(api_token=..., app_name=...)
  provider = CageEnforcementProvider(cage_runtime=cage_runtime)
"""

from __future__ import annotations

import logging

from server.cage.errors import CageError, ProxyDownError
from server.cage.runtime import CageRuntimeProvider

from .provider import (
    ConnectionHandle,
    EnforcementActive,
    EnforcementFailed,
    EnforcementOutcome,
    FailureKind,
    ProviderHealth,
    RepoSpec,
)

logger = logging.getLogger(__name__)


class CageEnforcementProvider:
    """Real enforcement provider — delegates workspace lifecycle to CageRuntimeProvider.

    Translates CageError hierarchy to typed EnforcementOutcome. Unexpected exceptions
    (infrastructure failures outside the CageError hierarchy) propagate to the service.
    """

    def __init__(self, cage_runtime: CageRuntimeProvider) -> None:
        self._runtime = cage_runtime

    async def ensure_active(
        self,
        project_id: str,
        repo: RepoSpec,
        tool: str,
    ) -> EnforcementOutcome:
        """Ensure a workspace is running; return typed outcome (never raises expected errors).

        On success → EnforcementActive with opaque ConnectionHandle.
        On CageError → EnforcementFailed with appropriate FailureKind.
        Unexpected exceptions propagate (service catches → 503).
        """
        try:
            handle = await self._runtime.start(
                project_id=project_id,
                repo_url=repo.url,
                ref=repo.ref,
                tool=tool,
            )
            return EnforcementActive(
                handle=ConnectionHandle(
                    control_url=handle.control_url,
                    terminal_url=handle.terminal_url,
                )
            )
        except ProxyDownError as e:
            # Network/availability failure — provider unreachable.
            logger.warning(
                "cage_enforcement.ensure_active: proxy_down project_id=%s internal_code=%s",
                project_id,
                e.code,  # stays server-side (RCP-A5)
            )
            return EnforcementFailed(
                kind=FailureKind.provider_unreachable,
                internal_code=e.code,
            )
        except CageError as e:
            # Policy or other cage error — provider responded but enforcement failed.
            logger.warning(
                "cage_enforcement.ensure_active: cage_error project_id=%s internal_code=%s",
                project_id,
                e.code,  # stays server-side (RCP-A5)
            )
            return EnforcementFailed(
                kind=FailureKind.provider_error,
                internal_code=e.code,
            )
        # Any other exception propagates — service will catch and return 503.

    async def health(self) -> ProviderHealth:
        """Delegate health check to the underlying runtime provider."""
        return await self._runtime.health()
