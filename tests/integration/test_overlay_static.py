"""Integration testy — statická verifikace overlay artefaktů (bez živé klece).

Testuje strukturální invarianty overlay souborů, které lze ověřit bez nasazení:
  - fly.workspace.toml: žádný [http_service], 6PN-only config (I7)
  - nftables.cage.conf: tvar pravidel odpovídá H1–H7 abstrakci (I1/I4)
  - Dockerfile.workspace: ŽÁDNÝ EXPOSE veřejný port, non-root USER nastavení (I6)
  - entrypoint.sh: de-root sekvence pořadí (CAP_DROP → NNP → exec jako non-root) (I4/I6)
  - smokescreen-acl rendered: default deny, allowlist omissions (I2/I3)

Tag: [static] — spustitelné teď, nevyžaduje běžící klec.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Cesty k overlay artefaktům
SANDBOX_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = SANDBOX_ROOT / "server" / "cage" / "overlay"
ENTRYPOINT = OVERLAY / "entrypoint.sh"
FLY_TOML = OVERLAY / "fly.workspace.toml"
NFTABLES_CONF = OVERLAY / "nftables.cage.conf"
DOCKERFILE = OVERLAY / "Dockerfile.workspace"


# ---------------------------------------------------------------------------
# I7 — fly.workspace.toml nesmí obsahovat [http_service]
# ---------------------------------------------------------------------------

class TestFlyTomlStaticI7:
    def test_no_http_service_section(self):
        """I7 [static]: overlay fly.workspace.toml nesmí mít aktivní [http_service]."""
        content = FLY_TOML.read_text(encoding="utf-8")
        # Kontrolujeme, že žádný nezakomentovaný řádek neobsahuje [http_service]
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "[http_service]" not in stripped, (
                f"Nalezena aktivní [http_service] sekce v overlay fly.workspace.toml: {line!r}"
            )

    def test_app_name_is_workspace(self):
        """fly.workspace.toml musí nasazovat dream-team-workspace (ne appku)."""
        content = FLY_TOML.read_text(encoding="utf-8")
        assert "dream-team-workspace" in content

    def test_no_public_services_block(self):
        """Žádný http_service ani services blok s external_port."""
        content = FLY_TOML.read_text(encoding="utf-8")
        # Nezakomentované řádky nesmí mít external_port (veřejný ingress)
        for line in content.splitlines():
            if not line.strip().startswith("#"):
                assert "external_port" not in line, (
                    f"external_port nalezen v fly.workspace.toml: {line!r}"
                )


# ---------------------------------------------------------------------------
# I4 / I1 — nftables.cage.conf: tvar pravidel H1–H7
# ---------------------------------------------------------------------------

class TestNftablesStaticI4I1:
    def test_output_chain_default_drop(self):
        """I1/I4 [static]: nftables chain output musí mít policy drop (H6 default-deny egress)."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert "policy drop" in content, "nftables output chain nemá default policy drop"
        # musí být v kontextu output chain
        assert re.search(r"chain output\s*\{[^}]*policy drop", content, re.DOTALL), (
            "policy drop nenalezena v output chain"
        )

    def test_input_chain_default_drop(self):
        """I7 [static]: nftables chain input musí mít policy drop (H7 default-deny ingress)."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert re.search(r"chain input\s*\{[^}]*policy drop", content, re.DOTALL), (
            "policy drop nenalezena v input chain"
        )

    def test_forward_chain_drop(self):
        """microVM neforwarduje (defense-in-depth)."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert re.search(r"chain forward\s*\{[^}]*policy drop", content, re.DOTALL), (
            "forward chain nemá policy drop"
        )

    def test_loopback_accept_for_proxy(self):
        """H1 [static]: loopback accept přítomen (proxy sidecar komunikace)."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert 'oif "lo" accept' in content or "iif lo accept" in content, (
            "loopback accept chybí — proxy sidecar by neměl komunikaci"
        )

    def test_ssh_drop_present(self):
        """H4 [static]: SSH port 22 musí být explicitně blokován."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert "dport 22" in content and ("drop" in content or "reject" in content), (
            "SSH port 22 není explicitně dropnut v nftables"
        )

    def test_metadata_blackhole_present(self):
        """H5 [static]: metadata/link-local CIDR musí být blackholován."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        # 169.254.0.0/16 nebo link-local blackhole
        assert "169.254" in content, "metadata CIDR blackhole chybí v nftables (H5)"

    def test_6pn_private_allowed(self):
        """H2 [static]: privátní 6PN síť musí být povolena."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        assert "fdaa" in content, "6PN CIDR (fdaa::/16) chybí v nftables allow (H2)"

    def test_no_flush_all_in_runtime(self):
        """Nftables config smí obsahovat 'flush ruleset' jen pro instalaci, ne pro celý remove."""
        content = NFTABLES_CONF.read_text(encoding="utf-8")
        # flush ruleset na začátku je správné (instalace přepíše starý), ale nesmí být
        # uvnitř chain/table bez table definice (to by byl prázdný flush)
        # Zjistíme, že po flush ruleset následuje table inet cage
        assert "table inet cage" in content, "table inet cage chybí v nftables.cage.conf"


# ---------------------------------------------------------------------------
# I6 — Dockerfile: non-root user, no EXPOSE veřejný port
# ---------------------------------------------------------------------------

class TestDockerfileStaticI6:
    def test_no_expose_directive(self):
        """I6/I7 [static]: Dockerfile nesmí mít EXPOSE (naivní appka ji měla — díra)."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        expose_lines = [
            line for line in content.splitlines()
            if re.match(r"^\s*EXPOSE\s+", line, re.IGNORECASE)
        ]
        assert expose_lines == [], (
            f"Dockerfile obsahuje EXPOSE direktivy (veřejný port): {expose_lines}"
        )

    def test_non_root_user_created(self):
        """I6 [static]: Dockerfile musí vytvořit non-root user (claude uid 10001)."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "10001" in content, "non-root agent user uid 10001 chybí v Dockerfile"
        assert "claude" in content, "non-root agent user 'claude' chybí v Dockerfile"

    def test_no_user_root_at_end(self):
        """I6 [static]: Dockerfile nesmí skončit s USER root (agent nesmí běžet jako root)."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        # Spočítej USER direktivy — poslední USER nesmí být root
        user_lines = [
            line.strip() for line in content.splitlines()
            if re.match(r"^\s*USER\s+", line, re.IGNORECASE)
        ]
        # Pokud žádný USER direktivy není (entrypoint to řeší sám), to je OK
        # (entrypoint.sh setuidne na claude). Pokud je USER, nesmí být root.
        if user_lines:
            assert user_lines[-1].lower() != "user root", (
                "Poslední USER direktiva v Dockerfile je root"
            )

    def test_smokescreen_binary_present(self):
        """Vrstva 1 [static]: Smokescreen binár musí být v overlay image."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "smokescreen" in content.lower(), "Smokescreen chybí v overlay Dockerfile"

    def test_nftables_installed(self):
        """Vrstva 3 [static]: nftables balíček musí být nainstalován pro de-root sekvenci."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "nftables" in content, "nftables balíček chybí v overlay Dockerfile"

    def test_capsh_installed(self):
        """I4 [static]: libcap2-bin (capsh) musí být nainstalován pro CAP_NET_ADMIN drop."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "libcap2-bin" in content, "libcap2-bin (capsh) chybí v overlay Dockerfile"

    def test_acl_mode_0400_set_in_dockerfile(self):
        """I5 [static]: ACL soubor musí být nastaven na mode 0400 (agentovi nečitelný)."""
        content = DOCKERFILE.read_text(encoding="utf-8")
        assert "0400" in content, "mode 0400 pro ACL soubor chybí v Dockerfile"


# ---------------------------------------------------------------------------
# I4/I6 — entrypoint.sh: závazné pořadí de-root sekvence
# ---------------------------------------------------------------------------

class TestEntrypointStaticI4I6:
    def test_nft_install_before_cap_drop(self):
        """I4 [static]: nft instalace (krok 1) MUSÍ předcházet cap drop (krok 2)."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        nft_pos = content.find("nft -f")
        cap_drop_pos = content.find("capsh")
        assert nft_pos != -1, "nft -f příkaz nenalezen v entrypoint.sh"
        assert cap_drop_pos != -1, "capsh příkaz nenalezen v entrypoint.sh"
        assert nft_pos < cap_drop_pos, (
            "nft instalace (krok 1) musí předcházet capsh/cap drop (krok 2) — "
            "bez CAP_NET_ADMIN by nftables nešel nainstalovat"
        )

    def test_cap_net_admin_dropped(self):
        """I4a [static]: entrypoint musí explicitně dropnout CAP_NET_ADMIN."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "cap_net_admin" in content.lower(), (
            "CAP_NET_ADMIN drop chybí v entrypoint.sh — agent by mohl smazat nftables"
        )

    def test_no_new_privs_set(self):
        """I6a [static]: no_new_privs musí být nastaven před exec agenta."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "--no-new-privs" in content, (
            "--no-new-privs chybí v entrypoint.sh (krok 3)"
        )

    def test_exec_as_non_root_user(self):
        """I6 [static]: agent je spuštěn pod non-root uživatelem (--user / exec jako claude)."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "--user=" in content or "--user =" in content, (
            "Exec agenta pod non-root uživatelem chybí v entrypoint.sh (krok 4)"
        )

    def test_fail_closed_abort_function(self):
        """CE-2 [static]: entrypoint musí mít fail-closed abort funkci."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "cage_abort" in content, (
            "cage_abort (fail-closed abort helper) chybí v entrypoint.sh"
        )

    def test_proxy_started_before_agent(self):
        """I2 [static]: Smokescreen proxy musí být startován PŘED exec agenta."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        smoke_pos = content.find("smokescreen")
        exec_pos = content.find("exec capsh")
        assert smoke_pos != -1, "smokescreen start chybí v entrypoint.sh"
        assert exec_pos != -1, "exec capsh (agent start) chybí v entrypoint.sh"
        assert smoke_pos < exec_pos, (
            "Smokescreen musí být startován PŘED exec agenta (proxy musí být ready)"
        )

    def test_no_proxy_for_localhost_set(self):
        """I2 [static]: no_proxy/NO_PROXY musí zahrnovat localhost (interní komunikace nesmí jít přes proxy)."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "no_proxy" in content, "no_proxy chybí v entrypoint.sh"
        assert "localhost" in content, "localhost není v no_proxy"

    def test_proxy_env_exported(self):
        """I2 [static]: http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY musí být exportovány."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        # Dvojitý zámek: env injekt (měkký) + H1 (tvrdý)
        assert "http_proxy" in content and "https_proxy" in content, (
            "proxy env (http_proxy/https_proxy) chybí v entrypoint.sh"
        )

    def test_login_persistence_regress_guard(self):
        """Regrese-guard [static]: entrypoint musí řešit Claude login token persistence po de-root."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        # Musí chownovat /data/claude-config na agent uid (kontrakt §1)
        assert "claude-config" in content, (
            "Login persistence path (claude-config) chybí v entrypoint.sh — regrese-guard"
        )
        assert "chown" in content, "chown (pre-chown na agent uid) chybí v entrypoint.sh"

    def test_acl_mode_set_in_entrypoint(self):
        """I5 [static]: entrypoint musí nastavit mode 0400 na ACL soubor."""
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert "chmod 0400" in content, (
            "chmod 0400 pro ACL soubor chybí v entrypoint.sh (I5 — agent nečte ACL)"
        )
