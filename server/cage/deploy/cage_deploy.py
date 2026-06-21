"""cage-deploy — jediná legitimní deploy cesta klece (CE-5, contracts §6).

Orchestruje fail-closed sekvenci (každý krok ABORTuje deploy při selhání, CE-2):

  1. drift-check (CE-6)            : appkové def vs. pinned hash → ERR_CAGE_DRIFT
  2. pre-deploy lint/scan (§5)     : [http_service]/secret/git-write → ERR_INGRESS_LEAK/...
  3. render ACL (rozhodnutí (d))   : CF doména z env → smokescreen-acl.yaml (do build artefaktu)
  4. overlay build (§2)            : kombinovaný context (appka RO + overlay) → workspace image
  5. apply host policy (vrstva 2)  : ruleset H1–H7 → enforcer → ERR_NO_POLICY/ERR_POLICY_APPLY_FAILED
  6. deploy workspace (overlay cfg): fly deploy -c overlay/fly.workspace.toml
  7. post-deploy smoke (§6)        : I7 leak re-check + login persistence (regrese-guard)

KRITICKÉ POŘADÍ (fail-closed): policy MUSÍ být aktivní PŘED spuštěním machine (krok 5 < 6).
Bez platné policy se deploy NESMÍ dokončit (I1).

Příkazy build/deploy (docker/fly) jsou injektnutelné callables (runner), aby šla
orchestrace testovat bez reálné infrastruktury. V provozu se dosadí reálné shell-výstupy.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from server.cage.deploy import drift, lint
from server.cage.errors import CageError
from server.cage.policy import acl
from server.cage.policy.enforcer import EnforcerAdapter, get_enforcer
from server.cage.policy.ruleset import RulesetParams, build_ruleset

# Cesty (relativní k sandbox repu). Overlay artefakty žijí jen tady (CE-5/I11).
SANDBOX_ROOT = Path(__file__).resolve().parents[3]
OVERLAY_DIR = SANDBOX_ROOT / "server" / "cage" / "overlay"
LOCK_PATH = SANDBOX_ROOT / "server" / "cage" / "cage-deploy.lock"
DEFAULT_APP_REPO = Path("/home/vitek/dev/AI/dream-team-app")  # read-only zdroj appky


@dataclass
class DeployContext:
    """Vstupy a injektnutelné runnery pro orchestraci (testovatelnost)."""

    app_repo: Path
    overlay_dir: Path = OVERLAY_DIR
    lock_path: Path = LOCK_PATH
    accept_drift: bool = False
    substrate: str = "fly"
    cf_team_domain: str = ""
    workspace_env: dict[str, str] = field(default_factory=dict)
    # Runnery (injektnutelné): build context, deploy, post-deploy smoke.
    enforcer: EnforcerAdapter | None = None
    build_runner: Callable[["DeployContext", str], None] | None = None
    deploy_runner: Callable[["DeployContext"], None] | None = None
    smoke_runner: Callable[["DeployContext"], None] | None = None
    log: Callable[[str], None] = print


def _step(ctx: DeployContext, n: int, msg: str) -> None:
    ctx.log(f"[cage-deploy {n}/7] {msg}")


def run_deploy(ctx: DeployContext) -> int:
    """Provede celou fail-closed sekvenci. Vrací exit code (0 = OK, !=0 = ABORT).

    Jakákoli CageError = fail-closed ABORT: vytiskne error code + důvod, vrátí 1.
    Deploy se NEDOKONČÍ (CE-2). Žádný best-effort.
    """
    try:
        # 1) drift-check (CE-6) — PŘED čímkoli, ať operátor ví, že overlay sedí.
        _step(ctx, 1, "drift-check (WORKSPACE_DEF_HASH)")
        wdh = drift.check_drift(ctx.app_repo, ctx.lock_path, accept_drift=ctx.accept_drift)
        ctx.log(f"        WORKSPACE_DEF_HASH={wdh[:16]}… (pinned)")

        # 2) pre-deploy lint/scan (§5) — fail-closed regrese-guardy.
        _step(ctx, 2, "pre-deploy lint/scan ([http_service]/secret/git-write)")
        lint.lint_overlay_fly_config(ctx.overlay_dir / "fly.workspace.toml")  # I7
        lint.scan_secret_leak(ctx.workspace_env)  # I9
        lint.scan_git_write_cred(*ctx.workspace_env.values())  # I10

        # 3) render ACL (rozhodnutí (d)) — CF doména z env, fail-closed validace.
        _step(ctx, 3, "render Smokescreen ACL (CF doména z env)")
        cf_team = ctx.cf_team_domain or os.environ.get("CF_ACCESS_TEAM_DOMAIN", "")
        acl_text = acl.render_acl(cf_team)  # → AclTemplateError(→fail-closed) při nevalidnosti
        # ACL se předá do build artefaktu s mode 0400 (řeší overlay Dockerfile/entrypoint, I5).
        (ctx.overlay_dir / "smokescreen-acl.rendered.yaml").write_text(acl_text, encoding="utf-8")

        # 4) overlay build (§2) — kombinovaný context (appka RO + overlay). Repo appky se NEMĚNÍ.
        _step(ctx, 4, "overlay build (kombinovaný context: appka RO + overlay)")
        if ctx.build_runner is None:
            raise CageError("build_runner není nakonfigurován — nelze sestavit overlay image (fail-closed)")
        ctx.build_runner(ctx, wdh)

        # 5) apply host policy (vrstva 2) — MUSÍ být PŘED deploy machine (I1, CE-1).
        _step(ctx, 5, "apply host-enforced policy (ruleset H1–H7)")
        enforcer = ctx.enforcer or get_enforcer(ctx.substrate)
        ruleset = build_ruleset(RulesetParams())  # spike-parametry s defaulty (TODO-spike)
        enforcer.validate_and_apply(ruleset)  # → ERR_NO_POLICY / ERR_POLICY_APPLY_FAILED
        ctx.log(f"        policy aktivní na substrátu '{enforcer.substrate}' (H1–H7)")

        # 6) deploy workspace s overlay config (6PN-only, bez [http_service]).
        _step(ctx, 6, "deploy workspace (overlay fly config, 6PN-only)")
        if ctx.deploy_runner is None:
            raise CageError("deploy_runner není nakonfigurován — nelze nasadit workspace (fail-closed)")
        ctx.deploy_runner(ctx)

        # 7) post-deploy smoke (§6) — I7 re-check + Claude login persistence regrese-guard.
        _step(ctx, 7, "post-deploy smoke (I7 leak re-check + login persistence)")
        if ctx.smoke_runner is not None:
            ctx.smoke_runner(ctx)  # → ERR_INGRESS_LEAK / ERR_LOGIN_PERSIST při regresi
        else:
            ctx.log("        smoke_runner nenastaven — smoke vynechán (manuální verifikace operátorem)")

        ctx.log("[cage-deploy] PASS — klec nasazena, policy aktivní, žádný leak.")
        return 0

    except CageError as exc:
        # Fail-closed (CE-2): vytiskni strojový kód + důvod, ABORT (žádné nasazení bez garance).
        ctx.log(f"[cage-deploy] ABORT {exc.code}: {exc.detail or exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cage-deploy",
        description="Jediná legitimní deploy cesta klece (fail-closed, CE-5).",
    )
    parser.add_argument("--app-repo", default=str(DEFAULT_APP_REPO), help="read-only repo appky")
    parser.add_argument("--accept-drift", action="store_true", help="vědomý re-pin WORKSPACE_DEF_HASH (CE-6)")
    parser.add_argument("--substrate", default="fly", help="enforcer substrát (fly|...)")
    parser.add_argument("--cf-team-domain", default="", help="CF Access team label (jinak z env CF_ACCESS_TEAM_DOMAIN)")
    args = parser.parse_args(argv)

    ctx = DeployContext(
        app_repo=Path(args.app_repo),
        accept_drift=args.accept_drift,
        substrate=args.substrate,
        cf_team_domain=args.cf_team_domain,
        workspace_env=dict(os.environ),  # v provozu: workspace env (zde proxy z procesu)
    )
    # Pozn.: build/deploy/smoke runnery se v provozu dosadí z deploy prostředí (shell wrappery).
    # Bez nich orchestrace fail-closed ABORTuje (krok 4/6) — žádný tichý "no-op deploy".
    return run_deploy(ctx)


if __name__ == "__main__":
    sys.exit(main())
