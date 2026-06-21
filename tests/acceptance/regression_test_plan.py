"""Regression test plan — containment-cage (post-deploy re-run suite).

Tento modul NEDEFINUJE nové testy — mapuje které existující testy/AC body
se musí re-spustit po každém deployi, a s jakou prioritou.

Kontraktem mandatorní: I7 (ingress leak) se MUSÍ re-testovat po každém deploy
(kontrakt §I7c, contracts/containment-cage.md §4 ERR_INGRESS_LEAK).

Použití:
    python3 -m pytest tests/acceptance/regression_test_plan.py -v
    # nebo jako součást post-deploy smoke:
    python3 -m pytest tests/ -m "regression" -v

Marking: testy označené @pytest.mark.regression jsou mandatorní po každém deployi.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SANDBOX_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = SANDBOX_ROOT / "server" / "cage" / "overlay"


# ---------------------------------------------------------------------------
# Registrace regression marku (aby pytest nezačal varovat)
# ---------------------------------------------------------------------------
# Viz pytest.ini / pyproject.toml — mark "regression" musí být registrován.


# ---------------------------------------------------------------------------
# P0 — MANDATORY po každém deployi (kontrakt §I7c + §4)
# ---------------------------------------------------------------------------

@pytest.mark.regression
class TestRegressionMandatoryPostDeploy:
    """P0: tyto testy MUSÍ proběhnout po každém cage-deploy (kontraktem mandatorní).

    Kontrakt §I7c: "Re-test po každém deployi (regression guard)"
    Kontrakt §4: ERR_INGRESS_LEAK — pre-deploy lint + post-deploy smoke ověří.
    """

    def test_I7_overlay_no_http_service_regression(self):
        """I7 regression [static]: overlay fly.workspace.toml musí stále být bez [http_service].

        WHY: fly deploy může obnovit konfiguraci na výchozí (s [http_service]) při chybě
        operátora. Tento test ověří, že overlay config ZŮSTAL bez veřejného ingressu.
        Kontraktem: povinný re-test po každém deployi.
        """
        content = (OVERLAY / "fly.workspace.toml").read_text(encoding="utf-8")
        for line in content.splitlines():
            if not line.strip().startswith("#"):
                assert "[http_service]" not in line, (
                    f"REGRESE I7: [http_service] nalezena v overlay fly.workspace.toml: {line!r}\n"
                    "Workspace by byl veřejně dostupný — opravit overlay a re-deploy."
                )

    def test_I7_lint_passes_on_overlay_config(self):
        """I7 regression [static]: lint guardia (ERR_INGRESS_LEAK) musí projít po deployi."""
        from server.cage.deploy.lint import lint_overlay_fly_config
        # nesmí vyhodit IngressLeakError
        lint_overlay_fly_config(OVERLAY / "fly.workspace.toml")

    def test_nftables_config_still_has_default_drop(self):
        """I1/I4 regression [static]: nftables.cage.conf musí stále mít default-drop output chain."""
        content = (OVERLAY / "nftables.cage.conf").read_text(encoding="utf-8")
        assert "policy drop" in content, (
            "REGRESE I1: nftables output/input chain ztratily default policy drop"
        )

    def test_entrypoint_cap_drop_sequence_intact(self):
        """I4/I6 regression [static]: entrypoint.sh musí stále mít korektní de-root pořadí."""
        content = (OVERLAY / "entrypoint.sh").read_text(encoding="utf-8")
        nft_pos = content.find("nft -f")
        cap_pos = content.find("capsh")
        assert nft_pos != -1, "REGRESE I4: nft -f zmizel z entrypoint.sh"
        assert cap_pos != -1, "REGRESE I4: capsh zmizel z entrypoint.sh"
        assert nft_pos < cap_pos, (
            "REGRESE I4: pořadí nftables/capsh je prohozené — cap drop PŘED nftables instalací!"
        )

    def test_ruleset_completeness_regression(self):
        """I1 regression [static]: ruleset H1–H7 musí být kompletní a ve správném pořadí."""
        from server.cage.policy.ruleset import RULE_IDS, assert_complete, build_ruleset
        rs = build_ruleset()
        assert_complete(rs)
        assert [r.id for r in rs] == list(RULE_IDS), (
            "REGRESE I1: ruleset H1–H7 přeházený nebo neúplný"
        )

    def test_error_registry_complete_regression(self):
        """CE-2 regression [static]: error kódy musí odpovídat kontraktu."""
        from server.cage.errors import ERROR_CODES
        EXPECTED = {
            "ERR_NO_POLICY", "ERR_POLICY_APPLY_FAILED", "ERR_CAGE_DRIFT",
            "ERR_PROXY_DOWN", "ERR_INVM_FW_FAILED", "ERR_CAP_DROP_FAILED",
            "ERR_NNP_FAILED", "ERR_INGRESS_LEAK", "ERR_SECRET_LEAK",
            "ERR_GIT_WRITE_CRED", "ERR_LOGIN_PERSIST",
        }
        assert set(ERROR_CODES.keys()) == EXPECTED, (
            f"REGRESE CE-2: error registry neodpovídá kontraktu.\n"
            f"Extra: {set(ERROR_CODES.keys()) - EXPECTED}\n"
            f"Chybí: {EXPECTED - set(ERROR_CODES.keys())}"
        )


# ---------------------------------------------------------------------------
# P1 — Doporučené po každém deployi (bezpečnostní invarianty)
# ---------------------------------------------------------------------------

@pytest.mark.regression
class TestRegressionSecurityInvariantsPostDeploy:
    """P1: bezpečnostní invarianty — doporučené po každém deployi."""

    def test_acl_default_deny_regression(self):
        """I2/I3 regression [static]: ACL render musí stále produkovat default-deny."""
        from server.cage.policy.acl import render_acl
        out = render_acl("acme")
        assert "default: deny" in out, "REGRESE I2: ACL render neprodukuje default-deny"
        # build-time hosty NIKDY nesmí v allow
        allow_lines = [
            l.split("domain:")[1].strip()
            for l in out.splitlines()
            if l.strip().startswith("- domain:")
        ]
        assert "raw.githubusercontent.com" not in allow_lines, (
            "REGRESE I3: raw.githubusercontent.com se objevil v ACL allow listu"
        )
        assert "pypi.org" not in allow_lines, (
            "REGRESE I3: pypi.org se objevil v ACL allow listu"
        )

    def test_dockerfile_no_expose_regression(self):
        """I7 regression [static]: Dockerfile nesmí získat EXPOSE po rebase/update."""
        import re
        content = (OVERLAY / "Dockerfile.workspace").read_text(encoding="utf-8")
        expose_lines = [
            l for l in content.splitlines()
            if re.match(r"^\s*EXPOSE\s+", l, re.IGNORECASE)
        ]
        assert expose_lines == [], (
            f"REGRESE I7: Dockerfile dostal EXPOSE: {expose_lines}"
        )

    def test_secret_scan_patterns_regression(self):
        """I9/I10 regression [static]: scanery high-value secrets musí pokrývat všechny 4 klíče."""
        from server.cage.deploy.lint import HIGH_VALUE_SECRETS
        REQUIRED = frozenset({
            "CLOUDFLARE_TUNNEL_TOKEN", "CF_ACCESS_AUD", "GH_TOKEN", "ADMIN_BOOTSTRAP_TOKEN"
        })
        assert REQUIRED <= set(HIGH_VALUE_SECRETS), (
            f"REGRESE I9: chybí secret v scan sadě: {REQUIRED - set(HIGH_VALUE_SECRETS)}"
        )

    def test_fail_closed_enforcer_factory_regression(self):
        """CE-9 regression [static]: neznámý substrát musí stále vyvolat NoPolicyError."""
        from server.cage.errors import NoPolicyError
        from server.cage.policy.enforcer import get_enforcer
        with pytest.raises(NoPolicyError):
            get_enforcer("unknown-substrate-regression-check")


# ---------------------------------------------------------------------------
# P2 — Smoke testy před každým cage-deploy (pre-deploy regression guardy)
# ---------------------------------------------------------------------------

@pytest.mark.regression
class TestPreDeployRegressionGuards:
    """P2: spustit PŘED každým cage-deploy jako smoke (lint guardy)."""

    def test_overlay_fly_config_lint_guard(self):
        """I7 pre-deploy guard: lint_overlay_fly_config nesmí FAILnout na aktuálním overlaye."""
        from server.cage.deploy.lint import lint_overlay_fly_config
        lint_overlay_fly_config(OVERLAY / "fly.workspace.toml")

    def test_drift_module_importable_regression(self):
        """CE-6 regression: drift modul musí být importovatelný (žádný syntax error po update)."""
        from server.cage.deploy import drift  # noqa: F401
        assert hasattr(drift, "check_drift")
        assert hasattr(drift, "compute_workspace_def_hash")

    def test_acl_module_importable_regression(self):
        """I2 regression: acl modul musí být importovatelný."""
        from server.cage.policy import acl  # noqa: F401
        assert hasattr(acl, "render_acl")
        assert hasattr(acl, "allow_domains")

    def test_cage_deploy_orchestrator_importable(self):
        """CE-2 regression: cage_deploy orchestrátor musí být importovatelný."""
        from server.cage.deploy.cage_deploy import DeployContext, run_deploy  # noqa: F401
        assert callable(run_deploy)


# ---------------------------------------------------------------------------
# Dokumentace: post-deploy-live AC body (nelze automatizovat zde)
# ---------------------------------------------------------------------------

class TestPostDeployLiveChecklist:
    """Připomínkový test: dokumentuje AC body, které NELZE ověřit staticky.

    Tyto testy vždy PASS (jsou jen dokumentace) — reálná verifikace
    probíhá přes containment_cage_harness.sh po deployi.
    """

    def test_document_live_checks_required(self):
        """Dokumentuje, které AC body vyžadují živou nasazenou klec."""
        live_checks = {
            "I1a": "curl https://example.com → exit ≠ 0 (host-enforced deny)",
            "I1b": "nc -w3 1.1.1.1 22 → exit ≠ 0 (H4 SSH deny)",
            "I1c": "ssh git@example.com → timeout (H4)",
            "I1d": "curl http://169.254.169.254/ → blokováno (H5 metadata)",
            "I1e": "nslookup na 8.8.8.8 → blokováno (H3 jen allowlisted resolver)",
            "I2a": "curl https://api.github.com → 2xx (proxy allow)",
            "I2b": "curl https://raw.githubusercontent.com → exit ≠ 0 (proxy deny)",
            "I2c": "curl https://<CF_TEAM>.cloudflareaccess.com → 2xx (proxy allow)",
            "I2d": "curl --noproxy '*' https://1.1.1.1 → exit ≠ 0 (H1 host deny)",
            "I3a": "pip install requests → network error (PyPI blokován)",
            "I3b": "npm i -g typescript → network error",
            "I3c": "apt update → network error",
            "I4a": "capsh --print | grep net_admin → prázdný",
            "I4b": "nft list ruleset → EPERM",
            "I4c": "nft flush ruleset → EPERM",
            "I5a": "find smokescreen* → nic v agent FS",
            "I5b": "env | grep proxy → jen endpoint URL",
            "I5c": "curl proxy management → 404/refused",
            "I6a": "/proc/self/status NoNewPrivs: 1",
            "I6b": "setuid bináry: žádné síťové utility",
            "I7a": "z externího hosta: curl workspace → timeout (NUTNO ZVENKU)",
            "I7c": "I7a + I7b re-test po každém deployi (MANDATORNÍ)",
            "I8a": "fly apps list → 2 entity (dream-team-app + workspace)",
            "I8b": "ip route → bez překryvu s app machine IP",
            "I8c": "fly volumes list → žádný sdílený volume",
            "I9a": "env | grep TUNNEL/CF_ACCESS_AUD/GH_TOKEN/BOOTSTRAP → prázdný",
            "I9b": "grep secrets /workspace/home/root → prázdný",
            "I10a": "gh auth status → not logged in nebo read-only",
            "I10b": "git push jiné-repo → permission denied",
            "I11a": "find entrypoint/cage-deploy → nic v agent FS",
            "I11b": "env | grep cage → prázdný",
            "I11c": "/proc/1/cmdline → bez cage identifikátoru",
        }
        # Test vždy projde — slouží jen jako dokumentace + počítač AC bodů
        assert len(live_checks) == 32, f"Počet live AC bodů: {len(live_checks)}"
        # Ověřit, že je harness script přítomen
        harness = Path(__file__).parent / "containment_cage_harness.sh"
        assert harness.is_file(), (
            f"Acceptance harness chybí: {harness}\n"
            "Spustit post-deploy: bash tests/acceptance/containment_cage_harness.sh"
        )
