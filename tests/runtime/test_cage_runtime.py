"""Unit tests for CageRuntimeProvider + FlyProvider (RCP-A9).

Tests use a mock httpx.AsyncClient injected via the constructor — no real network calls.

Coverage:
  - start() → WorkspaceHandle with opaque URLs (no fly/Fly/.internal/6PN/machine_id)
  - start() → Fly API timeout → ProxyDownError
  - start() → Fly API 5xx → ProxyDownError
  - start() → Fly API 4xx → CageError
  - health() → ok / degraded / unavailable
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from server.cage.errors import CageError, ProxyDownError
from server.cage.providers.fly_provider import FlyProvider, _make_handle
from server.cage.runtime import WorkspaceHandle, WorkspaceStatus
from server.runtime.enforcement.provider import ProviderHealth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data) -> httpx.Response:
    """Build a fake httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = str(json_data)
    return response


def _make_client(post_side_effects=None, get_side_effects=None) -> MagicMock:
    """Build a mock httpx.AsyncClient with configurable post/get behaviour."""
    client = MagicMock(spec=httpx.AsyncClient)
    if post_side_effects is not None:
        client.post = AsyncMock(side_effect=post_side_effects)
    if get_side_effects is not None:
        client.get = AsyncMock(side_effect=get_side_effects)
    return client


# ---------------------------------------------------------------------------
# Opaque URL invariant helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_SUBSTRINGS = [
    "fly",
    "Fly",
    ".internal",
    "6PN",
    ":808",
]


def _assert_opaque(handle: WorkspaceHandle, machine_id: str) -> None:
    """Assert that the handle URLs contain no substrate nouns."""
    for url in (handle.control_url, handle.terminal_url):
        for forbidden in _FORBIDDEN_SUBSTRINGS:
            assert forbidden not in url, (
                f"URL {url!r} contains forbidden substring {forbidden!r}"
            )
        assert machine_id not in url, (
            f"URL {url!r} contains machine_id {machine_id!r}"
        )


# ---------------------------------------------------------------------------
# _make_handle unit tests
# ---------------------------------------------------------------------------


def test_make_handle_opaque_urls():
    """_make_handle returns opaque URLs with no substrate nouns."""
    machine_id = "abc123machineXYZ"
    handle = _make_handle("proj-1", machine_id)

    assert handle.control_url.startswith("https://rt.")
    assert handle.terminal_url.startswith("wss://rt.")
    _assert_opaque(handle, machine_id)


def test_make_handle_stable():
    """Same inputs → same URLs (deterministic)."""
    h1 = _make_handle("proj-1", "machine-abc")
    h2 = _make_handle("proj-1", "machine-abc")
    assert h1 == h2


def test_make_handle_different_projects():
    """Different project_ids → different URLs."""
    h1 = _make_handle("proj-A", "machine-1")
    h2 = _make_handle("proj-B", "machine-1")
    assert h1.control_url != h2.control_url
    assert h1.terminal_url != h2.terminal_url


# ---------------------------------------------------------------------------
# FlyProvider.start() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fly_provider_start_returns_opaque_handle():
    """start() returns a WorkspaceHandle with opaque URLs — no Fly/machine_id nouns."""
    machine_id = "abcdef1234567890"
    create_resp = _mock_response(200, {"id": machine_id, "state": "created"})
    start_resp = _mock_response(200, {})
    client = _make_client(post_side_effects=[create_resp, start_resp])

    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)
    handle = await provider.start("proj-1", "https://github.com/x/y", None, "claude")

    assert isinstance(handle, WorkspaceHandle)
    _assert_opaque(handle, machine_id)
    # Verify URL shape
    assert "rt." in handle.control_url
    assert ".example/control/" in handle.control_url
    assert ".example/terminal/" in handle.terminal_url


@pytest.mark.asyncio
async def test_fly_provider_start_timeout_raises_proxy_down():
    """start() → Fly API timeout → ProxyDownError (provider_unreachable)."""
    client = _make_client(
        post_side_effects=[httpx.ConnectError("connection refused")]
    )
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    with pytest.raises(ProxyDownError):
        await provider.start("proj-1", "https://github.com/x/y", None, "claude")


@pytest.mark.asyncio
async def test_fly_provider_start_timeout_exception_raises_proxy_down():
    """start() → httpx.TimeoutException → ProxyDownError."""
    client = _make_client(
        post_side_effects=[httpx.TimeoutException("read timeout")]
    )
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    with pytest.raises(ProxyDownError):
        await provider.start("proj-1", "https://github.com/x/y", None, "claude")


@pytest.mark.asyncio
async def test_fly_provider_start_5xx_raises_proxy_down():
    """start() → Fly API 5xx → ProxyDownError."""
    create_resp = _mock_response(503, {"error": "service unavailable"})
    client = _make_client(post_side_effects=[create_resp])

    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    with pytest.raises(ProxyDownError):
        await provider.start("proj-1", "https://github.com/x/y", None, "claude")


@pytest.mark.asyncio
async def test_fly_provider_start_4xx_raises_cage_error():
    """start() → Fly API 4xx (non-policy) → CageError."""
    create_resp = _mock_response(400, {"error": "bad request"})
    client = _make_client(post_side_effects=[create_resp])

    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    with pytest.raises(CageError):
        await provider.start("proj-1", "https://github.com/x/y", None, "claude")


# ---------------------------------------------------------------------------
# FlyProvider.health() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fly_provider_health_ok():
    """health() → Fly API 200 → ProviderHealth.ok."""
    list_resp = _mock_response(200, [])
    client = _make_client(get_side_effects=[list_resp])
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    result = await provider.health()

    assert result == ProviderHealth.ok


@pytest.mark.asyncio
async def test_fly_provider_health_degraded_on_4xx():
    """health() → Fly API 4xx → ProviderHealth.degraded."""
    list_resp = _mock_response(403, {"error": "forbidden"})
    client = _make_client(get_side_effects=[list_resp])
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    result = await provider.health()

    assert result == ProviderHealth.degraded


@pytest.mark.asyncio
async def test_fly_provider_health_unavailable_on_5xx():
    """health() → Fly API 5xx → ProviderHealth.unavailable."""
    list_resp = _mock_response(500, {"error": "internal error"})
    client = _make_client(get_side_effects=[list_resp])
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    result = await provider.health()

    assert result == ProviderHealth.unavailable


@pytest.mark.asyncio
async def test_fly_provider_health_unavailable_on_network_error():
    """health() → network error → ProviderHealth.unavailable."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    result = await provider.health()

    assert result == ProviderHealth.unavailable


@pytest.mark.asyncio
async def test_fly_provider_health_unavailable_on_timeout():
    """health() → timeout → ProviderHealth.unavailable."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    provider = FlyProvider(api_token="tok", app_name="my-app", http_client=client)

    result = await provider.health()

    assert result == ProviderHealth.unavailable
