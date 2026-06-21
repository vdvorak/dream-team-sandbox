"""Regресní test: lehká dráha (FIX #2) NESMÍ zacyklit drive na auto-skip uzlech.

KOŘENOVÁ PŘÍČINA (bug 2026-06-17, vlna cockpit-elapsed):
Drive u lightweight=true auto-skipuje `feasibility`+`architecture` (skip_if == TRUE):
mark_completed + set_outcome PASS. Jenže staleness fixpoint (`_valid_completed`) ten
completed uzel VYHODIL, protože jeho upstream producent (`product`) ještě neběžel a uzel
neměl version-stamp → downward-closure fallback ho označil jako stale. Vyhozený uzel pak
`_auto_skip()` znovu nabídl → drive ho znovu auto-skipnul → nekonečná smyčka (guard 200).

OPRAVA (frontier._valid_completed): uzel s pravdivým `skip_if` je vyřešen POLITIKOU
nezávisle na vstupech (výstupy úmyslně nevzniknou, downstream ho bere jako PASS). Takový
completed uzel je chráněný před invalidací staleness → zůstane v completed_set → `_auto_skip`
ho už nenabídne.

AC:
  AC-1: skip-eligible completed uzel s NEhotovým upstream NEZůstane stale (loop-fix jádro).
  AC-2: po jednom auto-skip kroku už `auto_skip` ten uzel NEobsahuje (idempotence → konec smyčky).
  AC-3: simulace drive smyčky nad lehkou dráhou konverguje (≤ pár iterací) a doběhne na další
        REÁLNÝ uzel (product / ux-design), místo aby se točila na feasibility/architecture.
  AC-4: kontrast — bez lightweight flagu se uzly NEskipují (skip_if FALSE → běží normálně).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from frontier import Ctx, Frontier  # noqa: E402
from graph import Edge, Graph, make_node  # noqa: E402
from runstate import RunState  # noqa: E402


def _lightweight_graph() -> Graph:
    """Zúžený otisk delivery.yaml lehké dráhy: product → feasibility(skip_if) →
    architecture(skip_if) → backend(consume contract). has_ui=true větev: ux-design."""
    nodes_raw = {
        "product": {"type": "agent", "outputs": ["spec", "acceptance"]},
        "feasibility": {"type": "gate", "skip_if": "flags.lightweight",
                        "inputs": ["spec"], "outputs": ["gate-output"]},
        "architecture": {"type": "agent", "skip_if": "flags.lightweight",
                         "inputs": ["spec", "acceptance"],
                         "outputs": ["contract"]},
        "backend": {"type": "agent", "when": "project.has_server",
                    "inputs": ["contract"], "outputs": ["server-code"]},
    }
    edges_raw = [
        {"from": "product", "to": "feasibility", "when": "PASS"},
        {"from": "feasibility", "to": "architecture", "when": "PASS"},
        {"from": "architecture", "to": "backend",
         "when": "project.has_server", "kind": "normal"},
    ]
    return make_graph(nodes_raw, edges_raw, entry="product")


def make_graph(nodes_raw: dict, edges_raw: list, entry: str | None = None) -> Graph:
    nodes = {nid: make_node(nid, raw) for nid, raw in nodes_raw.items()}
    edges = [Edge(e) for e in edges_raw]
    meta = {"entry": entry or (next(iter(nodes_raw)) if nodes_raw else None)}
    return Graph(nodes, edges, meta, {"nodes": nodes_raw, "edges": edges_raw, "meta": meta})


def _ctx(graph: Graph, flags: dict) -> Ctx:
    return Ctx(graph=graph, artifacts=None, flags=dict(flags), targets=set(),
               targets_declared=False, agent_status={}, cls=None, outcome=None,
               role_status={})


# ── AC-1 + AC-2: skip-eligible completed uzel přežije staleness a nevrátí se do auto_skip ──
def test_ac1_skip_eligible_completed_not_stale_when_upstream_unran():
    """AC-1: architecture (skip_if TRUE) completed PASS, ale product NEběžel a uzel nemá
    version-stamp → staleness ho dřív vyhodila. Po opravě zůstává valid_completed."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"lightweight": True, "has_server": True})
    st = {"completed": ["architecture"], "outcomes": {"architecture": "PASS"},
          "frontier": [], "skipped": [], "flags": {"lightweight": True, "has_server": True}}
    state = RunState(st)
    state.ensure_result_keys()

    res = Frontier(g, ctx, state, {}).compute()
    # architecture (UŽ completed) se NESMÍ znovu objevit jako auto_skip kandidát (jádro smyčky).
    # feasibility legitimně smí být v auto_skip — ještě completed NENÍ.
    assert "architecture" not in res["auto_skip"], (
        f"skip-eligible completed uzel se vrátil do auto_skip (smyčka): {res['auto_skip']}"
    )
    # backend (consume contract z architecture) se NESMÍ stallnout — architecture drží PASS pro dataflow
    assert res["stall_diagnostics"] == [], f"neočekávaný stall: {res['stall_diagnostics']}"


def test_ac2_both_lightweight_nodes_drop_out_of_auto_skip_once_completed():
    """AC-2: feasibility i architecture completed PASS → auto_skip prázdné (idempotence)."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"lightweight": True, "has_server": True})
    st = {"completed": ["feasibility", "architecture"],
          "outcomes": {"feasibility": "PASS", "architecture": "PASS"},
          "frontier": [], "skipped": [], "flags": {"lightweight": True, "has_server": True}}
    state = RunState(st)
    state.ensure_result_keys()

    res = Frontier(g, ctx, state, {}).compute()
    assert res["auto_skip"] == []


# ── AC-3: simulace drive smyčky — konverguje, doběhne na další reálný uzel ────────────
def _drive_sim(graph: Graph, flags: dict, max_iter: int = 50, complete_workers: bool = False):
    """Mini-replika run.drive auto-advance smyčky (auto_skip + completion). Vrátí
    (počet_iterací, poslední_frontier_dict). Cyklus = dosažení max_iter.

    `complete_workers=True` zvěrohodňuje sim: drive po dispatchi worker uzlu dostane `done`
    (mark_completed PASS) → upstream se reálně uspokojí. Bez něj sim NIKDY nedokončí product,
    takže feasibility (dep=product) se po FIX A správně neauto-skipne (skip jen když vstupy
    dorazily). Default False zachová původní AC-3 (loop-konvergence sama o sobě)."""
    st = {"completed": [], "outcomes": {}, "frontier": [], "skipped": [],
          "flags": dict(flags), "active_node": graph.entry}
    state = RunState(st)
    state.ensure_result_keys()
    ctx = _ctx(graph, flags)
    last = None
    for i in range(max_iter):
        last = Frontier(graph, ctx, state, {}).compute()
        auto_skip = last["auto_skip"]
        if auto_skip:                       # přesně to, co dělá run.drive na auto_skip
            for nid in auto_skip:
                state.mark_completed(nid)
                state.set_outcome(nid, "PASS")
            continue                        # další iterace smyčky
        if complete_workers and last["ready"]:   # drive dispatchne+done worker → upstream uspokojen
            for r in last["ready"]:
                state.mark_completed(r["node"])
                state.set_outcome(r["node"], "PASS")
            continue
        return i + 1, last                  # ustálilo se → drive pokračuje jinou větví
    return max_iter, last                   # nekonvergovalo = smyčka


def test_ac3_lightweight_drive_does_not_loop_and_reaches_next_real_node():
    """AC-3: lehká dráha — drive smyčka NESMÍ cyklit; feasibility+architecture skončí
    completed PASS a běh stojí na DALŠÍM reálném uzlu (product → ready)."""
    g = _lightweight_graph()
    iters, res = _drive_sim(g, {"lightweight": True, "has_server": True})

    assert iters < 50, "drive smyčka nekonverguje (cyklus na auto-skip uzlech)"
    # po ustálení: další reálný uzel je product (entry, žádný upstream) — ready
    ready = [r["node"] for r in res["ready"]]
    assert "product" in ready, f"běh nedošel na další reálný uzel: ready={ready}"
    # feasibility i architecture musí být PASS pro dataflow (auto_skip prázdné = už hotové)
    assert res["auto_skip"] == []


def test_ac3_skip_nodes_persist_as_completed_pass():
    """AC-3 doplněk: po VĚROHODNÉ drive simulaci (product se reálně dokončí) jsou
    feasibility+architecture v completed s outcome PASS (NE ztracené, NE inflight) —
    tj. propsaly se trvale, jak slibuje design auto-skip. Po FIX A se auto-skip stane
    teprve POTÉ, co product (upstream) doběhl — proto věrohodný sim s complete_workers."""
    g = _lightweight_graph()
    st = {"completed": [], "outcomes": {}, "frontier": [], "skipped": [],
          "flags": {"lightweight": True, "has_server": True}, "active_node": g.entry}
    state = RunState(st)
    state.ensure_result_keys()
    ctx = _ctx(g, {"lightweight": True, "has_server": True})

    for _ in range(50):
        res = Frontier(g, ctx, state, {}).compute()
        if res["auto_skip"]:
            for nid in res["auto_skip"]:
                state.mark_completed(nid)
                state.set_outcome(nid, "PASS")
            continue
        if res["ready"]:                       # drive dispatchne+done worker (product)
            for r in res["ready"]:
                state.mark_completed(r["node"])
                state.set_outcome(r["node"], "PASS")
            continue
        break

    assert "feasibility" in state.completed and "architecture" in state.completed
    assert state.outcomes["feasibility"] == "PASS"
    assert state.outcomes["architecture"] == "PASS"
    assert "feasibility" not in state.inflight and "architecture" not in state.inflight


# ── FIX A: skip-protected producent nesmí udělat konzumenty ready PŘED svým upstream ──
def test_fix_a_skip_node_does_not_make_consumer_ready_before_its_own_upstream():
    """Regrese NÁLEZ A (2026-06-17, vlna project-create-wizard): skip-eligible architecture
    NESMÍ udělat backend (consume contract) dataflow-ready, dokud architecture nemá vlastní
    vstupy uspokojené (product → spec/acceptance). Červený-před: bez FIX A se architecture
    auto-skipla hned (skip_if TRUE) a backend leakl do ready, ač product neběžel."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"lightweight": True, "has_server": True})
    # Čistý start: nic neběželo (product NEhotový).
    st = {"completed": [], "outcomes": {}, "frontier": [], "skipped": [],
          "flags": {"lightweight": True, "has_server": True}, "active_node": g.entry}
    state = RunState(st)
    state.ensure_result_keys()

    res = Frontier(g, ctx, state, {}).compute()
    ready = [r["node"] for r in res["ready"]]
    # product (entry) je jediný legitimně ready; backend ani architecture NESMÍ leaknout.
    assert ready == ["product"], f"phantom-ready leak: {ready}"
    assert "architecture" not in res["auto_skip"], (
        f"architecture auto-skipnuta před product: {res['auto_skip']}")
    assert "backend" not in ready


def test_fix_a_skip_node_skips_only_after_upstream_completes():
    """FIX A pozitivní strana: jakmile product (+ jeho spec) doběhne, feasibility a pak
    architecture se SPRÁVNĚ auto-skipnou a teprve TEHDY backend zlegitimní jako ready.
    Skip = výstup uspokojen, ale jen v místě grafu, kam dataflow legitimně dorazil."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"lightweight": True, "has_server": True})
    # product hotový → feasibility (dep=product) teď smí auto-skip.
    st = {"completed": ["product"], "outcomes": {"product": "PASS"},
          "frontier": [], "skipped": [],
          "flags": {"lightweight": True, "has_server": True}, "active_node": "product"}
    state = RunState(st)
    state.ensure_result_keys()

    res1 = Frontier(g, ctx, state, {}).compute()
    assert "feasibility" in res1["auto_skip"], f"feasibility neskipla po product: {res1['auto_skip']}"
    state.mark_completed("feasibility"); state.set_outcome("feasibility", "PASS")

    res2 = Frontier(g, ctx, state, {}).compute()
    assert "architecture" in res2["auto_skip"], f"architecture neskipla po feasibility: {res2['auto_skip']}"
    state.mark_completed("architecture"); state.set_outcome("architecture", "PASS")

    res3 = Frontier(g, ctx, state, {}).compute()
    assert "backend" in [r["node"] for r in res3["ready"]], "backend nezlegitimněl po architecture skip"


# ── AC-4: kontrast — bez lightweight flagu se uzly NEskipují ──────────────────────────
def test_ac4_no_lightweight_no_auto_skip():
    """AC-4: bez flags.lightweight → skip_if FALSE → uzly se NEauto-skipují (běží normálně)."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"has_server": True})   # žádný lightweight
    st = {"completed": ["product"], "outcomes": {"product": "PASS"},
          "frontier": [], "skipped": [], "flags": {"has_server": True},
          "epoch": 1, "node_versions": {"product": 1}, "type_versions": {}}
    state = RunState(st)
    state.ensure_result_keys()

    res = Frontier(g, ctx, state, {}).compute()
    assert res["auto_skip"] == [], "feasibility/architecture se NEsmí skipovat bez lightweight"
    # feasibility je ready (product PASS), architecture čeká → normální dráha
    assert "feasibility" in [r["node"] for r in res["ready"]]


def test_ac4_unknown_lightweight_does_not_skip():
    """AC-4 doplněk: lightweight UNKNOWN (flag chybí) → fail-safe, NEskipuj (raději spustit)."""
    g = _lightweight_graph()
    ctx = _ctx(g, {"has_server": True})   # lightweight není v flags vůbec
    st = {"completed": [], "outcomes": {}, "frontier": [], "skipped": [],
          "flags": {"has_server": True}}
    state = RunState(st)
    state.ensure_result_keys()

    res = Frontier(g, ctx, state, {}).compute()
    assert res["auto_skip"] == []
