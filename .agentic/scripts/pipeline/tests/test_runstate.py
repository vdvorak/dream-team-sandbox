"""Unit testy runstate.py — RunState mutátory + read pohledy. Obal je MUTABILNÍ nad `st`
dictem (úložiště) → tady ověřujeme sémantiku metod, ne serializaci (tu drží selftest)."""
from runstate import RunState

from graph import Graph, make_node, Edge
from frontier import Frontier, Ctx


# ── inicializace / ensure ───────────────────────────────────────────────────────
def test_fresh_result_defaults():
    st = RunState.fresh_result("r1")
    assert st["run"] == "r1" and st["status"] == "in_progress"
    assert st["completed"] == [] and st["outcomes"] == {} and st["graph"] == "delivery"


def test_ensure_result_keys():
    rs = RunState({})
    rs.ensure_result_keys()
    for k in ("completed", "outcomes", "frontier", "skipped", "flags", "findings",
              "return_payload", "model_overrides"):
        assert k in rs.st
    assert rs.st["epoch"] == 0
    assert rs.st["type_versions"] == {} and rs.st["node_versions"] == {}
    assert rs.st["awaiting_human"] == []


def test_ensure_drive_keys():
    rs = RunState({})
    rs.ensure_drive_keys()
    assert rs.st["frontier"] == [] and rs.st["completed"] == []
    assert rs.st["outcomes"] == {} and rs.st["return_payload"] == {} and rs.st["model_overrides"] == {}


def test_coerce_awaiting_human():
    rs = RunState({"awaiting_human": "gate1"})
    rs.coerce_awaiting_human()
    assert rs.st["awaiting_human"] == ["gate1"]            # skalár → list
    rs2 = RunState({"awaiting_human": None})
    rs2.coerce_awaiting_human()
    assert rs2.st["awaiting_human"] == []                  # None → []


# ── pending_delegations (delegate-dispatch #6b) ──────────────────────────────────
def test_runstate_pending_delegations_init():
    """AC-1: fresh state má [], coerce z None i scalar vrátí []."""
    st = RunState.fresh_result("r1")
    assert st["pending_delegations"] == []                 # fresh init
    rs = RunState({})
    rs.ensure_result_keys()
    assert rs.st["pending_delegations"] == []              # ensure_result_keys coerce
    rs_d = RunState({})
    rs_d.ensure_drive_keys()
    assert rs_d.st["pending_delegations"] == []            # ensure_drive_keys coerce
    rs2 = RunState({"pending_delegations": None})
    rs2.coerce_pending_delegations()
    assert rs2.st["pending_delegations"] == []             # None → []
    rs3 = RunState({"pending_delegations": "stale-scalar"})
    rs3.coerce_pending_delegations()
    assert rs3.st["pending_delegations"] == []             # scalar → []


def test_add_pending_delegation_set_semantics():
    """AC-2: add připojí intent; duplicit dle `gate` se nahradí (latest-wins, no-dup)."""
    rs = RunState({})
    rs.ensure_result_keys()
    rs.add_pending_delegation({"gate": "g1", "delegate_to": "leonard-ui",
                               "artifact": "a", "requested_at": "t1"})
    rs.add_pending_delegation({"gate": "g1", "delegate_to": "leonard-ui",
                               "artifact": "a", "requested_at": "t2"})   # dedup g1
    assert len(rs.st["pending_delegations"]) == 1
    assert rs.st["pending_delegations"][0]["requested_at"] == "t2"       # latest-wins
    rs.add_pending_delegation({"gate": "g2", "delegate_to": "bob",
                               "artifact": "b", "requested_at": "t3"})
    assert [d["gate"] for d in rs.st["pending_delegations"]] == ["g1", "g2"]  # pořadí drží
    assert rs.pending_delegations == rs.st["pending_delegations"]        # read property


# ── completion / verze ──────────────────────────────────────────────────────────
def test_mark_completed_idempotent():
    rs = RunState({"completed": []})
    rs.mark_completed("a")
    rs.mark_completed("a")
    assert rs.completed == ["a"]


def test_set_outcome():
    rs = RunState({"outcomes": {}})
    rs.set_outcome("a", "PASS")
    assert rs.outcomes == {"a": "PASS"}


def test_stamp_monotone_epoch():
    rs = RunState({})
    rs.ensure_result_keys()
    rs.stamp("a", ["code"])
    assert rs.st["epoch"] == 1 and rs.st["node_versions"]["a"] == 1 and rs.st["type_versions"]["code"] == 1
    rs.stamp("b", ["spec"])
    assert rs.st["epoch"] == 2 and rs.st["node_versions"]["b"] == 2   # monotónní napříč uzly


def test_clear_payload():
    rs = RunState({"return_payload": {"a": ["sig"]}})
    rs.clear_payload("a")
    assert "a" not in rs.st["return_payload"]


# ── re-flow (return) ────────────────────────────────────────────────────────────
def test_uncomplete_removes_everywhere():
    rs = RunState({"completed": ["a", "b"], "outcomes": {"a": "PASS", "b": "PASS"},
                   "frontier": ["a"], "awaiting_human": ["a"]})
    rs.uncomplete("a")
    assert "a" not in rs.st["completed"] and "a" not in rs.st["outcomes"]
    assert "a" not in rs.st["frontier"] and "a" not in rs.st["awaiting_human"]
    assert rs.st["completed"] == ["b"]                    # ostatní netknuté


def test_bump_counter():
    rs = RunState({})
    assert rs.bump_counter("qa", "backend") == ("qa->backend", 1)
    assert rs.bump_counter("qa", "backend") == ("qa->backend", 2)


def test_add_payload_dedup():
    rs = RunState({"return_payload": {}})
    rs.add_payload("backend", "sig1")
    rs.add_payload("backend", "sig1")                     # dedup
    rs.add_payload("backend", "sig2")
    assert rs.st["return_payload"]["backend"] == ["sig1", "sig2"]


def test_add_finding():
    rs = RunState({"findings": []})
    rs.add_finding("vitek", "advisory", None, "dup ctor")
    assert rs.st["findings"] == [
        {"node": "vitek", "severity": "advisory", "returns_to": None, "signature": "dup ctor"}]


# ── frontier / gates ────────────────────────────────────────────────────────────
def test_inflight_add_remove_dedup():
    rs = RunState({"frontier": [], "awaiting_human": []})
    rs.add_inflight("a")
    rs.add_inflight("a")                                  # dedup
    assert rs.st["frontier"] == ["a"]
    rs.remove_inflight("a")
    assert rs.st["frontier"] == []


def test_awaiting_add_remove_dedup():
    rs = RunState({"frontier": [], "awaiting_human": []})
    rs.add_awaiting("g")
    rs.add_awaiting("g")
    assert rs.st["awaiting_human"] == ["g"]
    rs.remove_awaiting("g")
    assert rs.st["awaiting_human"] == []


def test_clear_halt_if():
    rs = RunState({"halt_gate": "g"})
    rs.clear_halt_if("other")
    assert rs.st["halt_gate"] == "g"                      # jiný gate → netknuto
    rs.clear_halt_if("g")
    assert rs.st["halt_gate"] is None


# ── envelope merge ──────────────────────────────────────────────────────────────
def test_merge_flags_coerce():
    rs = RunState({"flags": {}})
    rs.merge_flags({"has_db": "true", "design_source": "author"})
    assert rs.st["flags"]["has_db"] is True               # bool-ish → bool
    assert rs.st["flags"]["design_source"] == "author"    # value-flag verbatim


def test_merge_models_lowercased():
    rs = RunState({"model_overrides": {}})
    rs.merge_models({"backend": "HAIKU"})
    assert rs.st["model_overrides"]["backend"] == "haiku"


# ── scalar pole + read ──────────────────────────────────────────────────────────
def test_scalar_properties():
    rs = RunState({})
    rs.status, rs.note, rs.active_node, rs.halt_gate = "blocked", "x", "a", "g"
    assert (rs.status, rs.note, rs.active_node, rs.halt_gate) == ("blocked", "x", "a", "g")


def test_read_roundtrip(tmp_path):
    p = tmp_path / "current-run.md"
    p.write_text("# run\n\n```yaml\nrun: r1\ncompleted:\n- a\nstatus: in_progress\n```\n",
                 encoding="utf-8")
    rs, txt, m = RunState.read(str(p))
    assert rs.st["run"] == "r1" and rs.completed == ["a"] and m is not None


def test_read_missing_file(tmp_path):
    rs, txt, m = RunState.read(str(tmp_path / "nope.md"))
    assert rs.st == {} and txt is None and m is None


# ── inflight ↔ valid_completed smíření: perzistentní úložiště se NEMUTUJE (finding #3) ──
def _two_node_graph() -> Graph:
    nodes = {nid: make_node(nid, {"type": "agent"}) for nid in ("producer", "consumer")}
    edges = [Edge({"from": "producer", "to": "consumer", "kind": "normal"})]
    meta = {"entry": "producer"}
    return Graph(nodes, edges, meta, {"nodes": {}, "edges": [], "meta": meta})


def _ctx_for(graph: Graph) -> Ctx:
    return Ctx(graph=graph, artifacts=None, flags={}, targets=set(), targets_declared=False,
               agent_status={}, cls=None, outcome=None, role_status={})


def test_compute_reconciles_inflight_without_mutating_store():
    """Finding #3: smíření inflight↔valid_completed je VÝPOČETNÍ (Frontier.compute), ne
    cleanup perzistovaného pole. Ghost (uzel současně v completed ne-stale i ve frontieru)
    z LIVE inflight vypadne, ale `state.st['frontier']` (úložiště orchestrátora) zůstane
    nedotčené — demotaci dělá až `done`. Tím je smíření idempotentní a reziduum nemožné."""
    graph = _two_node_graph()
    st = {"completed": ["producer"], "outcomes": {"producer": "PASS"},
          "frontier": ["producer"], "skipped": [], "flags": {},
          "epoch": 1, "node_versions": {"producer": 1}, "type_versions": {}}
    state = RunState(st)
    result = Frontier(graph, _ctx_for(graph), state, {}).compute()

    assert "producer" not in result["inflight"]          # živý inflight smířen (ghost ven)
    assert state.st["frontier"] == ["producer"]          # úložiště netknuté (done ho dorovná)
    assert state.inflight == ["producer"]                # read property čte syrový store


def test_pending_delegation_write_roundtrip_preserves_text(tmp_path):
    """AC-2: read → add_pending_delegation → write_state → read; intent perzistuje,
    okolní text zachován, serializace bajt-stabilní (idempotentní druhý dump)."""
    from common import dump_block, read_state, write_state

    p = tmp_path / "current-run.md"
    p.write_text(
        "# header\n\n```yaml\nrun: r1\nawaiting_human:\n- g1\nstatus: blocked\n```\n\n## note\nKEEP\n",
        encoding="utf-8",
    )
    rs, _txt, _m = RunState.read(str(p))
    rs.add_pending_delegation({"gate": "g1", "delegate_to": "x",
                               "artifact": "y", "requested_at": "t"})
    write_state(str(p), rs.st)
    raw = p.read_text(encoding="utf-8")
    assert "# header" in raw and "KEEP" in raw and "pending_delegations" in raw
    st2, _t2, _m2 = read_state(str(p))
    assert st2["pending_delegations"][0]["gate"] == "g1"
    # bajt-stabilita: dump zapsaného stavu == dump znovu načteného
    assert dump_block(st2) == dump_block(read_state(str(p))[0])
