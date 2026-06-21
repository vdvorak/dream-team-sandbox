"""Unit testy graph.py — Node factory/podtřídy, is_active, drive_category, blocking,
Edge normalizace, Graph.load + dotazy (forward_producers/reachable/return cíle)."""
import pytest
import yaml

from graph import (AgentNode, Edge, GateNode, Graph, HumanGateNode, JoinNode, Node,
                   RouterNode, TerminalNode, make_node)
from predicate import Predicate


# ── Node factory + podtřídy ─────────────────────────────────────────────────────
def test_make_node_factory():
    cases = {"agent": AgentNode, "gate": GateNode, "human-gate": HumanGateNode,
             "router": RouterNode, "join": JoinNode, "terminal": TerminalNode}
    for t, cls in cases.items():
        assert type(make_node("x", {"type": t})) is cls
    assert type(make_node("x", {})) is AgentNode            # bez type → agent default
    generic = make_node("x", {"type": "gateway"})           # neznámý → generický Node (lenientní)
    assert type(generic) is Node and generic.type == "gateway"


def test_node_attrs_and_when_parsed():
    n = make_node("backend", {"type": "agent", "agent": "bob", "phase": "T2",
                              "inputs": ["contract"], "outputs": ["code"], "when": "has_db"})
    assert (n.id, n.agent, n.phase) == ("backend", "bob", "T2")
    assert n.inputs == ["contract"] and n.outputs == ["code"] and n.io_names() == ["contract", "code"]
    assert isinstance(n.when, Predicate) and n.when.root is not None


def test_node_requires_none_vs_empty():
    assert make_node("x", {}).requires is None              # neuvedeno ≠ prázdný list
    assert make_node("x", {"requires": []}).requires == []


# ── Node.is_active (role gating + when) ─────────────────────────────────────────
def test_is_active_role_inactive(make_ctx):
    n = make_node("web", {"type": "agent"})
    assert n.is_active(make_ctx(role_status={"web": "inactive"})) == "inactive"


def test_is_active_agent_backcompat(make_ctx):
    n = make_node("web", {"type": "agent", "agent": "peter"})
    assert n.is_active(make_ctx(agent_status={"peter": "inactive"})) == "inactive"


def test_is_active_when(make_ctx):
    n = make_node("web", {"type": "agent", "when": "has_db"})
    assert n.is_active(make_ctx(flags={"has_db": True})) == "active"
    assert n.is_active(make_ctx(flags={"has_db": False})) == "inactive"   # when skip
    assert n.is_active(make_ctx()) == "unknown"                           # when judgment


def test_is_active_no_when_is_active(make_ctx):
    assert make_node("web", {"type": "agent"}).is_active(make_ctx()) == "active"


# ── drive_category + human-gate blocking ────────────────────────────────────────
def test_drive_category():
    assert make_node("x", {"type": "agent"}).drive_category() == "WORKER"
    assert make_node("x", {"type": "gate"}).drive_category() == "WORKER"
    assert make_node("x", {"type": "router"}).drive_category() == "ROUTER"
    assert make_node("x", {"type": "join"}).drive_category() == "JOIN"
    assert make_node("x", {"type": "terminal"}).drive_category() == "TERMINAL"
    assert make_node("x", {"type": "gateway"}).drive_category() is None   # generický → bez kategorie


def test_drive_category_humangate_splits_by_blocking():
    hg = make_node("g", {"type": "human-gate"})
    assert hg.drive_category(blocking=True) == "BLOCKING_GATE"
    assert hg.drive_category(blocking=False) == "FREE_GATE"


def test_humangate_blocking_resolution():
    hg = make_node("g", {"type": "human-gate", "interaction": "approve", "level": "L3"})
    assert hg.blocking({"approve": {"blocking": True}}) is True
    assert hg.blocking({"approve": {"blocking": False}}) is False
    assert hg.blocking({}) is True                         # fallback level == L3
    hg2 = make_node("g", {"type": "human-gate", "interaction": "ack", "level": "L1"})
    assert hg2.blocking({}) is False
    # ne-human-gate uzel nikdy neblokuje
    assert make_node("x", {"type": "agent"}).blocking({}) is False


# ── Edge ────────────────────────────────────────────────────────────────────────
def test_edge_to_normalization():
    assert Edge({"from": "a", "to": "b"}).to == ["b"]
    assert Edge({"from": "a", "to": ["b", "c"]}).to == ["b", "c"]
    e = Edge({"from": "a"})                                # chybí to → [None] (C2 to reportuje)
    assert e.to == [None] and e.live_targets() == []


def test_edge_kind_defaults_and_direction():
    assert Edge({"from": "a", "to": "b"}).kind == "normal"            # default
    assert Edge({"from": "a", "to": "b"}).is_forward() is True
    ret = Edge({"from": "a", "to": "b", "kind": "return"})
    assert ret.is_return() is True and ret.is_forward() is False


# ── Graph.load + dotazy ─────────────────────────────────────────────────────────
@pytest.fixture
def small_graph(tmp_path):
    data = {
        "meta": {"entry": "intake"},
        "nodes": {
            "intake": {"type": "router"},
            "product": {"type": "agent", "phase": "T1"},
            "backend": {"type": "agent", "phase": "T2", "outputs": ["code"]},
            "qa": {"type": "agent", "phase": "T3"},
            "audit-join": {"type": "join", "requires": ["qa"]},
            "done": {"type": "terminal"},
        },
        "edges": [
            {"from": "intake", "to": "product"},
            {"from": "product", "to": "backend"},
            {"from": "backend", "to": "qa"},
            {"from": "qa", "to": "audit-join"},
            {"from": "audit-join", "to": "done"},
            {"from": "qa", "to": "backend", "kind": "return", "when": "fault == contract"},
        ],
    }
    p = tmp_path / "delivery.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return Graph.load(str(p))


def test_graph_contains_iter_get(small_graph):
    assert "backend" in small_graph and "ghost" not in small_graph
    assert small_graph.get("backend").id == "backend"
    assert set(small_graph) == {"intake", "product", "backend", "qa", "audit-join", "done"}
    assert small_graph.entry == "intake"


def test_graph_nodes_by_type(small_graph):
    assert [n.id for n in small_graph.nodes_by_type("terminal")] == ["done"]
    assert small_graph.has_type("join") is True and small_graph.has_type("gateway") is False


def test_graph_forward_producers_skips_return(small_graph):
    fp = small_graph.forward_producers()
    assert fp["backend"] == ["product"]    # return hrana qa→backend se NEpočítá
    assert fp["qa"] == ["backend"]
    assert fp["intake"] == []


def test_graph_reachable(small_graph):
    assert small_graph.reachable("intake") == \
        {"intake", "product", "backend", "qa", "audit-join", "done"}
    assert "backend" not in small_graph.reachable("intake", skip="product")


def test_graph_return_target_for_fault(small_graph):
    assert small_graph.return_target_for_fault("qa", "contract") == "backend"
    assert small_graph.return_target_for_fault("qa", "spec") is None


def test_graph_single_return_target(small_graph):
    assert small_graph.single_return_target("qa") == "backend"
    assert small_graph.single_return_target("backend") is None   # žádné return hrany


def test_graph_all_predicates_labels(small_graph):
    labels = [where for _p, where in small_graph.all_predicates()]
    assert "node 'backend'" in labels
    assert any(w.startswith("edge qa→") for w in labels)


def test_graph_load_lenient_unknown_type(tmp_path):
    data = {"meta": {"entry": "a"}, "nodes": {"a": {"type": "gateway"}}, "edges": []}
    p = tmp_path / "g.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    g = Graph.load(str(p))                       # nesmí spadnout (check ho reportuje)
    assert type(g.get("a")) is Node and g.get("a").type == "gateway"
