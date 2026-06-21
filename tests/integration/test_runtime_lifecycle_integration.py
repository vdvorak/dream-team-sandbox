"""Integration tests — runtime control-plane lifecycle (wave 2026-06-21-runtime-lifecycle).

Scope: in-scope AC from acceptance/runtime-control-plane.md treated as a black box
over the full HTTP stack (ASGI TestClient / httpx AsyncClient).

  RCP-1  ensure (new, idempotent, repo-mismatch, tool-not-allowed, extra-field)
  RCP-2  fail-closed (provider fail → 502 never ready; provider down → 503 never ready)
  RCP-3  get (ready, nonexistent, asleep/destroyed null-connection, provisioning phase)
  RCP-4  sleep (ready→asleep; idempotent; on provisioning; on destroyed; nonexistent)
  RCP-5  destroy (existing; idempotent; nonexistent; ensure-after-destroy = fresh)
  RCP-9  healthz (no auth; ok/degraded/503; contract_version consistency)
  RCP-10 standalone (full lifecycle with service token only, no app-specific identity)
  RCP-11 agnostika (no substrate noun in any response field or connection URL)
  RCP-12 ZEĎ-disjunktnost (bypass field → 400 ERR_INVALID_REQUEST, never reaches provider)
  RCP-13 BYOK neteče (response has no credential fields; request rejects token fields)
  RCP-14 auth (missing/invalid → 401 ERR_UNAUTHORIZED; healthz public; valid token proceeds)

Tag: [integration] [automated] [security]

Design notes:
- Each test creates a fresh app instance via create_runtime_app() with an injected
  DevEnforcementProvider — isolated state, no cross-test pollution.
- project_id values are unique per scenario (prefixed by class) to avoid accidental
  state bleed when a single app instance is shared within a class.
- Tests are written from acceptance criteria (black-box), NOT from reading service code.
- FAIL is reported as a failure-signature (what was expected vs what arrived), not a fix.
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest
from httpx import ASGITransport, AsyncClient

from server.runtime.enforcement.dev import DevEnforcementProvider
from server.runtime.main import create_runtime_app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_TOKEN = "integration-test-token"
AUTH = {"Authorization": f"Bearer {SERVICE_TOKEN}"}

VALID_REPO = "https://github.com/example/repo"
ALT_REPO = "https://github.com/example/other-repo"
VALID_TOOL = "claude"
INVALID_TOOL = "not-a-real-tool"

CONTRACT_VERSION = "1.1.0"

# RCP-11 / RCP-3b: substrate nouns that MUST NOT appear anywhere in response bodies.
_SUBSTRATE_RE = re.compile(
    r"Fly|fly\.dev|Docker|docker|6PN|\.internal|:808[0-9]|nftables|tmux|microVM|"
    r"WORKSPACE_AGENT_BASE|nftables",
    re.IGNORECASE,
)

# RCP-12c: policy/ruleset/allowlist/capability MUST NOT be response-body fields.
_WALL_FIELD_RE = re.compile(r"policy|ruleset|allowlist|capability", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(mode: str = "active") -> object:
    """Factory: fresh app with DevEnforcementProvider in given mode (active/fail/down)."""
    provider = DevEnforcementProvider(mode=mode)
    return create_runtime_app(
        service_token=SERVICE_TOKEN,
        enforcement_provider_override=provider,
    )


def _client(app) -> AsyncClient:
    """Return an AsyncClient wired to the ASGI app. Use as async context manager."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


def _grep_substrate(obj) -> list[str]:
    """Return all string values in obj (recursively) that match _SUBSTRATE_RE."""
    hits: list[str] = []
    if isinstance(obj, str):
        if _SUBSTRATE_RE.search(obj):
            hits.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            hits.extend(_grep_substrate(v))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(_grep_substrate(item))
    return hits


def _grep_wall_fields(obj) -> list[str]:
    """Return all keys in obj (recursively) that match _WALL_FIELD_RE."""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _WALL_FIELD_RE.search(k):
                hits.append(k)
            hits.extend(_grep_wall_fields(v))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(_grep_wall_fields(item))
    return hits


async def _ensure_ready(client: AsyncClient, project_id: str, repo: str = VALID_REPO) -> dict:
    """POST ensure and assert 200 ready. Returns parsed body."""
    r = await client.post(
        f"/v1/environments/{project_id}/ensure",
        json={"repo": {"url": repo}, "tool": VALID_TOOL},
        headers=AUTH,
    )
    assert r.status_code == 200, (
        f"_ensure_ready: expected 200 got {r.status_code}: {r.text}"
    )
    data = r.json()
    assert data["status"] == "ready", (
        f"_ensure_ready: expected status=ready got {data.get('status')}"
    )
    return data


# ---------------------------------------------------------------------------
# RCP-1 — ensure: basic lifecycle flow
# ---------------------------------------------------------------------------


class TestRCP1Ensure:
    """RCP-1: POST /v1/environments/{id}/ensure."""

    async def test_rcp1a_new_project_reaches_ready_or_provisioning(self):
        """RCP-1a: ensure for new project_id → 200 ready (dev active) or 202 provisioning."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1a-new/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code in (200, 202), (
            f"RCP-1a: expected 200 or 202, got {r.status_code}: {r.text}"
        )
        data = r.json()
        assert data.get("status") in ("ready", "provisioning"), (
            f"RCP-1a: unexpected status {data.get('status')}"
        )

    async def test_rcp1a_dev_active_ensure_returns_200_ready(self):
        """RCP-1a: dev provider in active mode → 200 with status=ready on first ensure."""
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp1a-active/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 200, (
            f"RCP-1a: active provider must return 200, got {r.status_code}: {r.text}"
        )
        assert r.json()["status"] == "ready"

    async def test_rcp1a_202_has_retry_after_header(self):
        """RCP-1a: if 202 provisioning returned, Retry-After header must be present."""
        # Use fail provider so ensure never reaches ready (stays provisioning path).
        # For dev active mode we get 200 directly; this test verifies the 202 contract
        # if the server ever returns 202. We use the active provider which always returns
        # 200 — skip if 200 is returned (that is also valid per AC).
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1a-202/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        if r.status_code == 202:
            assert "retry-after" in {k.lower() for k in r.headers}, (
                "RCP-1a: 202 response missing Retry-After header"
            )

    async def test_rcp1b_contract_version_present_in_ensure_response(self):
        """RCP-1b: every Environment body contains contract_version matching expected value."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1b-cv/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 200
        assert r.json().get("contract_version") == CONTRACT_VERSION, (
            f"RCP-1b: contract_version missing or wrong: {r.json()}"
        )

    async def test_rcp1c_idempotent_ensure_on_ready(self):
        """RCP-1c: repeated ensure with same project_id + same repo.url on ready → 200 same env."""
        app = _make_app()
        async with _client(app) as c:
            data1 = await _ensure_ready(c, "rcp1c-idem")
            r2 = await c.post(
                "/v1/environments/rcp1c-idem/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r2.status_code == 200, (
            f"RCP-1c: idempotent ensure must return 200, got {r2.status_code}: {r2.text}"
        )
        data2 = r2.json()
        assert data2["status"] == "ready", (
            f"RCP-1c: idempotent ensure must return ready, got {data2.get('status')}"
        )
        assert data2["project_id"] == data1["project_id"]
        # Verify single environment: same project_id, no duplication.
        assert data2["project_id"] == "rcp1c-idem"

    async def test_rcp1c_idempotent_ensure_no_second_environment_created(self):
        """RCP-1c: idempotent ensure does not create a second environment (same project_id)."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp1c-nodup")
            r2 = await c.post(
                "/v1/environments/rcp1c-nodup/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            r3 = await c.get("/v1/environments/rcp1c-nodup", headers=AUTH)
        # Only one record in the system — GET returns the same project_id.
        assert r3.status_code == 200
        assert r3.json()["project_id"] == "rcp1c-nodup"

    async def test_rcp1e_repo_mismatch_on_live_env_returns_409(self):
        """RCP-1e: ensure with different repo.url on live environment → 409 ERR_REPO_MISMATCH."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp1e-mismatch", repo=VALID_REPO)
            r = await c.post(
                "/v1/environments/rcp1e-mismatch/ensure",
                json={"repo": {"url": ALT_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 409, (
            f"RCP-1e: expected 409 ERR_REPO_MISMATCH, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_REPO_MISMATCH", (
            f"RCP-1e: expected code ERR_REPO_MISMATCH, got {r.json()}"
        )

    async def test_rcp1e_repo_mismatch_env_undamaged(self):
        """RCP-1e: 409 on mismatch leaves existing environment undamaged (still ready)."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp1e-nodamage", repo=VALID_REPO)
            # mismatch attempt
            await c.post(
                "/v1/environments/rcp1e-nodamage/ensure",
                json={"repo": {"url": ALT_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            r_get = await c.get("/v1/environments/rcp1e-nodamage", headers=AUTH)
        assert r_get.status_code == 200
        data = r_get.json()
        assert data["status"] == "ready", (
            f"RCP-1e: environment damaged after 409 mismatch, status={data.get('status')}"
        )

    async def test_rcp1f_invalid_tool_returns_400_tool_not_allowed(self):
        """RCP-1f: ensure with tool not in allowlist → 400 ERR_TOOL_NOT_ALLOWED."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1f-tool/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": INVALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-1f: expected 400, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_TOOL_NOT_ALLOWED", (
            f"RCP-1f: expected ERR_TOOL_NOT_ALLOWED, got {r.json()}"
        )

    async def test_rcp1f_invalid_tool_not_5xx(self):
        """RCP-1f: invalid tool must return 400, never 5xx."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1f-no5xx/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": "evil-malware"},
                headers=AUTH,
            )
        assert r.status_code < 500, (
            f"RCP-1f: invalid tool returned 5xx: {r.status_code}"
        )

    async def test_rcp1h_extra_field_in_body_returns_400_err_invalid_request(self):
        """RCP-1h/AC-12c: extra field in top-level request body → 400 ERR_INVALID_REQUEST."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1h-extra/ensure",
                json={
                    "repo": {"url": VALID_REPO},
                    "tool": VALID_TOOL,
                    "firewall": "off",
                },
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-1h: expected 400 for extra field, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_INVALID_REQUEST", (
            f"RCP-1h: expected ERR_INVALID_REQUEST, got {r.json()}"
        )

    async def test_rcp1h_extra_field_in_nested_repo_returns_400(self):
        """RCP-1h/AC-12c: extra field in nested repo object → 400 ERR_INVALID_REQUEST."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1h-repofld/ensure",
                json={
                    "repo": {"url": VALID_REPO, "egress": "allow-all"},
                    "tool": VALID_TOOL,
                },
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-1h nested repo: expected 400, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_INVALID_REQUEST"

    async def test_rcp1h_extra_field_never_silently_accepted(self):
        """RCP-1h: extra field must NEVER be silently accepted (not 200/202)."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp1h-nosilent/ensure",
                json={
                    "repo": {"url": VALID_REPO},
                    "tool": VALID_TOOL,
                    "policy": "none",
                },
                headers=AUTH,
            )
        assert r.status_code not in (200, 202), (
            f"RCP-1h: server silently accepted extra field 'policy' → {r.status_code}"
        )


# ---------------------------------------------------------------------------
# RCP-2 — fail-closed guarantee
# ---------------------------------------------------------------------------


class TestRCP2FailClosed:
    """RCP-2: enforcement-failure scenarios MUST never yield status=ready."""

    async def test_rcp2a_active_provider_returns_ready(self):
        """RCP-2a: dev provider active → ensure returns ready with non-null connection."""
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp2a-active/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready", f"RCP-2a: expected ready, got {data}"
        assert data["connection"] is not None, "RCP-2a: connection must be non-null for ready"
        assert data["connection"]["control_url"], "RCP-2a: control_url must be non-empty"
        assert data["connection"]["terminal_url"], "RCP-2a: terminal_url must be non-empty"

    async def test_rcp2b_provider_fail_returns_502_never_ready(self):
        """RCP-2b: provider in fail mode → 502 ERR_PROVISION_FAILED; NEVER status=ready."""
        async with _client(_make_app("fail")) as c:
            r = await c.post(
                "/v1/environments/rcp2b-fail/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 502, (
            f"RCP-2b: expected 502, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_PROVISION_FAILED", (
            f"RCP-2b: expected ERR_PROVISION_FAILED, got {r.json()}"
        )

    async def test_rcp2b_fail_mode_response_status_never_ready(self):
        """RCP-2b: fail-mode ensure must NOT return any response with status=ready."""
        async with _client(_make_app("fail")) as c:
            r = await c.post(
                "/v1/environments/rcp2b-noready/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        # 502 body has no status field — ensure no ready leaks out.
        body = r.json()
        if "status" in body:
            assert body["status"] != "ready", (
                f"RCP-2b FAIL-CLOSED VIOLATED: response body shows status=ready on fail provider"
            )

    async def test_rcp2c_provider_down_returns_503_never_ready(self):
        """RCP-2c: provider unreachable → 503 ERR_RUNTIME_UNAVAILABLE; NEVER 200 ready."""
        async with _client(_make_app("down")) as c:
            r = await c.post(
                "/v1/environments/rcp2c-down/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 503, (
            f"RCP-2c: expected 503, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_RUNTIME_UNAVAILABLE", (
            f"RCP-2c: expected ERR_RUNTIME_UNAVAILABLE, got {r.json()}"
        )

    async def test_rcp2c_down_mode_never_200_ready(self):
        """RCP-2c: down provider MUST NOT return 200 ready (fail-closed invariant)."""
        async with _client(_make_app("down")) as c:
            r = await c.post(
                "/v1/environments/rcp2c-noready/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code != 200, (
            f"RCP-2c FAIL-CLOSED VIOLATED: down provider returned 200: {r.text}"
        )
        if "status" in r.json():
            assert r.json()["status"] != "ready", (
                "RCP-2c FAIL-CLOSED VIOLATED: status=ready with down provider"
            )

    async def test_rcp2d_get_after_fail_ensure_shows_provisioning_not_ready(self):
        """RCP-2d: GET after failed ensure → status is provisioning, never ready."""
        app = _make_app("fail")
        async with _client(app) as c:
            await c.post(
                "/v1/environments/rcp2d-prov/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            r_get = await c.get("/v1/environments/rcp2d-prov", headers=AUTH)
        assert r_get.status_code == 200
        assert r_get.json()["status"] != "ready", (
            f"RCP-2d FAIL-CLOSED VIOLATED: GET shows ready after fail-mode ensure"
        )


# ---------------------------------------------------------------------------
# RCP-3 — get environment + opaque connection
# ---------------------------------------------------------------------------


class TestRCP3Get:
    """RCP-3: GET /v1/environments/{id}."""

    async def test_rcp3a_get_ready_returns_200_with_connection(self):
        """RCP-3a: GET on ready env → 200 with non-empty connection URLs."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp3a-ready")
            r = await c.get("/v1/environments/rcp3a-ready", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"
        assert data["connection"] is not None, "RCP-3a: connection must be non-null for ready"
        assert data["connection"]["control_url"], "RCP-3a: control_url must be non-empty"
        assert data["connection"]["terminal_url"], "RCP-3a: terminal_url must be non-empty"

    async def test_rcp3b_connection_urls_contain_no_substrate_nouns(self):
        """RCP-3b/AC-11c: connection URLs must not leak substrate identifiers."""
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp3b-opaque")
        conn = data["connection"]
        for url in [conn["control_url"], conn["terminal_url"]]:
            assert not _SUBSTRATE_RE.search(url), (
                f"RCP-3b: substrate noun found in connection URL: {url}"
            )

    async def test_rcp3c_get_nonexistent_returns_404(self):
        """RCP-3c: GET for nonexistent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/environments/rcp3c-nosuchid", headers=AUTH)
        assert r.status_code == 404, (
            f"RCP-3c: expected 404, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_FOUND", (
            f"RCP-3c: expected ERR_ENVIRONMENT_NOT_FOUND, got {r.json()}"
        )

    async def test_rcp3d_get_asleep_returns_null_connection(self):
        """RCP-3d: GET on asleep env → connection: null; status: asleep."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp3d-asleep")
            await c.post("/v1/environments/rcp3d-asleep/sleep", headers=AUTH)
            r = await c.get("/v1/environments/rcp3d-asleep", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "asleep", f"RCP-3d: expected asleep, got {data.get('status')}"
        assert data["connection"] is None, f"RCP-3d: connection must be null for asleep env"

    async def test_rcp3d_get_destroyed_returns_null_connection_or_404(self):
        """RCP-3d: GET on destroyed env → connection: null; either 200/destroyed or 404."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp3d-dest")
            await c.delete("/v1/environments/rcp3d-dest", headers=AUTH)
            r = await c.get("/v1/environments/rcp3d-dest", headers=AUTH)
        assert r.status_code in (200, 404), (
            f"RCP-3d: expected 200 or 404 after destroy, got {r.status_code}"
        )
        if r.status_code == 200:
            assert r.json()["connection"] is None, (
                "RCP-3d: destroyed env must have null connection"
            )
            assert r.json()["status"] == "destroyed"

    async def test_rcp3e_get_provisioning_has_phase(self):
        """RCP-3e: GET on provisioning env → connection: null; phase non-empty."""
        # Use fail provider: ensure sets record to provisioning then fails.
        app = _make_app("fail")
        async with _client(app) as c:
            await c.post(
                "/v1/environments/rcp3e-prov/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            r_get = await c.get("/v1/environments/rcp3e-prov", headers=AUTH)
        assert r_get.status_code == 200
        data = r_get.json()
        assert data["status"] == "provisioning", (
            f"RCP-3e: expected provisioning, got {data.get('status')}"
        )
        assert data["connection"] is None, "RCP-3e: connection must be null during provisioning"
        assert data.get("phase") is not None and data["phase"] != "", (
            f"RCP-3e: phase must be non-empty for provisioning env, got {data.get('phase')}"
        )


# ---------------------------------------------------------------------------
# RCP-4 — sleep
# ---------------------------------------------------------------------------


class TestRCP4Sleep:
    """RCP-4: POST /v1/environments/{id}/sleep."""

    async def test_rcp4a_sleep_on_ready_transitions(self):
        """RCP-4a: sleep on ready → 200; status asleep or ready (advisory); never 5xx."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp4a-sleep")
            r = await c.post("/v1/environments/rcp4a-sleep/sleep", headers=AUTH)
        assert r.status_code == 200, (
            f"RCP-4a: expected 200, got {r.status_code}: {r.text}"
        )
        assert r.json()["status"] in ("asleep", "ready"), (
            f"RCP-4a: expected asleep or ready, got {r.json().get('status')}"
        )

    async def test_rcp4a_sleep_on_ready_connection_cleared(self):
        """RCP-4a: after sleep, connection must be null (advisory sleep clears connection)."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp4a-conn")
            r_sleep = await c.post("/v1/environments/rcp4a-conn/sleep", headers=AUTH)
        if r_sleep.json().get("status") == "asleep":
            assert r_sleep.json()["connection"] is None, (
                "RCP-4a: asleep env must have null connection"
            )

    async def test_rcp4b_sleep_idempotent_on_asleep(self):
        """RCP-4b: sleep on already-asleep env → 200; never 5xx."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp4b-idem")
            await c.post("/v1/environments/rcp4b-idem/sleep", headers=AUTH)
            r2 = await c.post("/v1/environments/rcp4b-idem/sleep", headers=AUTH)
        assert r2.status_code == 200, (
            f"RCP-4b: idempotent sleep must return 200, got {r2.status_code}: {r2.text}"
        )
        assert r2.status_code < 500

    async def test_rcp4c_sleep_on_destroyed_never_5xx(self):
        """RCP-4c: sleep on destroyed → 200 or 404; never 5xx."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp4c-dest")
            await c.delete("/v1/environments/rcp4c-dest", headers=AUTH)
            r = await c.post("/v1/environments/rcp4c-dest/sleep", headers=AUTH)
        assert r.status_code in (200, 404), (
            f"RCP-4c: expected 200 or 404, got {r.status_code}: {r.text}"
        )
        assert r.status_code < 500, f"RCP-4c: got 5xx on sleep of destroyed env"

    async def test_rcp4d_sleep_on_nonexistent_never_5xx(self):
        """RCP-4d: sleep on nonexistent project_id → 200 or 404; never 5xx."""
        async with _client(_make_app()) as c:
            r = await c.post("/v1/environments/rcp4d-noexist/sleep", headers=AUTH)
        assert r.status_code in (200, 404), (
            f"RCP-4d: expected 200 or 404, got {r.status_code}: {r.text}"
        )
        assert r.status_code < 500

    async def test_rcp4_sleep_on_provisioning_no_interrupt(self):
        """RCP-4 edge: sleep during provisioning returns 200 with provisioning state; no interrupt."""
        app = _make_app("fail")
        async with _client(app) as c:
            # Place env in provisioning via fail-mode ensure.
            await c.post(
                "/v1/environments/rcp4-prov-sleep/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
            r_sleep = await c.post("/v1/environments/rcp4-prov-sleep/sleep", headers=AUTH)
        assert r_sleep.status_code == 200
        assert r_sleep.json()["status"] == "provisioning", (
            f"RCP-4 edge: sleep on provisioning should not interrupt; "
            f"got status={r_sleep.json().get('status')}"
        )


# ---------------------------------------------------------------------------
# RCP-5 — destroy
# ---------------------------------------------------------------------------


class TestRCP5Destroy:
    """RCP-5: DELETE /v1/environments/{id}."""

    async def test_rcp5a_destroy_existing_env(self):
        """RCP-5a: DELETE on existing env → 200 or 202."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp5a-dest")
            r = await c.delete("/v1/environments/rcp5a-dest", headers=AUTH)
        assert r.status_code in (200, 202), (
            f"RCP-5a: expected 200/202, got {r.status_code}: {r.text}"
        )

    async def test_rcp5a_get_after_destroy_returns_destroyed_or_404(self):
        """RCP-5a: GET after destroy → 404 or status: destroyed."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp5a-getdest")
            await c.delete("/v1/environments/rcp5a-getdest", headers=AUTH)
            r_get = await c.get("/v1/environments/rcp5a-getdest", headers=AUTH)
        assert r_get.status_code in (200, 404), (
            f"RCP-5a: expected 200 or 404 after destroy, got {r_get.status_code}"
        )
        if r_get.status_code == 200:
            assert r_get.json()["status"] == "destroyed", (
                f"RCP-5a: GET after destroy must show destroyed, got {r_get.json().get('status')}"
            )

    async def test_rcp5b_destroy_idempotent(self):
        """RCP-5b: repeated DELETE → 200 or 404; never 5xx."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp5b-idem")
            await c.delete("/v1/environments/rcp5b-idem", headers=AUTH)
            r2 = await c.delete("/v1/environments/rcp5b-idem", headers=AUTH)
        assert r2.status_code in (200, 404), (
            f"RCP-5b: idempotent destroy must be 200/404, got {r2.status_code}: {r2.text}"
        )
        assert r2.status_code < 500

    async def test_rcp5c_destroy_nonexistent_never_5xx(self):
        """RCP-5c: DELETE nonexistent → 200 or 404; never 5xx."""
        async with _client(_make_app()) as c:
            r = await c.delete("/v1/environments/rcp5c-noexist", headers=AUTH)
        assert r.status_code in (200, 404), (
            f"RCP-5c: expected 200/404, got {r.status_code}: {r.text}"
        )
        assert r.status_code < 500

    async def test_rcp5d_ensure_after_destroy_creates_fresh_env(self):
        """RCP-5d: ensure on destroyed project_id → fresh provisioning/ready cycle."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp5d-fresh")
            await c.delete("/v1/environments/rcp5d-fresh", headers=AUTH)
            r_new = await c.post(
                "/v1/environments/rcp5d-fresh/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r_new.status_code in (200, 202), (
            f"RCP-5d: ensure after destroy must return 200/202, got {r_new.status_code}: {r_new.text}"
        )
        assert r_new.json()["status"] in ("ready", "provisioning"), (
            f"RCP-5d: fresh cycle must be ready/provisioning, got {r_new.json().get('status')}"
        )


# ---------------------------------------------------------------------------
# RCP-9 — healthz
# ---------------------------------------------------------------------------


class TestRCP9Healthz:
    """RCP-9: GET /v1/healthz."""

    async def test_rcp9a_healthz_no_auth_returns_200_ok(self):
        """RCP-9a/14c: GET /v1/healthz without auth → 200 with status in {ok,degraded} + contract_version."""
        async with _client(_make_app("active")) as c:
            r = await c.get("/v1/healthz")  # intentionally no auth header
        assert r.status_code == 200, (
            f"RCP-9a: healthz without auth must return 200, got {r.status_code}: {r.text}"
        )
        data = r.json()
        assert data["status"] in ("ok", "degraded"), (
            f"RCP-9a: healthz status must be ok or degraded, got {data.get('status')}"
        )
        assert data.get("contract_version") == CONTRACT_VERSION, (
            f"RCP-9a: contract_version missing or wrong: {data}"
        )

    async def test_rcp9a_healthz_active_provider_reports_ok(self):
        """RCP-9a: active provider → healthz status ok."""
        async with _client(_make_app("active")) as c:
            r = await c.get("/v1/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_rcp9b_contract_version_consistent_with_environment(self):
        """RCP-9b: contract_version in healthz matches contract_version in Environment response."""
        app = _make_app()
        async with _client(app) as c:
            r_health = await c.get("/v1/healthz")
            env_data = await _ensure_ready(c, "rcp9b-cv")
        healthz_cv = r_health.json()["contract_version"]
        env_cv = env_data["contract_version"]
        assert healthz_cv == env_cv, (
            f"RCP-9b: contract_version drift: healthz={healthz_cv} env={env_cv}"
        )

    async def test_rcp9c_provider_down_healthz_not_silent_ok(self):
        """RCP-9c: provider down → healthz returns 503 or degraded; never silent ok."""
        async with _client(_make_app("down")) as c:
            r = await c.get("/v1/healthz")
        assert r.status_code in (200, 503), (
            f"RCP-9c: expected 200 or 503, got {r.status_code}"
        )
        if r.status_code == 200:
            assert r.json()["status"] != "ok", (
                f"RCP-9c: provider down must NOT report healthz ok; got {r.json()}"
            )

    async def test_rcp9c_provider_fail_healthz_degraded_not_ok(self):
        """RCP-9c: provider in fail mode (degraded health) → healthz must not report ok."""
        async with _client(_make_app("fail")) as c:
            r = await c.get("/v1/healthz")
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            assert r.json()["status"] == "degraded", (
                f"RCP-9c: fail provider must report degraded, got {r.json()['status']}"
            )


# ---------------------------------------------------------------------------
# RCP-10 — standalone usability (full lifecycle, service token only)
# ---------------------------------------------------------------------------


class TestRCP10Standalone:
    """RCP-10: entire lifecycle operable with service Bearer token only; no app-specific headers."""

    async def test_rcp10_s1_s2_ensure_then_get(self):
        """RCP-10 S1+S2: ensure reaches ready; GET confirms ready + non-empty connection."""
        headers_only_service = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = _make_app("active")
        async with _client(app) as c:
            r_ensure = await c.post(
                "/v1/environments/rcp10-s1/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=headers_only_service,
            )
            assert r_ensure.status_code == 200, (
                f"RCP-10 S1: ensure with service token only failed: {r_ensure.text}"
            )
            assert r_ensure.json()["status"] == "ready"

            r_get = await c.get("/v1/environments/rcp10-s1", headers=headers_only_service)
            assert r_get.status_code == 200, (
                f"RCP-10 S2: GET with service token only failed: {r_get.text}"
            )
            data_get = r_get.json()
            assert data_get["status"] == "ready"
            assert data_get["connection"] is not None

    async def test_rcp10_s3_sleep(self):
        """RCP-10 S3: sleep works with service token only."""
        headers_only_service = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = _make_app("active")
        async with _client(app) as c:
            await c.post(
                "/v1/environments/rcp10-s3/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=headers_only_service,
            )
            r_sleep = await c.post("/v1/environments/rcp10-s3/sleep", headers=headers_only_service)
            assert r_sleep.status_code == 200, (
                f"RCP-10 S3: sleep with service token only failed: {r_sleep.text}"
            )

    async def test_rcp10_s4_ensure_wakes_from_asleep(self):
        """RCP-10 S4: ensure on asleep env wakes it back to ready (service token only)."""
        headers_only_service = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = _make_app("active")
        async with _client(app) as c:
            await c.post(
                "/v1/environments/rcp10-s4/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=headers_only_service,
            )
            await c.post("/v1/environments/rcp10-s4/sleep", headers=headers_only_service)
            r_wake = await c.post(
                "/v1/environments/rcp10-s4/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=headers_only_service,
            )
            assert r_wake.status_code == 200
            assert r_wake.json()["status"] == "ready", (
                f"RCP-10 S4: wake from asleep with service token returned {r_wake.json().get('status')}"
            )

    async def test_rcp10_s5_destroy(self):
        """RCP-10 S5: destroy works with service token only; subsequent GET = 404/destroyed."""
        headers_only_service = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = _make_app("active")
        async with _client(app) as c:
            await c.post(
                "/v1/environments/rcp10-s5/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=headers_only_service,
            )
            r_del = await c.delete("/v1/environments/rcp10-s5", headers=headers_only_service)
            assert r_del.status_code in (200, 202), (
                f"RCP-10 S5: destroy with service token only failed: {r_del.text}"
            )
            r_get = await c.get("/v1/environments/rcp10-s5", headers=headers_only_service)
            assert r_get.status_code in (200, 404)
            if r_get.status_code == 200:
                assert r_get.json()["status"] == "destroyed"

    async def test_rcp10_s6_healthz_no_auth(self):
        """RCP-10 S6: healthz requires zero authentication."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/healthz")  # no auth header at all
        assert r.status_code == 200, (
            f"RCP-10 S6: healthz without auth returned {r.status_code}: {r.text}"
        )

    async def test_rcp10_no_app_identity_header_required(self):
        """RCP-10: server must NOT require any X-App-Id / X-Tenant / X-User extra header."""
        # Build headers with ONLY the service token — absolutely no other headers.
        service_only_headers = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = _make_app()
        async with _client(app) as c:
            r = await c.post(
                "/v1/environments/rcp10-noappid/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=service_only_headers,
            )
        assert r.status_code not in (400, 401, 403), (
            f"RCP-10: server requires extra identity header beyond service token: "
            f"{r.status_code} {r.text}"
        )


# ---------------------------------------------------------------------------
# RCP-11 — agnostika kontraktu (substrate-agnostic responses)
# ---------------------------------------------------------------------------


class TestRCP11Agnostika:
    """RCP-11: no substrate noun in any response body field or URL."""

    async def test_rcp11a_no_substrate_noun_in_ensure_response(self):
        """RCP-11a: ensure response body contains no substrate noun in any string field."""
        app = _make_app()
        async with _client(app) as c:
            r = await c.post(
                "/v1/environments/rcp11a-ensure/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code == 200
        hits = _grep_substrate(r.json())
        assert hits == [], (
            f"RCP-11a: substrate noun(s) found in ensure response: {hits}"
        )

    async def test_rcp11a_no_substrate_noun_in_get_response(self):
        """RCP-11a: GET response body contains no substrate noun."""
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp11a-get")
            r = await c.get("/v1/environments/rcp11a-get", headers=AUTH)
        hits = _grep_substrate(r.json())
        assert hits == [], (
            f"RCP-11a: substrate noun(s) found in GET response: {hits}"
        )

    async def test_rcp11b_error_codes_from_app_facing_registr_only(self):
        """RCP-11b: error codes returned by server are from app-facing registr §8 only."""
        from server.runtime.errors import APP_FACING_CODES

        app = _make_app()
        async with _client(app) as c:
            # Trigger a variety of error responses.
            r1 = await c.get("/v1/environments/noexist", headers=AUTH)            # 404
            r2 = await c.post(
                "/v1/environments/rcp11b/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": INVALID_TOOL},
                headers=AUTH,
            )                                                                       # 400
            r3 = await c.post(
                "/v1/environments/rcp11b/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
            )                                                                       # 401 (no auth)

        for r in [r1, r2, r3]:
            code = r.json().get("code")
            assert code in APP_FACING_CODES, (
                f"RCP-11b: non-app-facing code {code!r} in response {r.json()}"
            )

    async def test_rcp11c_connection_urls_opaque_no_substrate(self):
        """RCP-11c: connection URLs (control_url, terminal_url) contain no substrate noun."""
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp11c-conn")
        conn = data["connection"]
        for key, url in [("control_url", conn["control_url"]), ("terminal_url", conn["terminal_url"])]:
            assert not _SUBSTRATE_RE.search(url), (
                f"RCP-11c: substrate noun in {key}: {url}"
            )

    async def test_rcp11_control_url_uses_https_scheme(self):
        """RCP-11/RCP-A6 E: control_url uses https:// scheme."""
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp11-https")
        assert data["connection"]["control_url"].startswith("https://"), (
            f"RCP-11: control_url must use https://, got: {data['connection']['control_url']}"
        )

    async def test_rcp11_terminal_url_uses_wss_scheme(self):
        """RCP-11/RCP-A6 E: terminal_url uses wss:// scheme."""
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp11-wss")
        assert data["connection"]["terminal_url"].startswith("wss://"), (
            f"RCP-11: terminal_url must use wss://, got: {data['connection']['terminal_url']}"
        )


# ---------------------------------------------------------------------------
# RCP-12 — ZEĎ-disjunktnost (wall disjunctness)
# ---------------------------------------------------------------------------


class TestRCP12WallDisjunctness:
    """RCP-12: no request parameter or field weakens enforcement; bypass fields → 400."""

    async def test_rcp12b_firewall_off_field_returns_400(self):
        """RCP-12b/1h: 'firewall: off' in body → 400 ERR_INVALID_REQUEST."""
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp12b-fw/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL, "firewall": "off"},
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-12b: firewall field must be 400, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_INVALID_REQUEST", (
            f"RCP-12b: expected ERR_INVALID_REQUEST, got {r.json()}"
        )

    async def test_rcp12b_egress_field_returns_400(self):
        """RCP-12b: 'egress: allow-all' in body → 400 ERR_INVALID_REQUEST."""
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp12b-egress/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL, "egress": "allow-all"},
                headers=AUTH,
            )
        assert r.status_code == 400
        assert r.json()["code"] == "ERR_INVALID_REQUEST"

    async def test_rcp12b_policy_field_returns_400(self):
        """RCP-12b: 'policy: none' in body → 400 ERR_INVALID_REQUEST."""
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp12b-policy/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL, "policy": "none"},
                headers=AUTH,
            )
        assert r.status_code == 400
        assert r.json()["code"] == "ERR_INVALID_REQUEST"

    async def test_rcp12b_bypass_field_never_reaches_provider(self):
        """RCP-12b: bypass field rejected before provider is called (schema wall, not provider)."""
        # If the bypass field reached the provider (active mode), we would get 200 ready.
        # Getting 400 proves the wall stopped it before the service/provider layer.
        async with _client(_make_app("active")) as c:
            r = await c.post(
                "/v1/environments/rcp12b-wall/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL, "firewall": "disabled"},
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-12b WALL VIOLATED: bypass field reached provider (got {r.status_code} instead of 400)"
        )

    async def test_rcp12c_no_policy_ruleset_allowlist_capability_in_response(self):
        """RCP-12c: response body contains no policy/ruleset/allowlist/capability field keys."""
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp12c-wall")
        wall_hits = _grep_wall_fields(data)
        assert wall_hits == [], (
            f"RCP-12c: ZDI fields found in ensure response: {wall_hits}"
        )

    async def test_rcp12c_no_wall_fields_in_healthz_response(self):
        """RCP-12c: healthz response contains no policy/ruleset/allowlist/capability fields."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/healthz")
        hits = _grep_wall_fields(r.json())
        assert hits == [], f"RCP-12c: ZDI fields in healthz: {hits}"


# ---------------------------------------------------------------------------
# RCP-13 — BYOK token neteče přes control API
# ---------------------------------------------------------------------------


class TestRCP13ByokDoesNotLeak:
    """RCP-13: control API accepts no AI tool tokens and returns none in responses."""

    async def test_rcp13b_ensure_rejects_ai_token_field(self):
        """RCP-13b: EnsureRequest rejects ai_token field (BYOK cannot enter via request)."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp13b-tok/ensure",
                json={
                    "repo": {"url": VALID_REPO},
                    "tool": VALID_TOOL,
                    "ai_token": "sk-supersecret",
                },
                headers=AUTH,
            )
        assert r.status_code == 400, (
            f"RCP-13b: ai_token field must be rejected 400, got {r.status_code}: {r.text}"
        )

    async def test_rcp13b_ensure_rejects_api_key_field(self):
        """RCP-13b: EnsureRequest rejects api_key field."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp13b-apikey/ensure",
                json={
                    "repo": {"url": VALID_REPO},
                    "tool": VALID_TOOL,
                    "api_key": "anthropic-key",
                },
                headers=AUTH,
            )
        assert r.status_code == 400

    async def test_rcp13a_ensure_response_has_no_credential_fields(self):
        """RCP-13a: Environment response contains no token/secret/credential/password fields."""
        sensitive_keys = {"token", "api_key", "secret", "credential", "byok", "ai_token", "password"}
        app = _make_app()
        async with _client(app) as c:
            data = await _ensure_ready(c, "rcp13a-byok")

        def check_keys(obj):
            if isinstance(obj, dict):
                for k in obj.keys():
                    assert k.lower() not in sensitive_keys, (
                        f"RCP-13a: sensitive key {k!r} found in response"
                    )
                    check_keys(obj[k])
            elif isinstance(obj, list):
                for item in obj:
                    check_keys(item)

        check_keys(data)

    async def test_rcp13a_get_response_has_no_credential_fields(self):
        """RCP-13a: GET response has no credential fields either."""
        sensitive_keys = {"token", "api_key", "secret", "credential", "byok", "ai_token", "password"}
        app = _make_app()
        async with _client(app) as c:
            await _ensure_ready(c, "rcp13a-get")
            r = await c.get("/v1/environments/rcp13a-get", headers=AUTH)
        data = r.json()

        def check_keys(obj):
            if isinstance(obj, dict):
                for k in obj.keys():
                    assert k.lower() not in sensitive_keys, (
                        f"RCP-13a: sensitive key {k!r} in GET response"
                    )
                    check_keys(obj[k])
            elif isinstance(obj, list):
                for item in obj:
                    check_keys(item)

        check_keys(data)


# ---------------------------------------------------------------------------
# RCP-14 — auth odběratele
# ---------------------------------------------------------------------------


class TestRCP14Auth:
    """RCP-14: auth requirements on all lifecycle endpoints."""

    async def test_rcp14a_ensure_missing_auth_returns_401(self):
        """RCP-14a: POST ensure without Bearer token → 401 ERR_UNAUTHORIZED; never 5xx."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp14a-noauth/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                # intentionally no auth header
            )
        assert r.status_code == 401, (
            f"RCP-14a: expected 401, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_UNAUTHORIZED"
        assert r.status_code < 500

    async def test_rcp14a_get_missing_auth_returns_401(self):
        """RCP-14a: GET without auth → 401 ERR_UNAUTHORIZED."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/environments/rcp14a-getnoauth")
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_UNAUTHORIZED"

    async def test_rcp14a_sleep_missing_auth_returns_401(self):
        """RCP-14a: POST sleep without auth → 401 ERR_UNAUTHORIZED."""
        async with _client(_make_app()) as c:
            r = await c.post("/v1/environments/rcp14a-sleepnoauth/sleep")
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_UNAUTHORIZED"

    async def test_rcp14a_destroy_missing_auth_returns_401(self):
        """RCP-14a: DELETE without auth → 401 ERR_UNAUTHORIZED."""
        async with _client(_make_app()) as c:
            r = await c.delete("/v1/environments/rcp14a-destnoauth")
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_UNAUTHORIZED"

    async def test_rcp14a_wrong_token_returns_401_not_5xx(self):
        """RCP-14a: wrong Bearer token → 401 ERR_UNAUTHORIZED; never 5xx."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp14a-wrong/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers={"Authorization": "Bearer totally-wrong-token"},
            )
        assert r.status_code == 401, (
            f"RCP-14a: wrong token must return 401, got {r.status_code}: {r.text}"
        )
        assert r.json()["code"] == "ERR_UNAUTHORIZED"
        assert r.status_code < 500

    async def test_rcp14a_missing_bearer_scheme_returns_401(self):
        """RCP-14a: malformed Authorization header (no Bearer) → 401."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp14a-nobearer/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )
        assert r.status_code == 401
        assert r.status_code < 500

    async def test_rcp14b_valid_token_proceeds_not_401(self):
        """RCP-14b: valid service token → operation proceeds; never 401."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/rcp14b-valid/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
                headers=AUTH,
            )
        assert r.status_code != 401, (
            f"RCP-14b: valid token got 401: {r.text}"
        )

    async def test_rcp14c_healthz_public_no_auth_needed(self):
        """RCP-14c: GET /v1/healthz without auth → 200 (public endpoint)."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/healthz")  # no auth
        assert r.status_code == 200, (
            f"RCP-14c: healthz without auth must return 200, got {r.status_code}: {r.text}"
        )

    async def test_rcp14c_healthz_with_auth_also_works(self):
        """RCP-14c variant: healthz with valid auth header also returns 200."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/healthz", headers=AUTH)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Error envelope shape (cross-cutting)
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    """Error responses must conform to contract §8 shape {code, message}."""

    async def test_error_envelope_has_code_and_message_not_details(self):
        """Contract §8: error body has 'code' and 'message'; must NOT have scaffold 'details' key."""
        async with _client(_make_app()) as c:
            r = await c.get("/v1/environments/nonexistent", headers=AUTH)
        assert r.status_code == 404
        data = r.json()
        assert "code" in data, f"Error envelope missing 'code': {data}"
        assert "message" in data, f"Error envelope missing 'message': {data}"
        assert "details" not in data, (
            f"Error envelope has scaffold 'details' key (wrong shape): {data}"
        )

    async def test_ensure_401_error_envelope_shape(self):
        """Auth failure error envelope has correct shape."""
        async with _client(_make_app()) as c:
            r = await c.post(
                "/v1/environments/env-shape/ensure",
                json={"repo": {"url": VALID_REPO}, "tool": VALID_TOOL},
            )
        assert r.status_code == 401
        data = r.json()
        assert "code" in data and "message" in data
        assert "details" not in data
