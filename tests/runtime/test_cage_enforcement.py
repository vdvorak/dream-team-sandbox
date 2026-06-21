"""Unit tests for CageEnforcementProvider (RCP-A10).

Tests inject a mock CageRuntimeProvider — no Fly API calls.

Coverage:
  - runtime.start() OK → EnforcementActive with ConnectionHandle
  - runtime.start() raises ProxyDownError → EnforcementFailed(provider_unreachable)
  - runtime.start() raises CageError → EnforcementFailed(provider_error)
  - health() delegates to runtime.health()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from server.cage.errors import CageError, NoPolicyError, ProxyDownError
from server.cage.runtime import WorkspaceHandle
from server.runtime.enforcement.cage import CageEnforcementProvider
from server.runtime.enforcement.provider import (
    ConnectionHandle,
    EnforcementActive,
    EnforcementFailed,
    FailureKind,
    ProviderHealth,
    RepoSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_runtime(start_result=None, start_raises=None, health_result=None) -> MagicMock:
    """Build a mock CageRuntimeProvider with configurable behaviours."""
    runtime = MagicMock()
    if start_raises is not None:
        runtime.start = AsyncMock(side_effect=start_raises)
    elif start_result is not None:
        runtime.start = AsyncMock(return_value=start_result)
    else:
        runtime.start = AsyncMock(return_value=None)
    if health_result is not None:
        runtime.health = AsyncMock(return_value=health_result)
    else:
        runtime.health = AsyncMock(return_value=ProviderHealth.ok)
    return runtime


_REPO = RepoSpec(url="https://github.com/example/repo", ref=None)
_HANDLE = WorkspaceHandle(
    control_url="https://rt.abc123.example/control/token1234",
    terminal_url="wss://rt.abc123.example/terminal/token1234",
)


# ---------------------------------------------------------------------------
# ensure_active() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_active_ok_returns_enforcement_active():
    """runtime.start() OK → EnforcementActive with ConnectionHandle."""
    runtime = _mock_runtime(start_result=_HANDLE)
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.ensure_active("proj-1", _REPO, "claude")

    assert isinstance(result, EnforcementActive)
    assert isinstance(result.handle, ConnectionHandle)
    assert result.handle.control_url == _HANDLE.control_url
    assert result.handle.terminal_url == _HANDLE.terminal_url


@pytest.mark.asyncio
async def test_ensure_active_proxy_down_returns_failed_unreachable():
    """runtime.start() raises ProxyDownError → EnforcementFailed(provider_unreachable)."""
    runtime = _mock_runtime(start_raises=ProxyDownError("smoke is down"))
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.ensure_active("proj-1", _REPO, "claude")

    assert isinstance(result, EnforcementFailed)
    assert result.kind == FailureKind.provider_unreachable
    # internal_code is the cage error code (server-side only)
    assert result.internal_code == ProxyDownError.code


@pytest.mark.asyncio
async def test_ensure_active_cage_error_returns_failed_provider_error():
    """runtime.start() raises CageError → EnforcementFailed(provider_error)."""
    runtime = _mock_runtime(start_raises=CageError("some cage error"))
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.ensure_active("proj-1", _REPO, "claude")

    assert isinstance(result, EnforcementFailed)
    assert result.kind == FailureKind.provider_error
    assert result.internal_code == CageError.code


@pytest.mark.asyncio
async def test_ensure_active_no_policy_error_returns_failed_provider_error():
    """NoPolicyError (CageError subclass) → EnforcementFailed(provider_error)."""
    runtime = _mock_runtime(start_raises=NoPolicyError("no policy"))
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.ensure_active("proj-1", _REPO, "claude")

    assert isinstance(result, EnforcementFailed)
    assert result.kind == FailureKind.provider_error
    assert result.internal_code == NoPolicyError.code


@pytest.mark.asyncio
async def test_ensure_active_unexpected_exception_propagates():
    """Unexpected (non-CageError) exception propagates — service layer handles → 503."""
    runtime = _mock_runtime(start_raises=RuntimeError("unexpected infra failure"))
    provider = CageEnforcementProvider(cage_runtime=runtime)

    with pytest.raises(RuntimeError, match="unexpected infra failure"):
        await provider.ensure_active("proj-1", _REPO, "claude")


# ---------------------------------------------------------------------------
# health() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_delegates_to_runtime_ok():
    """health() delegates to runtime.health() → ProviderHealth.ok."""
    runtime = _mock_runtime(health_result=ProviderHealth.ok)
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.health()

    assert result == ProviderHealth.ok
    runtime.health.assert_called_once()


@pytest.mark.asyncio
async def test_health_delegates_to_runtime_degraded():
    """health() delegates to runtime.health() → ProviderHealth.degraded."""
    runtime = _mock_runtime(health_result=ProviderHealth.degraded)
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.health()

    assert result == ProviderHealth.degraded


@pytest.mark.asyncio
async def test_health_delegates_to_runtime_unavailable():
    """health() delegates to runtime.health() → ProviderHealth.unavailable."""
    runtime = _mock_runtime(health_result=ProviderHealth.unavailable)
    provider = CageEnforcementProvider(cage_runtime=runtime)

    result = await provider.health()

    assert result == ProviderHealth.unavailable
