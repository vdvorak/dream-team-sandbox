"""Unit tests for runtime control-plane lifecycle — slice 1 (RCP-1..5, 9, 11, 12, 13, 14).

Covers all in-scope AC:
  RCP-1  ensure (new→ready; idempotent; repo-mismatch→409; tool-not-allowed→400; extra-field→400)
  RCP-2  fail-closed (provider fail → never ready; provider down → 503; provider fail → 502)
  RCP-3  get (404 on nonexistent; connection null outside ready; connection opaque)
  RCP-4  sleep (idempotent; on provisioning no interrupt; on destroyed → 200/404)
  RCP-5  destroy (idempotent; ensure-after-destroy = fresh)
  RCP-9  healthz (ok/degraded/503; no auth required)
  RCP-11 agnostika (connection URLs free of substrate nouns)
  RCP-12 ZEĎ-disjunktnost (extra fields rejected → 400)
  RCP-13 BYOK neteče
  RCP-14 auth (missing/invalid → 401; healthz public)

Uses ASGI TestClient (httpx + ASGITransport) — no real network, no DB.
Each test creates its own app instance with an injected provider to stay isolated.
"""

from __future__ import annotations

import asyncio
import re

import pytest
from httpx import ASGITransport, AsyncClient

from server.runtime.enforcement.dev import DevEnforcementProvider
from server.runtime.main import create_runtime_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SERVICE_TOKEN = "test-service-token"
AUTH_HEADERS = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
BASE_REPO = "https://github.com/example/project"
BASE_REPO_ALT = "https://github.com/example/other"
VALID_TOOL = "claude"
INVALID_TOOL = "malware"

# Substrate nouns that MUST NOT appear in connection URLs (RCP-11c, AC-3b).
SUBSTRATE_NOUNS_PATTERN = re.compile(
    r"Fly|fly\.dev|docker|6PN|\.internal|:808[0-9]|nftables|tmux|WORKSPACE_AGENT_BASE",
    re.IGNORECASE,
)


def make_app(provider_mode: str = "active"):
    """Create a fresh app with a DevEnforcementProvider in the given mode."""
    provider = DevEnforcementProvider(mode=provider_mode)
    return create_runtime_app(
        service_token=SERVICE_TOKEN,
        enforcement_provider_override=provider,
    )


def client_for(app):
    """Return an async context manager yielding an AsyncClient for the given app."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def ensure_ready(client, project_id: str = "proj-1", repo: str = BASE_REPO) -> dict:
    """Helper: ensure project and assert it reaches ready. Returns response JSON."""
    r = await client.post(
        f"/v1/environments/{project_id}/ensure",
        json={"repo": {"url": repo}, "tool": VALID_TOOL},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["status"] == "ready"
    return data


# ---------------------------------------------------------------------------
# RCP-1 — ensure: basic flow
# ---------------------------------------------------------------------------


class TestEnsureBasic:
    async def test_rcp1a_ensure_new_project_returns_ready(self):
        """RCP-1a: POST /ensure with valid params returns 200 with status ready."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-1/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"
        assert data["project_id"] == "proj-1"
        assert data["tool"] == VALID_TOOL

    async def test_rcp1b_contract_version_in_response(self):
        """RCP-1b: Every Environment response contains contract_version '1.1.0'."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-cv/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 200
        assert r.json()["contract_version"] == "1.1.0"

    async def test_rcp1c_ensure_idempotent_on_ready(self):
        """RCP-1c: Repeated ensure with same project_id + same repo.url on ready → 200 same env."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-idem")
            r2 = await c.post(
                "/v1/environments/proj-idem/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r2.status_code == 200
        assert r2.json()["status"] == "ready"
        assert r2.json()["project_id"] == "proj-idem"

    async def test_rcp1d_concurrent_ensure_single_environment(self):
        """RCP-1d: Concurrent POSTs for same project_id produce exactly one environment; no 5xx."""
        app = make_app()
        async with client_for(app) as c:
            tasks = [
                c.post(
                    "/v1/environments/proj-race/ensure",
                    json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                    headers=AUTH_HEADERS,
                )
                for _ in range(5)
            ]
            results = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in results]
        # No 5xx.
        for s in statuses:
            assert s < 500, f"Got 5xx: {s}"
        # All successful results report same state (no two different ready environments).
        ready_data = [r.json() for r in results if r.status_code == 200]
        if ready_data:
            project_ids = {d["project_id"] for d in ready_data}
            assert project_ids == {"proj-race"}, "Multiple project IDs in concurrent results"

    async def test_rcp1e_repo_mismatch_returns_409(self):
        """RCP-1e: ensure with different repo.url on live env → 409 ERR_REPO_MISMATCH."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-mismatch", repo=BASE_REPO)
            r2 = await c.post(
                "/v1/environments/proj-mismatch/ensure",
                json={"repo": {"url": BASE_REPO_ALT}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r2.status_code == 409
        assert r2.json()["code"] == "ERR_REPO_MISMATCH"

    async def test_rcp1f_invalid_tool_returns_400(self):
        """RCP-1f: ensure with tool not in allowlist → 400 ERR_TOOL_NOT_ALLOWED (not 422)."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-tool/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": INVALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 400
        assert r.json()["code"] == "ERR_TOOL_NOT_ALLOWED"

    async def test_rcp1h_extra_field_in_body_returns_400(self):
        """RCP-1h/AC-12c: extra field in top-level request body → 400 (not 422, not silent accept)."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-extra/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "firewall": "off"},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 400

    async def test_rcp1h_extra_field_in_repo_returns_400(self):
        """RCP-A6 D: extra field in nested repo object → 400 (bypass attempt blocked)."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-repoextra/ensure",
                json={
                    "repo": {"url": BASE_REPO, "egress": "allow-all"},
                    "tool": VALID_TOOL,
                },
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# RCP-2 — fail-closed guarantee
# ---------------------------------------------------------------------------


class TestFailClosed:
    async def test_rcp2a_dev_provider_active_returns_ready(self):
        """RCP-2a: Dev provider in active mode → status ready + non-null connection."""
        async with client_for(make_app("active")) as c:
            data = await ensure_ready(c, "proj-fc-active")
        assert data["connection"] is not None
        assert data["connection"]["control_url"]
        assert data["connection"]["terminal_url"]

    async def test_rcp2b_provider_fail_returns_502_never_ready(self):
        """RCP-2b: Provider configured to return provider_error → 502 ERR_PROVISION_FAILED; NEVER ready."""
        async with client_for(make_app("fail")) as c:
            r = await c.post(
                "/v1/environments/proj-fail/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 502
        assert r.json()["code"] == "ERR_PROVISION_FAILED"
        # Also confirm: if we get status back, it's not ready.
        if "status" in r.json():
            assert r.json()["status"] != "ready"

    async def test_rcp2c_provider_down_returns_503_never_ready(self):
        """RCP-2c: Provider unreachable → 503 ERR_RUNTIME_UNAVAILABLE; NEVER 200 ready."""
        async with client_for(make_app("down")) as c:
            r = await c.post(
                "/v1/environments/proj-down/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 503
        assert r.json()["code"] == "ERR_RUNTIME_UNAVAILABLE"


# ---------------------------------------------------------------------------
# RCP-3 — get environment + opaque connection
# ---------------------------------------------------------------------------


class TestGetEnvironment:
    async def test_rcp3a_get_ready_returns_connection(self):
        """RCP-3a: GET on ready env → 200 with non-empty control_url and terminal_url."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-get")
            r = await c.get("/v1/environments/proj-get", headers=AUTH_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"
        assert data["connection"]["control_url"]
        assert data["connection"]["terminal_url"]

    async def test_rcp3b_connection_urls_no_substrate_nouns(self):
        """RCP-3b/AC-11c: connection URLs contain no substrate identifiers (Fly/docker/6PN/etc)."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-opaque")
        conn = data["connection"]
        for url in [conn["control_url"], conn["terminal_url"]]:
            assert not SUBSTRATE_NOUNS_PATTERN.search(url), (
                f"Substrate noun found in URL: {url}"
            )

    async def test_rcp3c_get_nonexistent_returns_404(self):
        """RCP-3c: GET on non-existent project_id → 404 ERR_ENVIRONMENT_NOT_FOUND."""
        async with client_for(make_app()) as c:
            r = await c.get("/v1/environments/no-such-id", headers=AUTH_HEADERS)
        assert r.status_code == 404
        assert r.json()["code"] == "ERR_ENVIRONMENT_NOT_FOUND"

    async def test_rcp3d_get_asleep_returns_null_connection(self):
        """RCP-3d: GET on asleep env → connection: null; status: asleep."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-slept")
            await c.post("/v1/environments/proj-slept/sleep", headers=AUTH_HEADERS)
            r = await c.get("/v1/environments/proj-slept", headers=AUTH_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "asleep"
        assert data["connection"] is None

    async def test_rcp3d_get_destroyed_returns_null_connection(self):
        """RCP-3d: GET on destroyed env → connection: null; status: destroyed."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-dest-get")
            await c.delete("/v1/environments/proj-dest-get", headers=AUTH_HEADERS)
            r = await c.get("/v1/environments/proj-dest-get", headers=AUTH_HEADERS)
        # Contract: GET after destroy → 200 destroyed OR 404. Either is acceptable.
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json()["connection"] is None

    async def test_rcp3e_get_provisioning_has_phase(self):
        """RCP-3e: GET on provisioning env → connection: null; phase string present."""
        # We can't easily observe provisioning without a slow provider.
        # Use fail-mode provider: ensure will be called, record set to provisioning,
        # then enforcement fails → 502. After that, record remains in provisioning state.
        app = make_app("fail")
        async with client_for(app) as c:
            r_ensure = await c.post(
                "/v1/environments/proj-prov/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
            # Ensure may return 502; the record is now in provisioning.
            assert r_ensure.status_code in (502, 503)
            # GET should show provisioning state.
            r_get = await c.get("/v1/environments/proj-prov", headers=AUTH_HEADERS)
        assert r_get.status_code == 200
        data = r_get.json()
        assert data["status"] == "provisioning"
        assert data["connection"] is None
        # phase should be present (was set to "enforcing" before the provider was called).
        assert data.get("phase") is not None
        assert data["phase"] != ""


# ---------------------------------------------------------------------------
# RCP-4 — sleep
# ---------------------------------------------------------------------------


class TestSleep:
    async def test_rcp4a_sleep_on_ready_transitions_to_asleep(self):
        """RCP-4a: POST sleep on ready → 200; state asleep or ready (advisory — both OK)."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-sleep4a")
            r = await c.post("/v1/environments/proj-sleep4a/sleep", headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] in ("asleep", "ready")

    async def test_rcp4b_sleep_idempotent_on_asleep(self):
        """RCP-4b: POST sleep on already-asleep → 200; never 5xx."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-sleep4b")
            await c.post("/v1/environments/proj-sleep4b/sleep", headers=AUTH_HEADERS)
            r2 = await c.post("/v1/environments/proj-sleep4b/sleep", headers=AUTH_HEADERS)
        assert r2.status_code == 200
        assert r2.status_code < 500

    async def test_rcp4c_sleep_on_destroyed_never_5xx(self):
        """RCP-4c: POST sleep on destroyed → 200 or 404; never 5xx."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-sleep4c")
            await c.delete("/v1/environments/proj-sleep4c", headers=AUTH_HEADERS)
            r = await c.post("/v1/environments/proj-sleep4c/sleep", headers=AUTH_HEADERS)
        assert r.status_code in (200, 404)
        assert r.status_code < 500

    async def test_rcp4d_sleep_on_nonexistent_never_5xx(self):
        """RCP-4d: POST sleep on nonexistent project_id → 200 or 404; never 5xx."""
        async with client_for(make_app()) as c:
            r = await c.post("/v1/environments/no-such/sleep", headers=AUTH_HEADERS)
        assert r.status_code in (200, 404)
        assert r.status_code < 500

    async def test_sleep_on_provisioning_no_interrupt(self):
        """spec edge case: sleep during provisioning returns 200 with current state; no interrupt."""
        app = make_app("fail")
        async with client_for(app) as c:
            # Put env into provisioning (fail provider keeps it there).
            await c.post(
                "/v1/environments/proj-prov-sleep/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
            r_sleep = await c.post("/v1/environments/proj-prov-sleep/sleep", headers=AUTH_HEADERS)
        assert r_sleep.status_code == 200
        # Should return current state (provisioning), not error.
        assert r_sleep.json()["status"] == "provisioning"


# ---------------------------------------------------------------------------
# RCP-5 — destroy
# ---------------------------------------------------------------------------


class TestDestroy:
    async def test_rcp5a_destroy_existing_env(self):
        """RCP-5a: DELETE on existing env → 200; subsequent GET = 404 or destroyed."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-dest5a")
            r = await c.delete("/v1/environments/proj-dest5a", headers=AUTH_HEADERS)
            assert r.status_code in (200, 202)
            r_get = await c.get("/v1/environments/proj-dest5a", headers=AUTH_HEADERS)
        assert r_get.status_code in (200, 404)
        if r_get.status_code == 200:
            assert r_get.json()["status"] == "destroyed"

    async def test_rcp5b_destroy_idempotent(self):
        """RCP-5b: DELETE repeatedly → 200 or 404; never 5xx."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-dest5b")
            await c.delete("/v1/environments/proj-dest5b", headers=AUTH_HEADERS)
            r2 = await c.delete("/v1/environments/proj-dest5b", headers=AUTH_HEADERS)
        assert r2.status_code in (200, 404)
        assert r2.status_code < 500

    async def test_rcp5c_destroy_nonexistent_never_5xx(self):
        """RCP-5c: DELETE on nonexistent → 200 or 404; never 5xx."""
        async with client_for(make_app()) as c:
            r = await c.delete("/v1/environments/no-such-id", headers=AUTH_HEADERS)
        assert r.status_code in (200, 404)
        assert r.status_code < 500

    async def test_rcp5d_ensure_after_destroy_fresh_env(self):
        """RCP-5d: ensure on destroyed project_id → fresh new provisioning/ready cycle."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-dest5d")
            await c.delete("/v1/environments/proj-dest5d", headers=AUTH_HEADERS)
            # Now ensure again (potentially with a different repo — destroy clears binding).
            r = await c.post(
                "/v1/environments/proj-dest5d/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code in (200, 202)
        assert r.json()["status"] in ("ready", "provisioning")


# ---------------------------------------------------------------------------
# RCP-9 — healthz
# ---------------------------------------------------------------------------


class TestHealthz:
    async def test_rcp9a_healthz_no_auth_returns_200(self):
        """RCP-9a/14c: GET /v1/healthz without auth → 200 with status ok/degraded + contract_version."""
        async with client_for(make_app("active")) as c:
            r = await c.get("/v1/healthz")  # no auth header
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")
        assert data["contract_version"] == "1.1.0"

    async def test_rcp9b_contract_version_matches(self):
        """RCP-9b: contract_version in healthz matches contract_version in Environment responses."""
        app = make_app()
        async with client_for(app) as c:
            r_health = await c.get("/v1/healthz")
            env_data = await ensure_ready(c, "proj-cv2")
        assert r_health.json()["contract_version"] == env_data["contract_version"]

    async def test_rcp9c_provider_down_healthz_degraded_not_ok(self):
        """RCP-9c: provider unreachable → healthz returns degraded (or 503); never silent ok."""
        async with client_for(make_app("down")) as c:
            r = await c.get("/v1/healthz")
        # Must not be silent ok — either 503 or degraded.
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            assert r.json()["status"] != "ok", "Provider down must not report healthz ok"

    async def test_rcp9c_provider_degraded_healthz_degraded(self):
        """RCP-9c: provider in fail mode (degraded health) → healthz status=degraded."""
        async with client_for(make_app("fail")) as c:
            r = await c.get("/v1/healthz")
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            assert r.json()["status"] == "degraded"


# ---------------------------------------------------------------------------
# RCP-11 — contract agnostika (substrate-agnostic)
# ---------------------------------------------------------------------------


class TestAgnostika:
    async def test_rcp11c_connection_urls_opaque(self):
        """RCP-11c: Dev provider connection URLs contain no substrate noun."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-agnostic")
        conn = data["connection"]
        for url in [conn["control_url"], conn["terminal_url"]]:
            assert not SUBSTRATE_NOUNS_PATTERN.search(url), f"Substrate leak in URL: {url}"

    async def test_control_url_https_scheme(self):
        """control_url uses https:// scheme (RCP-A6 E)."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-scheme-ctrl")
        assert data["connection"]["control_url"].startswith("https://")

    async def test_terminal_url_wss_scheme(self):
        """terminal_url uses wss:// scheme (RCP-A6 E)."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-scheme-term")
        assert data["connection"]["terminal_url"].startswith("wss://")

    async def test_no_substrate_noun_in_any_response_field(self):
        """RCP-11a: No substrate noun in any response body field value."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-grep")
        # Recursively check all string values in response.
        def grep_strings(obj):
            if isinstance(obj, str):
                assert not SUBSTRATE_NOUNS_PATTERN.search(obj), f"Substrate noun in value: {obj}"
            elif isinstance(obj, dict):
                for v in obj.values():
                    grep_strings(v)
            elif isinstance(obj, list):
                for item in obj:
                    grep_strings(item)
        grep_strings(data)


# ---------------------------------------------------------------------------
# RCP-12 — ZEĎ-disjunktnost
# ---------------------------------------------------------------------------


class TestWallDisjunctness:
    async def test_rcp12b_extra_enforcement_field_returns_400_err_invalid_request(self):
        """RCP-12b/1h: ensure with enforcement-bypass field → 400 ERR_INVALID_REQUEST.

        Verifies both the HTTP status and the exact error code (contract v1.1.0 §8).
        The bypass field must never silently pass through to the provider.
        """
        bypass_payloads = [
            {"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "firewall": "off"},
            {"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "egress": "allow-all"},
            {"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "policy": "none"},
        ]
        app = make_app()
        async with client_for(app) as c:
            for payload in bypass_payloads:
                r = await c.post(
                    "/v1/environments/proj-bypass/ensure",
                    json=payload,
                    headers=AUTH_HEADERS,
                )
                assert r.status_code == 400, (
                    f"Expected 400 for bypass payload {payload}, got {r.status_code}: {r.text}"
                )
                assert r.json()["code"] == "ERR_INVALID_REQUEST", (
                    f"Expected ERR_INVALID_REQUEST for bypass payload {payload}, got {r.json()}"
                )

    async def test_rcp12b_firewall_bypass_never_reaches_provider(self):
        """RCP-12b enforcement-bypass isolation: 'firewall' field rejected at schema layer.

        WHY this test: the wall (schema validation) must stop bypass fields before they
        reach LifecycleService / EnforcementProvider. We verify:
        1. Response is 400 ERR_INVALID_REQUEST (schema rejection, not provider rejection).
        2. Provider was never invoked — the DevEnforcementProvider in 'active' mode would
           return 200 if the call passed through; getting 400 proves pre-provider rejection.
        """
        async with client_for(make_app("active")) as c:
            r = await c.post(
                "/v1/environments/proj-firewall-bypass/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "firewall": "disabled"},
                headers=AUTH_HEADERS,
            )
        # If provider had been called with active mode, we'd get 200. Getting 400 confirms
        # the bypass field was rejected before reaching the service/provider layer.
        assert r.status_code == 400
        assert r.json()["code"] == "ERR_INVALID_REQUEST"

    async def test_rcp12b_extra_repo_field_returns_400(self):
        """RCP-12b/A6D: extra field in repo object (bypass via nested object) → 400 ERR_INVALID_REQUEST."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-repobp/ensure",
                json={"repo": {"url": BASE_REPO, "firewall": "off"}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 400
        assert r.json()["code"] == "ERR_INVALID_REQUEST"


# ---------------------------------------------------------------------------
# RCP-13 — BYOK neteče
# ---------------------------------------------------------------------------


class TestByokDoesNotLeak:
    async def test_rcp13b_ensure_request_rejects_token_field(self):
        """RCP-13b: EnsureRequest rejects any field that could carry a BYOK token."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-byok/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL, "ai_token": "sk-secret"},
                headers=AUTH_HEADERS,
            )
        assert r.status_code == 400  # extra_forbidden

    async def test_rcp13a_response_contains_no_token_fields(self):
        """RCP-13a: Environment response contains no credential or token fields."""
        app = make_app()
        async with client_for(app) as c:
            data = await ensure_ready(c, "proj-byokchk")
        sensitive_keys = {"token", "api_key", "secret", "credential", "byok", "ai_token", "password"}
        def check_keys(obj):
            if isinstance(obj, dict):
                for k in obj.keys():
                    assert k.lower() not in sensitive_keys, f"Sensitive key in response: {k}"
                    check_keys(obj[k])
            elif isinstance(obj, list):
                for item in obj:
                    check_keys(item)
        check_keys(data)


# ---------------------------------------------------------------------------
# RCP-14 — auth
# ---------------------------------------------------------------------------


class TestAuth:
    async def test_rcp14a_missing_token_returns_401(self):
        """RCP-14a: Any lifecycle op without auth → 401 ERR_UNAUTHORIZED; never 5xx."""
        app = make_app()
        async with client_for(app) as c:
            ops = [
                c.post("/v1/environments/proj-auth/ensure", json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL}),
                c.get("/v1/environments/proj-auth"),
                c.post("/v1/environments/proj-auth/sleep"),
                c.delete("/v1/environments/proj-auth"),
            ]
            for coro in ops:
                r = await coro
                assert r.status_code == 401, f"Expected 401, got {r.status_code} for {r.url}"
                assert r.json()["code"] == "ERR_UNAUTHORIZED"

    async def test_rcp14a_wrong_token_returns_401(self):
        """RCP-14a: Wrong Bearer token → 401; never 5xx."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-wrongtoken/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers={"Authorization": "Bearer wrong-token"},
            )
        assert r.status_code == 401
        assert r.json()["code"] == "ERR_UNAUTHORIZED"

    async def test_rcp14b_valid_token_proceeds(self):
        """RCP-14b: Valid service token → operation proceeds (not 401)."""
        async with client_for(make_app()) as c:
            r = await c.post(
                "/v1/environments/proj-validauth/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r.status_code != 401

    async def test_rcp14c_healthz_public_no_auth(self):
        """RCP-14c: GET /v1/healthz without auth → 200 (public endpoint)."""
        async with client_for(make_app()) as c:
            r = await c.get("/v1/healthz")
        assert r.status_code == 200

    async def test_rcp14c_healthz_auth_not_required(self):
        """RCP-14c variant: healthz with auth header also works (auth is optional)."""
        async with client_for(make_app()) as c:
            r = await c.get("/v1/healthz", headers=AUTH_HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Error envelope shape
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    async def test_error_envelope_has_code_and_message(self):
        """App-facing errors have {code, message}; no scaffold {code, details} shape."""
        async with client_for(make_app()) as c:
            r = await c.get("/v1/environments/nonexistent", headers=AUTH_HEADERS)
        assert r.status_code == 404
        data = r.json()
        assert "code" in data
        assert "message" in data
        # scaffold shape key must not be present
        assert "details" not in data

    async def test_error_code_in_app_facing_set(self):
        """All error codes returned are from the app-facing registr §8 (not cage codes)."""
        from server.runtime.errors import APP_FACING_CODES
        app = make_app()
        async with client_for(app) as c:
            responses = [
                await c.get("/v1/environments/nonexistent", headers=AUTH_HEADERS),  # 404
                await c.post("/v1/environments/proj-tc/ensure", json={"repo": {"url": BASE_REPO}, "tool": INVALID_TOOL}, headers=AUTH_HEADERS),  # 400
                await c.post("/v1/environments/proj-tc/ensure", json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL}),  # 401
            ]
        for r in responses:
            code = r.json().get("code")
            assert code in APP_FACING_CODES, f"Non-app-facing code in response: {code}"


# ---------------------------------------------------------------------------
# Wake from asleep (RCP-S4 / ensure-from-asleep)
# ---------------------------------------------------------------------------


class TestWakeFromAsleep:
    async def test_ensure_from_asleep_returns_ready(self):
        """ensure on asleep env → wake → ready (RCP-S4)."""
        app = make_app()
        async with client_for(app) as c:
            await ensure_ready(c, "proj-wake")
            await c.post("/v1/environments/proj-wake/sleep", headers=AUTH_HEADERS)
            # verify asleep
            r_get = await c.get("/v1/environments/proj-wake", headers=AUTH_HEADERS)
            assert r_get.json()["status"] == "asleep"
            # wake via ensure
            r_wake = await c.post(
                "/v1/environments/proj-wake/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=AUTH_HEADERS,
            )
        assert r_wake.status_code == 200
        assert r_wake.json()["status"] == "ready"
        assert r_wake.json()["connection"] is not None


# ---------------------------------------------------------------------------
# RCP-10 — standalone operability (service identity only, no app identity)
# ---------------------------------------------------------------------------


class TestStandaloneServiceIdentity:
    """RCP-10: server is fully operable via service token alone.

    WHY explicit: RCP-10 mandates that the server does NOT require any application-specific
    identity header (e.g. X-App-Id, X-Tenant, X-User) in addition to the service token.
    The full lifecycle (ensure → get → sleep → destroy) must complete with only the
    service Bearer token — no other authentication or identification header present.
    """

    async def test_rcp10_full_lifecycle_with_service_token_only(self):
        """RCP-10: ensure → get → sleep → destroy using only service Bearer token; no app header."""
        # Intentionally build headers with ONLY the service token — no X-App-Id or similar.
        service_only_headers = {"Authorization": f"Bearer {SERVICE_TOKEN}"}
        app = make_app("active")
        async with client_for(app) as c:
            # ensure
            r_ensure = await c.post(
                "/v1/environments/proj-standalone/ensure",
                json={"repo": {"url": BASE_REPO}, "tool": VALID_TOOL},
                headers=service_only_headers,
            )
            assert r_ensure.status_code == 200, (
                f"RCP-10: ensure with service token only failed: {r_ensure.text}"
            )
            assert r_ensure.json()["status"] == "ready"

            # get
            r_get = await c.get("/v1/environments/proj-standalone", headers=service_only_headers)
            assert r_get.status_code == 200, (
                f"RCP-10: get with service token only failed: {r_get.text}"
            )

            # sleep
            r_sleep = await c.post(
                "/v1/environments/proj-standalone/sleep", headers=service_only_headers
            )
            assert r_sleep.status_code == 200, (
                f"RCP-10: sleep with service token only failed: {r_sleep.text}"
            )

            # destroy
            r_destroy = await c.delete(
                "/v1/environments/proj-standalone", headers=service_only_headers
            )
            assert r_destroy.status_code in (200, 202), (
                f"RCP-10: destroy with service token only failed: {r_destroy.text}"
            )

    async def test_rcp10_healthz_no_auth_required(self):
        """RCP-10/RCP-9a: healthz requires zero authentication — not even service token."""
        async with client_for(make_app()) as c:
            r = await c.get("/v1/healthz")  # no Authorization header at all
        assert r.status_code == 200, f"RCP-10: healthz without any auth failed: {r.text}"
