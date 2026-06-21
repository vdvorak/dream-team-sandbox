"""test_reflow_staleness.py — re-flow staleness transitivita (2026-06-18, vlna app-shell BUG 2).

Re-flow z auditora (code-quality/design-audit FAIL) vrátil na implementační uzel (ui-system),
ten změnil implementaci → downstream verifikační uzly (qa, code-lint), které z té implementace
vychází, MUSÍ zestárnout a znovu proběhnout PŘED uzávěrem vlny. Dřív nezestárly (zůstaly
"completed"), protože `uncomplete` cíl jen vyhodil z completed, ale jeho výstupní typy
(ui-components, …) NEpřeverzoval → verzová staleness je neviděla.

Fix: `RunState.uncomplete(target, outputs)` invaliduje výstupní typy cíle (bump epoch) a smaže
jeho node-verzi → downstream konzumenti těch typů zestárnou skrz EXISTUJÍCÍ verzový mechanismus
a tier-po-tieru se re-runnou (scoped re-flow E1 drží — invaliduje se jen to, co cíl produkuje).

Graf zrcadlí delivery.yaml řetěz: ui-system → web → code-lint → qa.
Pouští se z .agentic root: `cd .agentic && pytest scripts/pipeline/tests`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from frontier import Ctx, Frontier   # noqa: E402
from graph import Edge, Graph, make_node   # noqa: E402
from runstate import RunState         # noqa: E402


def make_graph(nodes_raw: dict, edges_raw: list, entry: str) -> Graph:
    nodes = {nid: make_node(nid, raw) for nid, raw in nodes_raw.items()}
    edges = [Edge(e) for e in edges_raw]
    meta = {"entry": entry}
    return Graph(nodes, edges, meta, {"nodes": nodes_raw, "edges": edges_raw, "meta": meta})


def make_frontier(graph: Graph, state: RunState, flags: dict) -> Frontier:
    ctx = Ctx(graph=graph, artifacts=None, flags=dict(flags), targets={"web"},
              targets_declared=True, agent_status={}, cls=None, outcome=None, role_status={})
    return Frontier(graph, ctx, state, {})


def _impl_chain_graph() -> Graph:
    """ui-system → web → code-lint → qa (dataflow přes type-inputs jako v delivery.yaml)."""
    nodes_raw = {
        "ui-system": {"type": "agent", "agent": "leonard-ui",
                      "inputs": ["spec"], "outputs": ["ui-components"]},
        "web":       {"type": "agent", "agent": "peter-web",
                      "inputs": ["ui-components"], "outputs": ["web-code"]},
        "code-lint": {"type": "gate", "agent": "vitek-quality",
                      "inputs": ["web-code"], "outputs": ["gate-output"]},
        "qa":        {"type": "gate", "agent": "joey-qa",
                      "inputs": ["web-code"], "outputs": ["gate-output"]},
    }
    edges_raw = [
        {"from": "ui-system", "to": "web"},
        {"from": "web",       "to": "code-lint", "when": "PASS"},
        {"from": "code-lint", "to": "qa", "when": "PASS"},
    ]
    return make_graph(nodes_raw, edges_raw, entry="ui-system")


FLAGS = {"has_ui": True, "touches_shared_ui": True}


def _all_done_state() -> RunState:
    """Vlna prošla celým řetězem (verze orazítkované monotónně)."""
    st = RunState({
        "completed": ["ui-system", "web", "code-lint", "qa"],
        "outcomes": {"ui-system": "PASS", "web": "PASS", "code-lint": "PASS", "qa": "PASS"},
        "frontier": [], "skipped": [], "flags": FLAGS,
        "epoch": 4,
        "node_versions": {"ui-system": 1, "web": 2, "code-lint": 3, "qa": 4},
        "type_versions": {"ui-components": 1, "web-code": 2},
    })
    st.ensure_result_keys()
    return st


def test_uncomplete_invalidates_output_type_versions():
    """Jádro fixu: re-flow un-completne cíl A převerzuje jeho výstupní typy + smaže node-verzi."""
    st = _all_done_state()
    graph = _impl_chain_graph()
    st.uncomplete("ui-system", list(graph.nodes["ui-system"].outputs))
    assert "ui-system" not in st.completed
    assert st.type_versions["ui-components"] > 1, "výstupní typ cíle musí dostat novou verzi"
    assert "ui-system" not in st.node_versions, "node-verze cíle smazána (bude přepracován)"


def test_reflow_stales_direct_consumer():
    """Po re-flow na ui-system se přímý konzument ui-components (web) stane stale."""
    st = _all_done_state()
    graph = _impl_chain_graph()
    st.uncomplete("ui-system", list(graph.nodes["ui-system"].outputs))
    valid = make_frontier(graph, st, FLAGS)._valid_completed_via_deps()
    assert "web" not in valid, "web konzumuje ui-components → po re-flow stale"


def test_reflow_transitive_to_verifiers_after_web_rerun():
    """Tranzitivita tier-po-tieru: jakmile se web po opravě re-runne (bump web-code), zestárnou
    i verifikační uzly (code-lint, qa), které web-code konzumují → znovu proběhnou před uzávěrem."""
    st = _all_done_state()
    graph = _impl_chain_graph()
    st.uncomplete("ui-system", list(graph.nodes["ui-system"].outputs))
    st.mark_completed("ui-system")            # ui-system přepracován
    st.stamp("ui-system", ["ui-components"])
    st.mark_completed("web")                  # web přepracován (bump web-code)
    st.stamp("web", ["web-code"])
    valid = make_frontier(graph, st, FLAGS)._valid_completed_via_deps()
    assert "code-lint" not in valid, "code-lint konzumuje web-code → po re-runu web stale"
    assert "qa" not in valid, "qa konzumuje web-code → po re-runu web stale; jinak regrese proklouzne"


def test_healthy_run_keeps_all_valid():
    """Fix NEpřeinvaliduje: bez re-flow zůstanou všechny uzly valid (staleness se nespouští)."""
    st = _all_done_state()
    graph = _impl_chain_graph()
    valid = make_frontier(graph, st, FLAGS)._valid_completed_via_deps()
    assert {"ui-system", "web", "code-lint", "qa"} <= valid


# Frontier._valid_completed je private a bere deps — tenký helper pro čitelnost testů.
def _valid_completed_via_deps(self):   # noqa: ANN001
    return self._valid_completed(self._live_deps())


Frontier._valid_completed_via_deps = _valid_completed_via_deps
