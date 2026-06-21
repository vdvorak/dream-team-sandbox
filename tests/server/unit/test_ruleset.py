"""Unit testy — ruleset H1–H7 generování (tvar, pořadí, kompletnost, fail-closed).

Acceptance vazba: I1 (default-deny), I2 (allow tvar), I7 (ingress deny), CE-2 (fail-closed).
"""

import pytest

from server.cage.errors import NoPolicyError
from server.cage.policy.ruleset import (
    RULE_IDS,
    Action,
    Direction,
    RulesetParams,
    assert_complete,
    build_ruleset,
)


def test_ruleset_has_exactly_h1_to_h7_in_order():
    rs = build_ruleset()
    assert [r.id for r in rs] == list(RULE_IDS) == ["H1", "H2", "H3", "H4", "H5", "H6", "H7"]


def test_allow_before_deny_semantics_ordering():
    # explicit ALLOW (H1–H3) MUSÍ předcházet default-deny (H6), jinak deny přebije allow.
    rs = build_ruleset()
    idx = {r.id: i for i, r in enumerate(rs)}
    assert idx["H1"] < idx["H6"]
    assert idx["H2"] < idx["H6"]
    assert idx["H3"] < idx["H6"]


def test_h1_allows_443_only_to_proxy_cidr():
    rs = build_ruleset()
    h1 = next(r for r in rs if r.id == "H1")
    assert h1.action == Action.ALLOW
    assert h1.protocol == "tcp/443"
    assert h1.direction == Direction.EGRESS


def test_h4_denies_ssh_egress_anywhere():
    rs = build_ruleset()
    h4 = next(r for r in rs if r.id == "H4")
    assert h4.action == Action.DENY
    assert h4.protocol == "tcp/22"
    assert h4.target == "*"


def test_h5_blackholes_metadata():
    rs = build_ruleset()
    h5 = next(r for r in rs if r.id == "H5")
    assert h5.action == Action.DROP  # blackhole, ne reject


def test_h6_is_default_deny_egress():
    rs = build_ruleset()
    h6 = next(r for r in rs if r.id == "H6")
    assert h6.action == Action.DENY
    assert h6.direction == Direction.EGRESS
    assert h6.target == "*"


def test_h7_denies_all_ingress():
    rs = build_ruleset()
    h7 = next(r for r in rs if r.id == "H7")
    assert h7.action == Action.DENY
    assert h7.direction == Direction.INGRESS


def test_spike_params_change_target_not_structure():
    # Spike-parametr (DNS resolver) změní jen cílovou hodnotu, NE strukturu/pořadí.
    custom = RulesetParams(dns_resolver_ip="10.0.0.53")
    rs = build_ruleset(custom)
    assert [r.id for r in rs] == list(RULE_IDS)
    h3 = next(r for r in rs if r.id == "H3")
    assert h3.target == "10.0.0.53/32"


def test_assert_complete_passes_for_full_ruleset():
    assert_complete(build_ruleset())  # nesmí raisnout


def test_assert_complete_fails_closed_on_missing_rule():
    # Fail-closed (CE-2/I1): neúplný ruleset (chybí H6 default-deny) → NoPolicyError.
    rs = [r for r in build_ruleset() if r.id != "H6"]
    with pytest.raises(NoPolicyError):
        assert_complete(rs)


def test_assert_complete_fails_closed_on_reordered_rules():
    rs = build_ruleset()
    rs[0], rs[5] = rs[5], rs[0]  # přeházení pořadí
    with pytest.raises(NoPolicyError):
        assert_complete(rs)
