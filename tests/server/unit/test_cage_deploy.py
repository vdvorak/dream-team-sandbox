"""Unit testy — cage-deploy orchestrace (fail-closed sekvence, pořadí kroků).

Acceptance vazba: CE-2 (fail-closed všude), CE-1/I1 (policy PŘED deploy machine),
contracts §6 (pořadí kroků).
"""

import pytest

from server.cage.deploy import drift
from server.cage.deploy.cage_deploy import DeployContext, run_deploy
from server.cage.deploy.drift import WORKSPACE_DEF_FILES
from server.cage.policy.enforcer import FlyNetworkPolicyAdapter


def _fake_app_repo(tmp_path):
    for rel in WORKSPACE_DEF_FILES:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {rel}\n")
    return tmp_path


def _ok_enforcer():
    return FlyNetworkPolicyAdapter(http_post=lambda *a: (200, "ok"))


def _base_ctx(tmp_path, **over):
    app = over.pop("app_repo", None) or _fake_app_repo(tmp_path / "app")
    overlay = tmp_path / "overlay"
    overlay.mkdir(exist_ok=True)
    # minimální overlay fly config bez [http_service]
    (overlay / "fly.workspace.toml").write_text("app = 'dream-team-workspace'\n")
    order = []
    defaults = dict(
        overlay_dir=overlay,
        lock_path=tmp_path / "cage-deploy.lock",
        cf_team_domain="acme",
        workspace_env={"WORKSPACE_DIR": "/workspace"},
        enforcer=_ok_enforcer(),
        build_runner=lambda ctx, wdh: order.append("build"),
        deploy_runner=lambda ctx: order.append("deploy"),
        smoke_runner=lambda ctx: order.append("smoke"),
        log=lambda m: None,
    )
    defaults.update(over)
    ctx = DeployContext(app_repo=app, **defaults)
    ctx._order = order  # type: ignore[attr-defined]
    return ctx


def test_happy_path_returns_zero_and_correct_order(tmp_path):
    ctx = _base_ctx(tmp_path)
    rc = run_deploy(ctx)
    assert rc == 0
    # KRITICKÉ pořadí: build → (policy apply) → deploy → smoke.
    # build PŘED deploy; policy apply mezi nimi (enforcer volán); smoke poslední.
    assert ctx._order == ["build", "deploy", "smoke"]


def test_policy_applied_before_deploy(tmp_path):
    # I1/CE-1: host policy MUSÍ být aktivní PŘED spuštěním workspace machine.
    events = []
    enforcer = FlyNetworkPolicyAdapter(
        http_post=lambda *a: (events.append("policy"), (200, "ok"))[1]
    )
    ctx = _base_ctx(
        tmp_path,
        enforcer=enforcer,
        deploy_runner=lambda ctx: events.append("deploy"),
        build_runner=lambda ctx, wdh: events.append("build"),
        smoke_runner=lambda ctx: events.append("smoke"),
    )
    run_deploy(ctx)
    assert events.index("policy") < events.index("deploy")


def test_drift_aborts_before_deploy(tmp_path):
    ctx = _base_ctx(tmp_path)
    # pin v1
    run_deploy(ctx)
    # změň appkovou definici → drift
    for rel in WORKSPACE_DEF_FILES:
        (ctx.app_repo / rel).write_text("# changed\n")
    deployed = []
    ctx2 = _base_ctx(
        tmp_path,
        app_repo=ctx.app_repo,
        lock_path=ctx.lock_path,
        deploy_runner=lambda c: deployed.append(1),
    )
    rc = run_deploy(ctx2)
    assert rc == 1  # fail-closed ABORT
    assert deployed == []  # workspace se NENASADIL


def test_ingress_leak_aborts(tmp_path):
    ctx = _base_ctx(tmp_path)
    (ctx.overlay_dir / "fly.workspace.toml").write_text(
        "app = 'x'\n[http_service]\n  internal_port = 8081\n"
    )
    deployed = []
    ctx.deploy_runner = lambda c: deployed.append(1)
    rc = run_deploy(ctx)
    assert rc == 1
    assert deployed == []


def test_secret_leak_aborts(tmp_path):
    ctx = _base_ctx(tmp_path, workspace_env={"GH_TOKEN": "secret"})
    deployed = []
    ctx.deploy_runner = lambda c: deployed.append(1)
    rc = run_deploy(ctx)
    assert rc == 1
    assert deployed == []


def test_policy_apply_failure_aborts_before_deploy(tmp_path):
    deployed = []
    ctx = _base_ctx(
        tmp_path,
        enforcer=FlyNetworkPolicyAdapter(http_post=lambda *a: (500, "err")),
        deploy_runner=lambda c: deployed.append(1),
    )
    rc = run_deploy(ctx)
    assert rc == 1  # ERR_POLICY_APPLY_FAILED
    assert deployed == []  # bez platné policy se workspace NENASADÍ (I1)


def test_missing_build_runner_aborts(tmp_path):
    ctx = _base_ctx(tmp_path, build_runner=None)
    deployed = []
    ctx.deploy_runner = lambda c: deployed.append(1)
    rc = run_deploy(ctx)
    assert rc == 1
    assert deployed == []


def test_bad_cf_domain_aborts(tmp_path):
    ctx = _base_ctx(tmp_path, cf_team_domain="evil.com\n  - domain: x")
    rc = run_deploy(ctx)
    assert rc == 1  # ACL render fail-closed
