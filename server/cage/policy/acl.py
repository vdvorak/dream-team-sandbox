"""Smokescreen ACL render (vrstva 1 — doménový egress proxy, GRANULARITA).

ACL je render-time šablona (contracts §1): CF Access team doména se NEHARDCODUJE,
injektuje se z env `CF_ACCESS_TEAM_DOMAIN` při deploy (rozhodnutí (d)).

Opacita (CE-4 / I5 / I11): vyrenderovaný ACL existuje jen v runtime proxy procesu pod
jiným (proxy) uid, soubor mode 0400 root:root. NIKDY se nekopíruje čitelně do workspace
image / FS dosažitelného agentem. Tento modul vrací jen text + render kontrakt; fyzické
umístění (mode/uid) řeší entrypoint klece (server/cage/overlay/entrypoint.sh, krok 0).

Allowlist (contracts §1, stack):
  - api.github.com                                   (I2: 2a)
  - ${CF_ACCESS_TEAM_DOMAIN}.cloudflareaccess.com    (I2: 2c, šablonováno z env)
  default: deny  → raw.githubusercontent.com, PyPI, npmjs, apt NEjsou v allow (I2/I3)
"""

from __future__ import annotations

import os
import re

from server.cage.errors import CageError

# Statický allow seznam (mimo CF doménu). Drží se contracts §1 — žádné build-time hosty.
STATIC_ALLOW_DOMAINS: tuple[str, ...] = ("api.github.com",)

# CF Access team doména: jméno → "<team>.cloudflareaccess.com". Validace jména (níže).
CF_ACCESS_SUFFIX = "cloudflareaccess.com"

# Povolený tvar team domény (subdoména label): písmena/číslice/pomlčka, ne na okrajích.
# WHY: injekt z env — bránit injektáži dalších domén/řádků do ACL přes hodnotu env.
_CF_TEAM_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

ACL_FILE_MODE = 0o400  # I5: ACL čitelný jen pro proxy/root, ne pro agenta


class AclTemplateError(CageError):
    """Chybný/nebezpečný vstup do ACL šablony (např. nevalidní CF team doména)."""

    code = "ERR_NO_POLICY"  # mapuje na fail-closed deploy ABORT (chybí validní policy)


def _validate_cf_team(team: str) -> str:
    """Ověř, že CF team doména je jeden bezpečný DNS label. Fail-closed při nevalidnosti.

    WHY (CE-2): hodnota přichází z env při deploy. Nevalidní/prázdná hodnota by buď
    rozbila ACL, nebo umožnila injektáž → raději deploy ABORT než děravý allowlist.
    """
    team = (team or "").strip().lower()
    if not team:
        raise AclTemplateError(
            "CF_ACCESS_TEAM_DOMAIN není nastaven — nelze vyrenderovat ACL (fail-closed)"
        )
    # Pokud operátor omylem zadal celé FQDN, vezmi první label a ověř zbytek.
    if team.endswith("." + CF_ACCESS_SUFFIX):
        team = team[: -(len(CF_ACCESS_SUFFIX) + 1)]
    if "." in team or not _CF_TEAM_RE.match(team):
        raise AclTemplateError(
            f"CF_ACCESS_TEAM_DOMAIN '{team}' není validní team label "
            "(očekává se jediný DNS label, např. 'myteam')"
        )
    return team


def cf_access_domain(team: str) -> str:
    """Sestaví plnou CF Access doménu z (ověřeného) team labelu."""
    return f"{_validate_cf_team(team)}.{CF_ACCESS_SUFFIX}"


def allow_domains(cf_team_domain: str) -> list[str]:
    """Kompletní allow seznam domén (static + CF Access). Pořadí: static, pak CF."""
    return list(STATIC_ALLOW_DOMAINS) + [cf_access_domain(cf_team_domain)]


def render_acl(cf_team_domain: str | None = None) -> str:
    """Vyrenderuje Smokescreen ACL YAML. CF doména z argumentu nebo z env (fail-closed).

    Vrací textový obsah; zápis s mode 0400 řeší entrypoint (I5). NEpíše na FS sám.
    """
    if cf_team_domain is None:
        cf_team_domain = os.environ.get("CF_ACCESS_TEAM_DOMAIN", "")
    domains = allow_domains(cf_team_domain)
    lines = [
        "# smokescreen-acl.yaml — vygenerováno cage-deploy (render-time, CE-4/I5).",
        "# CF Access doména injektnuta z env CF_ACCESS_TEAM_DOMAIN (rozhodnutí (d)).",
        "# default: deny → raw.githubusercontent.com / PyPI / npmjs / apt = DENY (I2/I3).",
        "version: 1",
        "default: deny",
        "allow:",
    ]
    for d in domains:
        lines.append(f"  - domain: {d}")
    return "\n".join(lines) + "\n"
