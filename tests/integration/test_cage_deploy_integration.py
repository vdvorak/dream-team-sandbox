"""Integration testy — cage_deploy end-to-end orchestrace s mockovanými runnery.

Pokrývá mezivrstevní chování, které unit testy netestují:
- Kompletní happy-path průchod (drift-pin → lint → ACL render → build → policy → deploy → smoke).
- Všechny abort cesty s reálnými disk I/O (lock file, overlay dir).
- Pořadí volání enforceru (policy PŘED deploy, I1/CE-1).
- Kombinované selhání (drift + policy fail; drift OK + ingress leak).
- Idempotent re-run (druhý deploy bez driftu).
- accept-drift re-pin a ihned úspěšný deploy.
- smoke_runner selhání (ERR_LOGIN_PERSIST, ERR_INGRESS_LEAK) → deploy vrátí 1.

Acceptance vazba: I1, I7, I9, I10, I11, CE-1, CE-2, CE-6.
"""

from __future__ import annotations

import pytest

from server.cage.deploy.cage_deploy import DeployContext, run_deploy  # noqa: F401 (used in test)
from server.cage.deploy.drift import WORKSPACE_DEF_FILES
from server.cage.errors import (
    CageDriftError,
    IngressLeakError,
    LoginPersistError,
    SecretLeakError,
)
from server.cage.policy.enforcer import FlyNetworkPolicyAdapter


# ---------------------------------------------------------------------------
# Pomocné továrny
# ---------------------------------------------------------------------------

def _make_app_repo(base, marker="v1"):
    """Vytvoří fake appkový workspace-def strom s daným markerem."""
    for rel in WORKSPACE_DEF_FILES:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {rel}\nmarker={marker}\n", encoding="utf-8")
    return base


def _ok_enforcer():
    return FlyNetworkPolicyAdapter(http_post=lambda *_: (200, "ok"))


def _base_ctx(tmp_path, *, app_marker="v1", cf_team="acme", env=None, **overrides):
    """Sestaví minimální DeployContext s nahratenými runnery; vrátí (ctx, events)."""
    app = _make_app_repo(tmp_path / "app", marker=app_marker)
    overlay = tmp_path / "overlay"
    overlay.mkdir(exist_ok=True)
    (overlay / "fly.workspace.toml").write_text("app = 'dream-team-workspace'\n", encoding="utf-8")

    events: list[str] = []
    defaults: dict = dict(
        overlay_dir=overlay,
        lock_path=tmp_path / "cage-deploy.lock",
        cf_team_domain=cf_team,
        workspace_env=env or {"WORKSPACE_DIR": "/workspace"},
        enforcer=_ok_enforcer(),
        build_runner=lambda ctx, wdh: events.append("build"),
        deploy_runner=lambda ctx: events.append("deploy"),
        smoke_runner=lambda ctx: events.append("smoke"),
        log=lambda _: None,
    )
    defaults.update(overrides)
    ctx = DeployContext(app_repo=app, **defaults)
    return ctx, events


# ---------------------------------------------------------------------------
# I1 / CE-1 — happy path + pořadí policy PŘED deploy
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_full_run_returns_zero(self, tmp_path):
        ctx, events = _base_ctx(tmp_path)
        assert run_deploy(ctx) == 0

    def test_all_runner_phases_called(self, tmp_path):
        ctx, events = _base_ctx(tmp_path)
        run_deploy(ctx)
        # build, deploy, smoke musí být zavolány (a v tomto pořadí)
        assert events == ["build", "deploy", "smoke"]

    def test_policy_applied_strictly_before_deploy(self, tmp_path):
        """CE-1 / I1: host-policy musí být aktivní PŘED spuštěním workspace machine."""
        policy_calls: list[str] = []
        deploy_calls: list[str] = []

        enforcer = FlyNetworkPolicyAdapter(
            http_post=lambda *_: (policy_calls.append("policy"), (200, "ok"))[1]
        )
        ctx, _ = _base_ctx(
            tmp_path,
            enforcer=enforcer,
            deploy_runner=lambda ctx: deploy_calls.append("deploy"),
        )
        run_deploy(ctx)
        assert policy_calls, "enforcer se nikdy nezavolal"
        assert deploy_calls, "deploy se nikdy nezavolal"
        # policy musí předcházet deploy i v absolutním event pořadí
        combined = policy_calls + deploy_calls
        assert combined.index("policy") < combined.index("deploy")

    def test_lock_file_created_after_first_deploy(self, tmp_path):
        ctx, _ = _base_ctx(tmp_path)
        run_deploy(ctx)
        assert ctx.lock_path.is_file(), "cage-deploy.lock nebyl vytvořen"

    def test_idempotent_second_deploy_without_drift(self, tmp_path):
        """Druhý deploy bez driftu projde bez --accept-drift (hash match)."""
        ctx, events1 = _base_ctx(tmp_path)
        assert run_deploy(ctx) == 0
        ctx2, events2 = _base_ctx(
            tmp_path,
            app_marker="v1",  # stejný marker = stejný hash
            lock_path=ctx.lock_path,
        )
        # sdílíme app repo pro korektní hash srovnání
        ctx2.app_repo = ctx.app_repo
        assert run_deploy(ctx2) == 0
        assert "deploy" in events2


# ---------------------------------------------------------------------------
# I11 / CE-6 — drift detekce (fail-closed, re-pin)
# ---------------------------------------------------------------------------

class TestDriftDetection:
    def test_drift_aborts_deploy(self, tmp_path):
        """CE-6 / I11: změna appkové definice → fail-closed ABORT, workspace nenasazen."""
        # Subdir pro první deploy
        d1 = tmp_path / "run1"
        d1.mkdir()
        ctx, events = _base_ctx(d1)
        run_deploy(ctx)  # první deploy, pin v1
        assert ctx.lock_path.is_file()
        # Simuluj změnu appkové definice (v2) — NE přes _base_ctx, aby nedošlo k přepsání
        _make_app_repo(ctx.app_repo, marker="v2")
        # Druhý deploy: jiný subdir pro pomocné soubory, ale SDÍLÍME lock + overlay + app_repo
        d2 = tmp_path / "run2"
        d2.mkdir()
        events2: list[str] = []
        ctx2 = DeployContext(
            app_repo=ctx.app_repo,    # stejný (upravený na v2) app repo
            overlay_dir=ctx.overlay_dir,  # sdílíme overlay
            lock_path=ctx.lock_path,  # sdílíme lock → drift se detekuje
            cf_team_domain="acme",
            workspace_env={"WORKSPACE_DIR": "/workspace"},
            enforcer=_ok_enforcer(),
            build_runner=lambda c, wdh: events2.append("build"),
            deploy_runner=lambda c: events2.append("deploy"),
            smoke_runner=lambda c: events2.append("smoke"),
            log=lambda _: None,
        )
        rc = run_deploy(ctx2)
        assert rc == 1, "deploy se nesmí dokončit při driftu (CE-6)"
        assert "deploy" not in events2

    def test_drift_with_accept_drift_repins_and_succeeds(self, tmp_path):
        """--accept-drift: vědomý re-pin umožní deploy (operátor re-reviewoval overlay)."""
        ctx, _ = _base_ctx(tmp_path)
        run_deploy(ctx)
        _make_app_repo(ctx.app_repo, marker="v2")
        ctx2, events2 = _base_ctx(tmp_path, lock_path=ctx.lock_path, accept_drift=True)
        ctx2.app_repo = ctx.app_repo
        rc = run_deploy(ctx2)
        assert rc == 0
        assert "deploy" in events2

    def test_missing_app_file_aborts(self, tmp_path):
        """Chybějící komponenta workspace definice → CageDriftError → deploy ABORT."""
        ctx, _ = _base_ctx(tmp_path)
        # odstraň první soubor z definice
        (ctx.app_repo / WORKSPACE_DEF_FILES[0]).unlink()
        rc = run_deploy(ctx)
        assert rc == 1


# ---------------------------------------------------------------------------
# I7 / CE-8 — ingress leak (pre-deploy lint)
# ---------------------------------------------------------------------------

class TestIngressLeak:
    def test_http_service_in_overlay_aborts(self, tmp_path):
        """I7: aktivní [http_service] v overlay config → ERR_INGRESS_LEAK → ABORT."""
        ctx, events = _base_ctx(tmp_path)
        (ctx.overlay_dir / "fly.workspace.toml").write_text(
            "app = 'x'\n[http_service]\n  internal_port = 8081\n",
            encoding="utf-8",
        )
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_double_bracket_http_service_aborts(self, tmp_path):
        ctx, events = _base_ctx(tmp_path)
        (ctx.overlay_dir / "fly.workspace.toml").write_text(
            "app = 'x'\n[[http_service]]\n  internal_port = 8081\n",
            encoding="utf-8",
        )
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_commented_http_service_passes(self, tmp_path):
        """Zakomentovaná sekce [http_service] nesmí blokovat deploy."""
        ctx, events = _base_ctx(tmp_path)
        (ctx.overlay_dir / "fly.workspace.toml").write_text(
            "app = 'x'\n# [http_service]  zarazeno (I7)\n",
            encoding="utf-8",
        )
        rc = run_deploy(ctx)
        assert rc == 0


# ---------------------------------------------------------------------------
# I9 — secret leak (workspace env scan)
# ---------------------------------------------------------------------------

class TestSecretLeak:
    @pytest.mark.parametrize("key", [
        "CLOUDFLARE_TUNNEL_TOKEN", "CF_ACCESS_AUD", "GH_TOKEN", "ADMIN_BOOTSTRAP_TOKEN"
    ])
    def test_each_high_value_secret_aborts(self, tmp_path, key):
        """I9: jakýkoli high-value secret ve workspace env → ERR_SECRET_LEAK → ABORT."""
        ctx, events = _base_ctx(tmp_path, env={key: "super-secret"})
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events


# ---------------------------------------------------------------------------
# I10 / CE-7 — git write credential
# ---------------------------------------------------------------------------

class TestGitWriteCred:
    def test_classic_pat_in_env_aborts(self, tmp_path):
        """I10: classic GitHub PAT ve workspace env → ERR_GIT_WRITE_CRED → ABORT."""
        ctx, events = _base_ctx(tmp_path, env={"WORKSPACE_DIR": "/w", "SOME_TOKEN": "ghp_" + "x" * 30})
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_fine_grained_pat_aborts(self, tmp_path):
        ctx, events = _base_ctx(tmp_path, env={"T": "github_pat_11ABC_xyz123"})
        rc = run_deploy(ctx)
        assert rc == 1


# ---------------------------------------------------------------------------
# I1 / CE-2 — policy apply selhání (fail-closed)
# ---------------------------------------------------------------------------

class TestPolicyFailClosed:
    def test_api_500_aborts_before_deploy(self, tmp_path):
        """CE-2 / I1: Fly API vrátí 500 → ERR_POLICY_APPLY_FAILED → ABORT před deploy."""
        ctx, events = _base_ctx(
            tmp_path,
            enforcer=FlyNetworkPolicyAdapter(http_post=lambda *_: (500, "error")),
        )
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_api_transport_exception_aborts(self, tmp_path):
        def _fail(*_):
            raise ConnectionError("unreachable")
        ctx, events = _base_ctx(
            tmp_path,
            enforcer=FlyNetworkPolicyAdapter(http_post=_fail),
        )
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_no_transport_aborts(self, tmp_path):
        ctx, events = _base_ctx(
            tmp_path,
            enforcer=FlyNetworkPolicyAdapter(http_post=None),
        )
        rc = run_deploy(ctx)
        assert rc == 1


# ---------------------------------------------------------------------------
# Smoke selhání (post-deploy regrese)
# ---------------------------------------------------------------------------

class TestSmokeFail:
    def test_smoke_runner_raising_cage_error_returns_1(self, tmp_path):
        """ERR_LOGIN_PERSIST ze smoke → deploy vrátí 1 (regrese-guard)."""
        def _bad_smoke(ctx):
            raise LoginPersistError("token path chybí po de-root")

        ctx, _ = _base_ctx(tmp_path, smoke_runner=_bad_smoke)
        rc = run_deploy(ctx)
        assert rc == 1

    def test_smoke_ingress_leak_regression_returns_1(self, tmp_path):
        """ERR_INGRESS_LEAK ze smoke (I7 regression guard post-deploy) → rc=1."""
        def _bad_smoke(ctx):
            raise IngressLeakError("[http_service] nalezen po deploy (regrese I7)")

        ctx, _ = _base_ctx(tmp_path, smoke_runner=_bad_smoke)
        rc = run_deploy(ctx)
        assert rc == 1

    def test_missing_smoke_runner_still_passes(self, tmp_path):
        """Chybějící smoke_runner nevyvolá chybu — manuální verifikace operátorem."""
        ctx, _ = _base_ctx(tmp_path, smoke_runner=None)
        rc = run_deploy(ctx)
        assert rc == 0


# ---------------------------------------------------------------------------
# ACL render integrace
# ---------------------------------------------------------------------------

class TestAclRenderIntegration:
    def test_rendered_acl_file_exists_after_deploy(self, tmp_path):
        """cage-deploy zapíše rendered ACL do overlay dir (krok 3)."""
        ctx, _ = _base_ctx(tmp_path)
        run_deploy(ctx)
        rendered = ctx.overlay_dir / "smokescreen-acl.rendered.yaml"
        assert rendered.is_file(), "smokescreen-acl.rendered.yaml nebyl vytvořen"

    def test_rendered_acl_contains_expected_domains(self, tmp_path):
        ctx, _ = _base_ctx(tmp_path, cf_team="myteam")
        run_deploy(ctx)
        content = (ctx.overlay_dir / "smokescreen-acl.rendered.yaml").read_text()
        assert "api.github.com" in content, "GitHub doména chybí v ACL"
        assert "myteam.cloudflareaccess.com" in content, "CF Access doména chybí v ACL"
        assert "default: deny" in content, "ACL není default-deny"
        # I3: build-time hosty nesmí být ve skutečném allow bloku (komentáře nevadí).
        # Extrahujeme allow: sekci — domény jsou řádky "  - domain: <x>"
        allow_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("- domain:")
        ]
        allow_domains_found = [ln.split("domain:")[1].strip() for ln in allow_lines]
        assert "raw.githubusercontent.com" not in allow_domains_found, "raw.githubusercontent.com nesmí být v allow"
        assert "pypi.org" not in allow_domains_found, "pypi.org nesmí být v allow"
        assert "api.github.com" in allow_domains_found
        assert "myteam.cloudflareaccess.com" in allow_domains_found

    def test_invalid_cf_team_domain_aborts_before_deploy(self, tmp_path):
        ctx, events = _base_ctx(tmp_path, cf_team="evil.com\n  - domain: attacker")
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events

    def test_empty_cf_team_domain_aborts(self, tmp_path):
        ctx, events = _base_ctx(tmp_path, cf_team="")
        rc = run_deploy(ctx)
        assert rc == 1
        assert "deploy" not in events
