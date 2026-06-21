"""DevEnforcementProvider — slice 1 default enforcement provider.

Real enforcement is NOT applied (dry-run mode for local/dev use).
Returns opaque stub handles with no substrate identifiers (RCP-A6 risk E).

Supports three test modes via constructor injection (RCP-2):
  - "active"  (default) → EnforcementActive with opaque stub handle
  - "fail"              → EnforcementFailed(provider_error)
  - "down"              → EnforcementFailed(provider_unreachable)

WHY test modes on the provider rather than mocking: service tests need deterministic
enforcement outcomes without patching internals. Injecting the provider (DI) with
a configured mode gives clean, readable test setup.
"""

from __future__ import annotations

import hashlib
import logging

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

# Valid test modes (documented; checked at construction time to fail fast on typo).
_VALID_MODES = frozenset({"active", "fail", "down"})


def _opaque_id(project_id: str) -> str:
    """Derive a short opaque identifier from project_id.

    WHY hashed: the resulting string must not reveal the original project_id
    (or any substrate noun) in the URL. A 16-char hex prefix of SHA-256 is
    effectively unguessable while being stable for the same project.
    """
    return hashlib.sha256(project_id.encode()).hexdigest()[:16]


def _opaque_token(project_id: str, suffix: str) -> str:
    """Derive a stable opaque token segment for the URL path."""
    return hashlib.sha256(f"{project_id}:{suffix}".encode()).hexdigest()[:32]


def _make_handle(project_id: str) -> ConnectionHandle:
    """Produce an opaque ConnectionHandle that reveals no substrate information.

    URL shape: https://rt.<opaque-id>.example/control/<opaque-token>
               wss://rt.<opaque-id>.example/terminal/<opaque-token>

    - No Fly / Docker / 6PN / .internal nouns (RCP-A6 E, RCP-11c, AC-3b).
    - No port :808x.
    - control_url uses https:// scheme.
    - terminal_url uses wss:// scheme (RCP-A6 E).
    - .example TLD is clearly non-production; swap for real host in CageEnforcementProvider.
    """
    oid = _opaque_id(project_id)
    control_token = _opaque_token(project_id, "control")
    terminal_token = _opaque_token(project_id, "terminal")
    return ConnectionHandle(
        control_url=f"https://rt.{oid}.example/control/{control_token}",
        terminal_url=f"wss://rt.{oid}.example/terminal/{terminal_token}",
    )


class DevEnforcementProvider:
    """Development / dry-run enforcement provider (slice 1 default).

    Enforcement is NOT applied — suitable only for local development and testing.
    In production, replace with CageEnforcementProvider via config enforcement_provider=cage.
    """

    def __init__(self, mode: str = "active") -> None:
        if mode not in _VALID_MODES:
            raise ValueError(f"DevEnforcementProvider: invalid mode {mode!r}. Must be one of {_VALID_MODES}")
        self._mode = mode

    async def ensure_active(
        self,
        project_id: str,
        repo: RepoSpec,
        tool: str,
    ) -> EnforcementOutcome:
        logger.debug(
            "dev_provider.ensure_active project_id=%s mode=%s",
            project_id,
            self._mode,
        )
        if self._mode == "active":
            handle = _make_handle(project_id)
            return EnforcementActive(handle=handle)
        if self._mode == "fail":
            # Simulates enforcement error (e.g. policy apply failed).
            return EnforcementFailed(
                kind=FailureKind.provider_error,
                internal_code=None,
            )
        # mode == "down": simulates provider unreachable.
        return EnforcementFailed(
            kind=FailureKind.provider_unreachable,
            internal_code=None,
        )

    async def health(self) -> ProviderHealth:
        if self._mode == "active":
            return ProviderHealth.ok
        if self._mode == "fail":
            # Provider responds but reports degradation.
            return ProviderHealth.degraded
        # mode == "down": provider unreachable.
        return ProviderHealth.unavailable
