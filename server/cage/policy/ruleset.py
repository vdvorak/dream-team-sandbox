"""Abstraktní host-enforced egress ruleset H1–H7 (substrát-agnostický model).

Toto je JEDINÝ vstup pro libovolný enforcer adapter (CE-9): Fly Network Policy dnes,
nftables na hypervisor hostu na VPS později. Adapter překládá `ruleset → enforcer-specific
call`; struktura pravidel se NEMĚNÍ napříč substráty (contracts §3, §6).

Tvar pravidel přesně dle contracts/containment-cage.md §1 (tabulka H1–H7).

Pořadí semantiky (závazné): explicit ALLOW (H1–H3) → explicit DENY/DROP (H4–H5)
→ default-deny (H6–H7). Adapter MUSÍ pořadí zachovat (priorita = index v listu).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# --- Spike-to-confirm parametry (rozhodnutí (c), contracts §7) -----------------
# TODO-spike(heimdall): tyto hodnoty jsou PŘEDPOKLAD, ne finál. Heimdall ověří reálné
# hodnoty proti Fly microVM; STRUKTURA pravidel se nemění, jen se dosadí potvrzené IP/CIDR.
# Necháváme je jako konfigurovatelné parametry s rozumným defaultem (NEhardcoduj jinde).

# H3: Fly interní DNS resolver. Předpoklad = Fly interní resolver.
# TODO-spike(heimdall): potvrdit konkrétní IP a zda DNS jde tcp i udp (contracts §7).
DEFAULT_DNS_RESOLVER_IP = "169.254.0.2"

# H5: link-local / cloud metadata rozsah k blackhole.
# TODO-spike(heimdall): potvrdit, zda Fly metadata používá jiný rozsah než link-local.
DEFAULT_METADATA_CIDR = "169.254.0.0/16"

# H1: proxy sidecar CIDR. Loopback, protože Smokescreen běží in-VM jako sidecar
# (contracts §1) — H1 pak reálně reguluje, že proxy proces (vlastní non-root uid) smí ven.
DEFAULT_PROXY_CIDR = "127.0.0.1/32"

# H2: schválená privátní síť (6PN peers). Fly 6PN rozsah.
# TODO-spike(heimdall): potvrdit konkrétní 6PN CIDR aplikace.
DEFAULT_APPROVED_PRIVATE_CIDR = "fdaa::/16"


class Direction(str, Enum):
    EGRESS = "egress"
    INGRESS = "ingress"


class Action(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    DROP = "drop"  # blackhole (H5) — tichý zahoz, ne reject


@dataclass(frozen=True)
class Rule:
    """Jedno abstraktní pravidlo. `id` = H1..H7 (auditovatelnost, mapování na invariant)."""

    id: str
    direction: Direction
    protocol: str  # "tcp/443", "udp/53+tcp/53", "tcp/22", "any"
    target: str  # CIDR nebo "*"
    action: Action
    invariant: str  # který invariant pravidlo nese (audit)


@dataclass(frozen=True)
class RulesetParams:
    """Spike-konfigurovatelné parametry rulesetu. Defaulty = předpoklady (viz výše)."""

    proxy_cidr: str = DEFAULT_PROXY_CIDR
    approved_private_cidr: str = DEFAULT_APPROVED_PRIVATE_CIDR
    dns_resolver_ip: str = DEFAULT_DNS_RESOLVER_IP
    metadata_cidr: str = DEFAULT_METADATA_CIDR


# Závazné ID pravidel a jejich pořadí (priorita). Kontrolováno v testech (ruleset tvar).
RULE_IDS: tuple[str, ...] = ("H1", "H2", "H3", "H4", "H5", "H6", "H7")


def build_ruleset(params: RulesetParams | None = None) -> list[Rule]:
    """Sestaví kompletní ruleset H1–H7 v ZÁVAZNÉM pořadí.

    Pořadí v listu = priorita: explicit ALLOW → explicit DENY/DROP → default-deny.
    Adapter MUSÍ aplikovat v tomto pořadí (jinak default-deny H6 přebije ALLOW H1–H3).

    Fail-closed kontrola kompletnosti je v `assert_complete()`; tahle funkce vždy
    vrátí všech 7 pravidel (parametrizace nemění strukturu, jen cílové CIDR).
    """
    p = params or RulesetParams()
    return [
        # --- explicit ALLOW (H1–H3) ---
        Rule(
            id="H1",
            direction=Direction.EGRESS,
            protocol="tcp/443",
            target=p.proxy_cidr,  # proxy sidecar — H1 nese egress garanci (CE-1)
            action=Action.ALLOW,
            invariant="I2",
        ),
        Rule(
            id="H2",
            direction=Direction.EGRESS,
            protocol="tcp/443",
            target=p.approved_private_cidr,  # 6PN peers / privátní síť
            action=Action.ALLOW,
            invariant="I2,I8",
        ),
        Rule(
            id="H3",
            direction=Direction.EGRESS,
            protocol="udp/53+tcp/53",
            target=f"{p.dns_resolver_ip}/32",  # jen allowlisted resolver (DNS side-channel)
            action=Action.ALLOW,
            invariant="I1e",
        ),
        # --- explicit DENY/DROP (H4–H5) ---
        Rule(
            id="H4",
            direction=Direction.EGRESS,
            protocol="tcp/22",  # SSH ven NIKDY (pivot)
            target="*",
            action=Action.DENY,
            invariant="I1b,I1c",
        ),
        Rule(
            id="H5",
            direction=Direction.EGRESS,
            protocol="any",
            target=p.metadata_cidr,  # blackhole link-local/metadata (side-channel)
            action=Action.DROP,
            invariant="I1d",
        ),
        # --- default-deny (H6–H7) ---
        Rule(
            id="H6",
            direction=Direction.EGRESS,
            protocol="any",
            target="*",  # vše ostatní DENY (default-deny egress)
            action=Action.DENY,
            invariant="I1a",
        ),
        Rule(
            id="H7",
            direction=Direction.INGRESS,
            protocol="any",
            target="*",  # žádný veřejný ingress; jen privátní síť (6PN-only)
            action=Action.DENY,
            invariant="I7",
        ),
    ]


def assert_complete(ruleset: list[Rule]) -> None:
    """Fail-closed kontrola: ruleset MUSÍ obsahovat přesně H1–H7 ve správném pořadí.

    WHY (CE-2 / I1): deploy bez kompletního rulesetu = žádná egress garance →
    NoPolicyError → deploy ABORT. Raději odmítnout než aplikovat děravou politiku.
    """
    from server.cage.errors import NoPolicyError

    ids = [r.id for r in ruleset]
    if ids != list(RULE_IDS):
        raise NoPolicyError(
            f"ruleset neúplný/přeházený: očekáváno {list(RULE_IDS)}, je {ids}"
        )
    # Musí být přítomna default-deny "kotva" (H6 egress + H7 ingress).
    if not any(r.id == "H6" and r.action == Action.DENY and r.target == "*" for r in ruleset):
        raise NoPolicyError("chybí default-deny egress (H6)")
    if not any(r.id == "H7" and r.action == Action.DENY for r in ruleset):
        raise NoPolicyError("chybí default-deny ingress (H7)")
