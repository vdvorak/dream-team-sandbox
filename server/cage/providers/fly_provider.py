"""FlyProvider — Fly.io Machines API adapter for CageRuntimeProvider (RCP-A9).

ALL Fly-specific details are CONTAINED HERE and MUST NOT leak through the
CageRuntimeProvider interface:
  - Fly API base URL and endpoints
  - Machine IDs
  - fly.io hostnames, 6PN addresses, .internal suffixes
  - FLY_API_TOKEN

WHY opaque URLs (RCP-A6 E):
  The caller (CageEnforcementProvider) receives WorkspaceHandle.control_url and
  terminal_url and passes them unchanged to ConnectionHandle. Neither the service nor
  the client should be able to infer the substrate from these URLs.

  opaque_id  = SHA-256(project_id)[:12]      — stable, short, not guessable
  opaque_token = SHA-256(project_id:machine_id)[:24] — stable per (project, machine)

  URL shape:
    control:  https://rt.<opaque_id>.example/control/<opaque_token>
    terminal: wss://rt.<opaque_id>.example/terminal/<opaque_token>

  None of: fly, Fly, .internal, 6PN, :808x, machine_id appear in the URLs.

httpx.AsyncClient is injected via the constructor so tests can pass a mock client
without making real network calls (RCP-A9).
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import httpx

from server.cage.errors import (
    CageError,
    NoPolicyError,
    PolicyApplyFailedError,
    ProxyDownError,
)
from server.cage.runtime import WorkspaceHandle, WorkspaceStatus
from server.runtime.enforcement.provider import ProviderHealth

logger = logging.getLogger(__name__)

# Fly Machines API base URL (all requests start here).
_FLY_API_BASE = "https://api.machines.dev/v1"

# Mapping from Fly machine state to our WorkspaceStatus enum.
_FLY_STATE_MAP: dict[str, WorkspaceStatus] = {
    "started": WorkspaceStatus.ready,
    "stopped": WorkspaceStatus.stopped,
    "created": WorkspaceStatus.starting,
    "destroyed": WorkspaceStatus.stopped,
}


def _opaque_id(project_id: str) -> str:
    """Derive a short opaque identifier from project_id (12 hex chars of SHA-256)."""
    return hashlib.sha256(project_id.encode()).hexdigest()[:12]


def _opaque_token(project_id: str, machine_id: str) -> str:
    """Derive a stable opaque token from (project_id, machine_id) (24 hex chars)."""
    return hashlib.sha256(f"{project_id}:{machine_id}".encode()).hexdigest()[:24]


def _make_handle(project_id: str, machine_id: str) -> WorkspaceHandle:
    """Produce an opaque WorkspaceHandle — no Fly noun, no machine ID in URLs.

    Verified invariant: the returned URLs do NOT contain any of:
    'fly', 'Fly', '.internal', '6PN', machine_id, ':808'
    """
    oid = _opaque_id(project_id)
    token = _opaque_token(project_id, machine_id)
    return WorkspaceHandle(
        control_url=f"https://rt.{oid}.example/control/{token}",
        terminal_url=f"wss://rt.{oid}.example/terminal/{token}",
    )


class FlyProvider:
    """Fly.io Machines API adapter implementing CageRuntimeProvider (RCP-A9).

    Usage:
        provider = FlyProvider(api_token="<token>", app_name="<app>")
        handle = await provider.start(project_id, repo_url, ref, tool)

    For testing, pass a pre-configured httpx.AsyncClient mock:
        provider = FlyProvider(api_token="x", app_name="test", http_client=mock_client)
    """

    def __init__(
        self,
        api_token: str | None = None,
        app_name: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_token = api_token or os.environ.get("FLY_API_TOKEN", "")
        self._app_name = app_name or os.environ.get("FLY_APP_NAME", "")
        # Shared client — created once to enable TCP connection reuse.
        # Injected for testability (avoids real network calls in unit tests).
        self._http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    # --- internal helpers ---

    def _url(self, *parts: str) -> str:
        """Build a Fly API URL from path segments."""
        path = "/".join(parts)
        return f"{_FLY_API_BASE}/{path}"

    def _client(self) -> httpx.AsyncClient:
        """Return the shared AsyncClient instance."""
        return self._http_client

    def _translate_error(self, exc: Exception) -> CageError:
        """Translate httpx errors to CageError subclasses.

        - ConnectError / TimeoutException → ProxyDownError (network/availability)
        - Other HTTP errors → CageError (generic)
        """
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            return ProxyDownError(f"Fly API unreachable: {exc}")
        return CageError(f"Fly API error: {exc}")

    def _check_status_code(self, response: httpx.Response) -> None:
        """Raise a CageError if the response indicates failure.

        - 4xx (non-policy)  → CageError
        - 403 / 422 (policy-like) → PolicyApplyFailedError or NoPolicyError
        - 5xx → ProxyDownError (Fly infrastructure issue)
        """
        if response.status_code < 400:
            return  # success
        if response.status_code in (403, 422):
            raise PolicyApplyFailedError(
                f"Fly API policy error {response.status_code}: {response.text}"
            )
        if response.status_code >= 500:
            raise ProxyDownError(
                f"Fly API server error {response.status_code}: {response.text}"
            )
        # 4xx other
        raise CageError(
            f"Fly API client error {response.status_code}: {response.text}"
        )

    # --- CageRuntimeProvider implementation ---

    async def start(
        self,
        project_id: str,
        repo_url: str,
        ref: str | None,
        tool: str,
    ) -> WorkspaceHandle:
        """Create and start a Fly Machine for the workspace, return opaque handle.

        Steps:
          1. POST /apps/{app_name}/machines — create machine
          2. POST /apps/{app_name}/machines/{id}/start — start it
          3. Return opaque WorkspaceHandle (no Fly nouns)

        All CageError subclasses propagate to the caller (CageEnforcementProvider).
        """
        client = self._client()
        machine_payload: dict[str, Any] = {
            "config": {
                "env": {
                    "PROJECT_ID": project_id,
                    "REPO_URL": repo_url,
                    "REPO_REF": ref or "",
                    "TOOL": tool,
                },
                "image": "registry.fly.io/workspace:latest",
            }
        }
        try:
            # 1. Create machine
            create_resp = await client.post(
                self._url("apps", self._app_name, "machines"),
                headers=self._headers,
                json=machine_payload,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        self._check_status_code(create_resp)
        machine_data = create_resp.json()
        machine_id: str = machine_data["id"]

        logger.debug(
            "fly_provider.start: created machine machine_id=%s project_id=%s",
            machine_id,
            project_id,
        )

        try:
            # 2. Start machine
            start_resp = await client.post(
                self._url("apps", self._app_name, "machines", machine_id, "start"),
                headers=self._headers,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        self._check_status_code(start_resp)

        logger.info(
            "fly_provider.start: machine started project_id=%s",
            project_id,
        )

        # 3. Return opaque handle — machine_id is used only to compute the opaque token,
        #    and never appears in the returned URLs.
        return _make_handle(project_id, machine_id)

    async def stop(self, project_id: str) -> None:
        """Stop the Fly Machine for the given project.

        NOTE: In this implementation we look up the machine by listing all machines
        and finding one with a matching PROJECT_ID env label. Idempotent if not found.
        """
        client = self._client()
        try:
            list_resp = await client.get(
                self._url("apps", self._app_name, "machines"),
                headers=self._headers,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        self._check_status_code(list_resp)
        machines = list_resp.json()

        # Find machine for this project_id (match env label).
        machine_id: str | None = None
        for m in machines:
            env = (m.get("config") or {}).get("env") or {}
            if env.get("PROJECT_ID") == project_id:
                machine_id = m["id"]
                break

        if machine_id is None:
            logger.debug(
                "fly_provider.stop: no machine found for project_id=%s (idempotent)",
                project_id,
            )
            return

        try:
            stop_resp = await client.post(
                self._url("apps", self._app_name, "machines", machine_id, "stop"),
                headers=self._headers,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        self._check_status_code(stop_resp)
        logger.info("fly_provider.stop: machine stopped project_id=%s", project_id)

    async def status(self, project_id: str) -> WorkspaceStatus:
        """Return current WorkspaceStatus for project_id by querying Fly.

        Returns WorkspaceStatus.unknown if no machine is found.
        """
        client = self._client()
        try:
            list_resp = await client.get(
                self._url("apps", self._app_name, "machines"),
                headers=self._headers,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        self._check_status_code(list_resp)
        machines = list_resp.json()

        for m in machines:
            env = (m.get("config") or {}).get("env") or {}
            if env.get("PROJECT_ID") == project_id:
                fly_state = m.get("state", "")
                return _FLY_STATE_MAP.get(fly_state, WorkspaceStatus.unknown)

        return WorkspaceStatus.unknown

    async def health(self) -> ProviderHealth:
        """Check Fly API health by listing machines.

        - HTTP 2xx → ok
        - HTTP 5xx → unavailable
        - Network/timeout error → unavailable
        - Other 4xx → degraded (API reachable but issue)
        """
        client = self._client()
        try:
            resp = await client.get(
                self._url("apps", self._app_name, "machines"),
                headers=self._headers,
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            logger.warning("fly_provider.health: Fly API unreachable")
            return ProviderHealth.unavailable
        except Exception:
            logger.warning("fly_provider.health: unexpected error")
            return ProviderHealth.unavailable

        if resp.status_code < 300:
            return ProviderHealth.ok
        if resp.status_code >= 500:
            return ProviderHealth.unavailable
        # 4xx — API reachable but something is wrong (auth, etc.)
        return ProviderHealth.degraded
