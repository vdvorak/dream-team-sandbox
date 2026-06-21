"""Unit testy check.py C10 produces-validace (P5 human-interaction registry).

Ověřuje typované I/O interakcí: každá `produces` = { artifact: ∈artifacts } | { outcome: ∈vocab }.
delegate-or-provide je platný kind."""
from check import INTERACTION_KINDS, _check_produces, check_forward_acyclic
from graph import Graph, make_node, Edge

ARTIFACTS = {"mockup": {}, "spec": {}}


def test_delegate_or_provide_is_valid_kind():
    assert "delegate-or-provide" in INTERACTION_KINDS


def test_produces_artifact_ok():
    assert _check_produces("i", {"produces": {"artifact": "mockup"}}, ARTIFACTS) == []


def test_produces_artifact_unknown():
    assert _check_produces("i", {"produces": {"artifact": "ghost"}}, ARTIFACTS) == \
        ["C10 interakce 'i': produces.artifact 'ghost' není v artifacts.yaml"]


def test_produces_outcome_ok():
    assert _check_produces("i", {"produces": {"outcome": "ACK"}}, ARTIFACTS) == []


def test_produces_outcome_unknown():
    out = _check_produces("i", {"produces": {"outcome": "BOGUS"}}, ARTIFACTS)
    assert out and "produces.outcome 'BOGUS'" in out[0]


def test_produces_missing():
    assert _check_produces("i", {}, ARTIFACTS) == \
        ["C10 interakce 'i': chybí typovaný 'produces' (artifact|outcome)"]


def test_produces_neither_artifact_nor_outcome():
    out = _check_produces("i", {"produces": {"foo": "bar"}}, ARTIFACTS)
    assert out and "musí mít 'artifact' nebo 'outcome'" in out[0]


def test_produces_artifact_skip_when_no_registry():
    # artifacts=None (SKIP režim) → artifact se neověřuje
    assert _check_produces("i", {"produces": {"artifact": "anything"}}, None) == []


# ── C17 forward-acyclic cycle-guard (finding #3 obrana do hloubky) ───────────────
def _g(nodes_ids, edges_raw):
    nodes = {i: make_node(i, {"type": "agent"}) for i in nodes_ids}
    edges = [Edge(e) for e in edges_raw]
    return Graph(nodes, edges, {"entry": nodes_ids[0]}, {})


def test_c17_acyclic_forward_graph_ok():
    """Lineární forward graf (a→b→c) → žádný cyklus, prázdné nálezy."""
    g = _g(["a", "b", "c"], [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}])
    assert check_forward_acyclic(g) == []


def test_c17_detects_forward_cycle():
    """Forward cyklus (a→b→a, zrcadlí ux-design↔ui-system z findingu #2) → C17 nález."""
    g = _g(["a", "b"], [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
    out = check_forward_acyclic(g)
    assert len(out) == 1 and out[0].startswith("C17 CYKLUS")
    assert "a" in out[0] and "b" in out[0]


def test_c17_return_edge_is_not_a_cycle():
    """Return hrana (re-flow) je ZÁMĚRNÁ zpětná hrana → C17 ji nepočítá jako cyklus.
    qa→backend forward, backend→qa return → DAG ve forward podgrafu."""
    g = _g(["backend", "qa"], [
        {"from": "backend", "to": "qa"},
        {"from": "qa", "to": "backend", "kind": "return"},
    ])
    assert check_forward_acyclic(g) == []


def test_c17_self_loop_forward():
    """Forward self-loop (a→a) → cyklus."""
    g = _g(["a"], [{"from": "a", "to": "a"}])
    out = check_forward_acyclic(g)
    assert len(out) == 1 and out[0].startswith("C17 CYKLUS")
