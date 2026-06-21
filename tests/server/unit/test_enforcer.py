"""Unit testy — host-policy enforcer adapter (render, fail-closed apply, factory).

Acceptance vazba: I1 (host-enforced garance), CE-1/CE-9 (substrát-agnostika),
CE-2 (fail-closed: API selže → ABORT, ne pokračuj).
"""

import pytest

from server.cage.errors import NoPolicyError, PolicyApplyFailedError
from server.cage.policy.enforcer import FlyNetworkPolicyAdapter, get_enforcer
from server.cage.policy.ruleset import build_ruleset


def test_render_preserves_rule_order_as_priority():
    adapter = FlyNetworkPolicyAdapter(app="dream-team-workspace")
    payload = adapter.render(build_ruleset())
    ids = [r["id"] for r in payload["rules"]]
    prios = [r["priority"] for r in payload["rules"]]
    assert ids == ["H1", "H2", "H3", "H4", "H5", "H6", "H7"]
    assert prios == list(range(7))  # priorita = pořadí (ALLOW před default-deny)
    assert payload["default_action"] == "deny"  # default-deny posture


def test_apply_success_calls_api_2xx():
    calls = []

    def fake_post(url, body, headers):
        calls.append((url, body, headers))
        return 200, "ok"

    adapter = FlyNetworkPolicyAdapter(app="dream-team-workspace", http_post=fake_post)
    adapter.validate_and_apply(build_ruleset())  # nesmí raisnout
    assert len(calls) == 1
    assert "network_policies" in calls[0][0]


def test_apply_fails_closed_on_non_2xx():
    # Fail-closed (CE-2): API vrátí 500 → PolicyApplyFailedError → deploy ABORT.
    def fake_post(url, body, headers):
        return 500, "internal error"

    adapter = FlyNetworkPolicyAdapter(http_post=fake_post)
    with pytest.raises(PolicyApplyFailedError):
        adapter.validate_and_apply(build_ruleset())


def test_apply_fails_closed_on_transport_exception():
    def fake_post(url, body, headers):
        raise ConnectionError("network down")

    adapter = FlyNetworkPolicyAdapter(http_post=fake_post)
    with pytest.raises(PolicyApplyFailedError):
        adapter.validate_and_apply(build_ruleset())


def test_apply_fails_closed_when_no_transport():
    # Bez nakonfigurovaného transportu nelze policy aplikovat ANI ověřit → ABORT.
    adapter = FlyNetworkPolicyAdapter(http_post=None)
    with pytest.raises(PolicyApplyFailedError):
        adapter.validate_and_apply(build_ruleset())


def test_validate_and_apply_rejects_incomplete_ruleset():
    # Neúplný ruleset → NoPolicyError PŘED jakýmkoli API voláním (I1).
    called = []
    adapter = FlyNetworkPolicyAdapter(http_post=lambda *a: called.append(1) or (200, ""))
    incomplete = [r for r in build_ruleset() if r.id != "H6"]
    with pytest.raises(NoPolicyError):
        adapter.validate_and_apply(incomplete)
    assert called == []  # apply se NESMÍ zavolat s děravou policy


def test_factory_returns_fly_adapter():
    assert isinstance(get_enforcer("fly"), FlyNetworkPolicyAdapter)


def test_factory_unknown_substrate_fails_closed():
    # CE-9 + CE-2: neznámý/neimplementovaný substrát → NoPolicyError (ne tichý no-policy).
    with pytest.raises(NoPolicyError):
        get_enforcer("vps-nftables")
