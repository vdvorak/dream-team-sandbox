"""Enforcement provider Protocol + closed result type (RCP-A2).

WHY closed result (not exception-for-failure): the fail-closed invariant must be
structurally enforced. A two-variant return type makes the compiler/type-checker
reject any path that doesn't handle both outcomes. Exceptions can be swallowed;
a required pattern-match cannot.

This module defines:
  - ConnectionHandle  — opaque pair of URLs (control + terminal). Provider-owned.
  - EnforcementActive — enforcement is provably active; carries the handle.
  - EnforcementFailed — enforcement cannot be applied or verified; carries a kind.
  - FailureKind       — closed enum: provider_error | provider_unreachable.
  - ProviderHealth    — closed enum for healthz: ok | degraded | unavailable.
  - EnforcementOutcome — type alias for the two-variant result.
  - EnforcementProvider Protocol — the single abstract boundary (RCP-A2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class FailureKind(str, Enum):
    """Two kinds of enforcement failure (RCP-A2). Service translates kind → HTTP, never internal_code."""

    provider_error = "provider_error"
    provider_unreachable = "provider_unreachable"


class ProviderHealth(str, Enum):
    """Health state reported by provider.health() (RCP-A3, RCP-9c)."""

    ok = "ok"
    degraded = "degraded"
    unavailable = "unavailable"


@dataclass(frozen=True)
class ConnectionHandle:
    """Opaque connection handle produced by the provider (not the service).

    WHY opaque: service passes it to the response unchanged. Neither service
    nor client can infer the substrate from the URLs (RCP-A6 / contract §1).
    """

    control_url: str
    terminal_url: str


@dataclass(frozen=True)
class EnforcementActive:
    """Enforcement is provably active. Sole gateway to status=ready (RCP-A3)."""

    handle: ConnectionHandle


@dataclass(frozen=True)
class EnforcementFailed:
    """Enforcement cannot be applied or verified — fail-closed.

    internal_code: cage error code (contracts/error-codes.md) OR None.
    MUST stay server-side; MUST NOT appear in any app-facing response (RCP-A5).
    """

    kind: FailureKind
    internal_code: str | None = None


# Closed two-variant result — no third path (RCP-A2).
EnforcementOutcome = EnforcementActive | EnforcementFailed


@dataclass(frozen=True)
class RepoSpec:
    """Minimal repo parameters needed by the provider (mirrors EnsureRequest.repo)."""

    url: str
    ref: str | None = None


@runtime_checkable
class EnforcementProvider(Protocol):
    """Abstract boundary between the control-plane and security enforcement (RCP-A2).

    Implementations: DevEnforcementProvider (default, slice 1) and
    CageEnforcementProvider (STUB, deferred integration).
    """

    async def ensure_active(
        self,
        project_id: str,
        repo: RepoSpec,
        tool: str,
    ) -> EnforcementOutcome:
        """Ensure enforcement is active for the given project/repo/tool.

        MUST return EnforcementActive or EnforcementFailed — no third path.
        MUST NOT raise expected failures as exceptions (use EnforcementFailed).
        Unexpected (infra) exceptions may propagate — service catches them.
        """
        ...

    async def health(self) -> ProviderHealth:
        """Report current health for the healthz endpoint (RCP-9c)."""
        ...
