"""Testy pro framework-touches-db-stall (pilíř A + pilíř B).

AC-1: architecture envelope bez touches_db → validace selže; s touches_db → projde.
AC-3: stall kvůli inactive producentovi → stall_diagnostics jmenuje blocked+blocking+reason.
AC-4: ruční skip producenta → stall přetrvá, diagnostika reason='skipped'.
AC-5: normální souběh (inflight neprázdné) → stall_diagnostics prázdné.
"""
import sys
import os
import pytest

# core/ na sys.path přidává conftest.py — doplnit přímo pro explicitnost
_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from graph import Graph, make_node, Edge
from runstate import RunState
from frontier import Frontier, Ctx
from predicate import Predicate


# ── helpery ─────────────────────────────────────────────────────────────────────

def make_graph(nodes_raw: dict, edges_raw: list, entry: str | None = None) -> Graph:
    """Sestaví minimální Graph z raw diktů bez načítání souboru."""
    nodes = {nid: make_node(nid, raw) for nid, raw in nodes_raw.items()}
    edges = [Edge(e) for e in edges_raw]
    meta = {"entry": entry or (list(nodes_raw.keys())[0] if nodes_raw else None)}
    return Graph(nodes, edges, meta, {"nodes": nodes_raw, "edges": edges_raw, "meta": meta})


def make_ctx_simple(flags=None, role_status=None) -> Ctx:
    """Jednoduchý Ctx bez načítání project-config.md."""
    graph = make_graph({}, [])
    return Ctx(
        graph=graph,
        artifacts=None,
        flags=dict(flags or {}),
        targets=set(),
        targets_declared=False,
        agent_status={},
        cls=None,
        outcome=None,
        role_status=dict(role_status or {}),
    )


def make_frontier(graph: Graph, state_dict: dict, flags=None, role_status=None) -> Frontier:
    ctx = make_ctx_simple(flags=flags, role_status=role_status)
    ctx.graph = graph
    state = RunState(state_dict)
    state.ensure_result_keys()
    return Frontier(graph, ctx, state, {})


# ── Pilíř A: _validate_touches_db ───────────────────────────────────────────────

class TestValidateTouchesDb:
    """Testuje _validate_touches_db přes volání z validate_envelope."""

    def _make_graph_with_architecture(self):
        """Minimální Graf s uzlem 'architecture'."""
        nodes = {"architecture": {"type": "agent", "agent": "ted-architect"}}
        edges = []
        return make_graph(nodes, edges, entry="architecture")

    def test_ac1_missing_touches_db_fails(self):
        """AC-1: architecture PASS bez flags.touches_db → validace selže."""
        import yaml as _yaml
        from result import validate_envelope, fail
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})  # prázdný — nevaliduje severity/model

        env = {"run": "r1", "node": "architecture", "outcome": "PASS"}
        with pytest.raises(SystemExit) as exc:
            validate_envelope(env, graph, vocab)
        assert exc.value.code == 1

    def test_ac1_missing_touches_db_error_message(self, capsys):
        """AC-1: chybová zpráva obsahuje instructions na přidání flagu."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "PASS"}
        with pytest.raises(SystemExit):
            validate_envelope(env, graph, vocab)
        err = capsys.readouterr().err
        assert "flags.touches_db" in err
        assert "touches_db: true" in err or "touches_db: false" in err

    def test_ac1_with_touches_db_true_passes(self):
        """AC-1: architecture PASS s flags.touches_db=True → projde validací."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "PASS",
               "flags": {"touches_db": True, "touches_server": True,
                         "touches_shared_ui": True}}
        run, node, outcome, node_def = validate_envelope(env, graph, vocab)
        assert node == "architecture" and outcome == "PASS"

    def test_ac1_with_touches_db_false_passes(self):
        """AC-1: architecture PASS s flags.touches_db=False → projde validací."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "PASS",
               "flags": {"touches_db": False, "touches_server": False,
                         "touches_shared_ui": False}}
        run, node, outcome, node_def = validate_envelope(env, graph, vocab)
        assert node == "architecture" and outcome == "PASS"

    def test_ac1_fail_outcome_skips_validation(self):
        """AC-1: architecture FAIL bez touches_db → projde (FAIL nepostoupí do db-schema)."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "FAIL"}
        # nesmí selhat
        run, node, outcome, node_def = validate_envelope(env, graph, vocab)
        assert outcome == "FAIL"

    def test_non_architecture_node_skips_validation(self):
        """Jiný uzel (ne architecture) nepodléhá touches_db validaci."""
        from result import validate_envelope
        from vocab import Vocabulary

        nodes = {"backend": {"type": "agent", "agent": "bob-backend"}}
        graph = make_graph(nodes, [], entry="backend")
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "backend", "outcome": "PASS"}
        # backend nemusí mít touches_db
        run, node, outcome, _ = validate_envelope(env, graph, vocab)
        assert node == "backend"

    def test_touches_db_non_bool_fails(self, capsys):
        """flags.touches_db s ne-bool hodnotou → validace selže."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "PASS",
               "flags": {"touches_db": "yes"}}  # string, ne bool
        with pytest.raises(SystemExit) as exc:
            validate_envelope(env, graph, vocab)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "bool" in err

    def test_approved_outcome_requires_touches_db(self):
        """AC-1 rozšíření: architecture APPROVED bez touches_db → taky selže."""
        from result import validate_envelope
        from vocab import Vocabulary

        graph = self._make_graph_with_architecture()
        vocab = Vocabulary({})

        env = {"run": "r1", "node": "architecture", "outcome": "APPROVED"}
        with pytest.raises(SystemExit) as exc:
            validate_envelope(env, graph, vocab)
        assert exc.value.code == 1


# ── Pilíř B: stall_diagnostics ──────────────────────────────────────────────────

def _simple_two_node_graph(producer_raw: dict, consumer_raw: dict,
                            edge_when: str | None = None) -> Graph:
    """Graf: producer → consumer (forward hrana, volitelně podmíněná)."""
    nodes_raw = {
        "producer": producer_raw,
        "consumer": {**consumer_raw},
    }
    edge: dict = {"from": "producer", "to": "consumer", "kind": "normal"}
    if edge_when:
        edge["when"] = edge_when
    return make_graph(nodes_raw, [edge], entry="producer")


class TestStallDiagnostics:
    """Testuje frontier._stall_diagnostics a compute() → stall_diagnostics klíč."""

    def test_ac3_inactive_producer_stall(self):
        """AC-3: producer inactive (when predikát = false) → stall_diagnostics identifikuje příčinu."""
        # producer má when=has_db, ale flag=false → inactive
        graph = _simple_two_node_graph(
            {"type": "agent", "when": "has_db"},
            {"type": "agent"},
        )
        state_dict = {
            "completed": [],
            "outcomes": {},
            "frontier": [],   # nic inflight
            "skipped": [],
            "flags": {"has_db": False},
        }
        ft = make_frontier(graph, state_dict, flags={"has_db": False})
        result = ft.compute()

        # consumer čeká, producer inactive → stall
        diags = result["stall_diagnostics"]
        assert len(diags) == 1
        d = diags[0]
        assert d["blocked_node"] == "consumer"
        assert d["blocking_node"] == "producer"
        assert d["reason"] == "inactive"

    def test_ac4_skipped_producer_stall(self):
        """AC-4: producer ručně skipped → stall_diagnostics reason='skipped'."""
        graph = _simple_two_node_graph(
            {"type": "agent"},
            {"type": "agent"},
        )
        state_dict = {
            "completed": [],
            "outcomes": {},
            "frontier": [],
            "skipped": ["producer"],   # ruční skip
            "flags": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        diags = result["stall_diagnostics"]
        assert len(diags) == 1
        d = diags[0]
        assert d["blocked_node"] == "consumer"
        assert d["blocking_node"] == "producer"
        assert d["reason"] == "skipped"

    def test_ac5_inflight_no_false_positive(self):
        """AC-5: producer inflight (ještě běží) → žádný stall, stall_diagnostics prázdné."""
        graph = _simple_two_node_graph(
            {"type": "agent"},
            {"type": "agent"},
        )
        state_dict = {
            "completed": [],
            "outcomes": {},
            "frontier": ["producer"],   # producer inflight
            "skipped": [],
            "flags": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        # AC-5 guard: inflight neprázdné → diagnostika nesmí proběhnout
        assert result["stall_diagnostics"] == []

    def test_normal_flow_empty_stall_diagnostics(self):
        """Normální průchod (oba uzly čisté, producer ready) → stall_diagnostics == []."""
        graph = _simple_two_node_graph(
            {"type": "agent"},
            {"type": "agent"},
        )
        state_dict = {
            "completed": [],
            "outcomes": {},
            "frontier": [],
            "skipped": [],
            "flags": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        # producer je ready (entry), consumer waiting na producera → ne stall
        assert result["stall_diagnostics"] == []

    def test_completed_producer_no_stall(self):
        """Producer completed PASS → consumer ready, žádný stall."""
        graph = _simple_two_node_graph(
            {"type": "agent"},
            {"type": "agent"},
        )
        state_dict = {
            "completed": ["producer"],
            "outcomes": {"producer": "PASS"},
            "frontier": [],
            "skipped": [],
            "flags": {},
            "epoch": 1,
            "node_versions": {"producer": 1},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        # consumer by měl být ready (producer completed)
        ready_nodes = [r["node"] for r in result["ready"]]
        assert "consumer" in ready_nodes
        assert result["stall_diagnostics"] == []

    def test_bare_fail_producer_stall(self):
        """Producer completed s FAIL (bare, bez returns_to) → stall, reason='failed'.
        Hrana consumer→producer musí mít when: PASS, jinak FAIL producent nezabrání průchodu."""
        graph = _simple_two_node_graph(
            {"type": "agent"},
            {"type": "agent"},
            edge_when="PASS",   # reálné grafy mají podmíněné hrany
        )
        state_dict = {
            "completed": ["producer"],
            "outcomes": {"producer": "FAIL"},
            "frontier": [],
            "skipped": [],
            "flags": {},
            "epoch": 1,
            "node_versions": {"producer": 1},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        diags = result["stall_diagnostics"]
        assert len(diags) == 1
        d = diags[0]
        assert d["blocked_node"] == "consumer"
        assert d["blocking_node"] == "producer"
        assert d["reason"] == "failed"

    def test_stall_diagnostics_key_always_present(self):
        """stall_diagnostics klíč je vždy přítomný v compute() výstupu (additivní)."""
        graph = _simple_two_node_graph({"type": "agent"}, {"type": "agent"})
        state_dict = {"completed": [], "outcomes": {}, "frontier": [], "skipped": [], "flags": {}}
        ft = make_frontier(graph, state_dict)
        result = ft.compute()
        assert "stall_diagnostics" in result


# ── AC-2: touches_db=false odřízne db-schema z frontieru ────────────────────
#
# Jádro opravovaného bugu: když architecture emituje touches_db=false, db-schema
# uzel má when="project.has_db && touches_db" → inactive → nesmí se zařadit do
# ready/waiting. Backend (when="project.has_server && !(project.has_db && touches_db)")
# jde přímo (nezávisí na db-schema), takže se neblokuje.
#
# Graf zrcadlí delivery.yaml hrany:
#   architecture → db-schema (when: project.has_db && touches_db)
#   architecture → backend   (when: project.has_server && !(project.has_db && touches_db))
#   db-schema   → backend    (when: project.has_server)


def _make_arch_dbschema_backend_graph() -> Graph:
    """Minimální trojuzelový graf: architecture → db-schema + backend."""
    nodes_raw = {
        "architecture": {"type": "agent", "agent": "ted-architect"},
        "db-schema":    {"type": "agent", "agent": "chandler-db",
                         "when": "project.has_db && touches_db"},
        "backend":      {"type": "agent", "agent": "bob-backend"},
    }
    edges_raw = [
        {"from": "architecture", "to": "db-schema",
         "kind": "normal", "when": "project.has_db && touches_db"},
        {"from": "architecture", "to": "backend",
         "kind": "normal", "when": "project.has_server && !(project.has_db && touches_db)"},
        {"from": "db-schema",   "to": "backend",
         "kind": "normal", "when": "project.has_server"},
    ]
    return make_graph(nodes_raw, edges_raw, entry="architecture")


class TestAc2TouchesDbFalse:
    """AC-2: touches_db=false odřízne db-schema z frontieru; backend se neblokuje."""

    def test_ac2_touches_db_false_db_schema_not_in_frontier(self):
        """AC-2 hlavní: architecture PASS + touches_db=false + has_db=true
        → db-schema není ready ani waiting; backend je ready (nezávisí na db-schema)."""
        graph = _make_arch_dbschema_backend_graph()
        # architecture dokončena s touches_db=false
        state_dict = {
            "completed": ["architecture"],
            "outcomes": {"architecture": "PASS"},
            "frontier": [],
            "skipped": [],
            "flags": {
                "has_db": True,
                "has_server": True,
                "touches_db": False,   # klíčový flag emitovaný architecture
            },
            "epoch": 1,
            "node_versions": {"architecture": 1},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict,
                           flags={"has_db": True, "has_server": True, "touches_db": False})
        result = ft.compute()

        ready_nodes   = [r["node"] for r in result["ready"]]
        waiting_nodes = [r["node"] for r in result["waiting"]]
        all_active    = ready_nodes + waiting_nodes + result["auto_skip"] + result["inflight"]

        # db-schema musí být úplně mimo (inactive kvůli when predikátu)
        assert "db-schema" not in all_active, (
            f"db-schema se objevil ve frontieru, ačkoli touches_db=false: ready={ready_nodes}, "
            f"waiting={waiting_nodes}"
        )
        # backend musí být ready (dostane se sem přes přímou hranu architecture→backend)
        assert "backend" in ready_nodes, (
            f"backend není ready, ačkoli touches_db=false (nemá čekat na db-schema): "
            f"ready={ready_nodes}, waiting={waiting_nodes}"
        )
        # žádný stall
        assert result["stall_diagnostics"] == [], (
            f"neočekávaný stall při touches_db=false: {result['stall_diagnostics']}"
        )

    def test_ac2_touches_db_true_db_schema_in_frontier(self):
        """AC-2 kontrast: touches_db=true → db-schema je ready (architecture PASS); backend čeká."""
        graph = _make_arch_dbschema_backend_graph()
        state_dict = {
            "completed": ["architecture"],
            "outcomes": {"architecture": "PASS"},
            "frontier": [],
            "skipped": [],
            "flags": {
                "has_db": True,
                "has_server": True,
                "touches_db": True,
            },
            "epoch": 1,
            "node_versions": {"architecture": 1},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict,
                           flags={"has_db": True, "has_server": True, "touches_db": True})
        result = ft.compute()

        ready_nodes   = [r["node"] for r in result["ready"]]
        waiting_nodes = [r["node"] for r in result["waiting"]]

        # db-schema musí být ready (touches_db=true, has_db=true)
        assert "db-schema" in ready_nodes, (
            f"db-schema není ready při touches_db=true: ready={ready_nodes}"
        )
        # backend musí čekat na db-schema
        assert "backend" in waiting_nodes, (
            f"backend není waiting při touches_db=true: waiting={waiting_nodes}"
        )
        # žádný stall (db-schema je v ready, backend čeká legitimně)
        assert result["stall_diagnostics"] == []

    def test_ac2_stall_when_db_schema_skipped_and_touches_db_true(self):
        """AC-2 + AC-4: touches_db=true ale db-schema ručně skipped → backend se
        neblokuje na db-schema výstup (stall diagnostika to pojmenuje)."""
        graph = _make_arch_dbschema_backend_graph()
        state_dict = {
            "completed": ["architecture"],
            "outcomes": {"architecture": "PASS"},
            "frontier": [],
            "skipped": ["db-schema"],   # ruční skip produkujícího uzlu
            "flags": {
                "has_db": True,
                "has_server": True,
                "touches_db": True,
            },
            "epoch": 1,
            "node_versions": {"architecture": 1},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict,
                           flags={"has_db": True, "has_server": True, "touches_db": True})
        result = ft.compute()

        # backend čeká na výstup db-schema (který byl skipped → data nikdy nevzniknou)
        # → stall diagnostika to musí pojmenovat
        diags = result["stall_diagnostics"]
        assert len(diags) >= 1, "očekávaná stall diagnostika pro backend→db-schema chybí"
        reasons = {(d["blocked_node"], d["blocking_node"], d["reason"]) for d in diags}
        assert ("backend", "db-schema", "skipped") in reasons, (
            f"stall diagnostika neidentifikuje skipped db-schema jako příčinu blokace backendu: {diags}"
        )


# ── Framework finding #3: inflight ↔ valid_completed smíření (ghost reaper) ──────
#
# Kořenová příčina: perzistovaný `frontier:` (= state.inflight echo) se rozejde s živě
# spočítaným valid_completed. Uzel se promuje do inflight přes drive (add_inflight) a jediná
# cesta ven je `done <uzel>`. Když ale uzel mezitím ZPLATNÍ (přejde do valid_completed —
# např. po opravě grafu přestane být stale), echo ho NIKDY nedemotuje → ghost přežije,
# bucket-loop ho slepě přeskakuje a terminal_reached čeká na prázdný inflight → vlna nezavře.
#
# Oprava (Frontier.compute): inflight = set(state.inflight) - completed_set při KAŽDÉM
# recompute. Uzel současně v inflight A valid_completed = kontradikce → reality vyhrává.
# Reziduum je nemožné z konstrukce (smíření, ne jednorázový cleanup).


class TestInflightCompletedReconciliation:
    """Ghost reaper: uzel v inflight, který živě zplatnil (valid_completed) → vypadne sám."""

    def test_ghost_inflight_dropped_when_valid_completed(self):
        """Hlavní AC: uzel je SOUČASNĚ v completed (ne-stale) A v perzistovaném frontieru →
        compute().inflight ho NESMÍ obsahovat (smířeno proti valid_completed)."""
        graph = _simple_two_node_graph({"type": "agent"}, {"type": "agent"})
        state_dict = {
            "completed": ["producer"],
            "outcomes": {"producer": "PASS"},
            "frontier": ["producer"],   # ghost: echo zůstalo po promoci, uzel mezitím zplatnil
            "skipped": [],
            "flags": {},
            "epoch": 1,
            "node_versions": {"producer": 1},   # ne-stale → patří do valid_completed
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        assert "producer" not in result["inflight"], (
            f"ghost: producer je completed (ne-stale) i v inflight, smíření ho nevyřadilo: "
            f"{result['inflight']}"
        )
        # downstream se odblokuje: consumer ready (producer je legitimně completed)
        assert "consumer" in [r["node"] for r in result["ready"]]

    def test_legitimate_inflight_survives(self):
        """Kontrast: uzel v inflight, který NENÍ valid_completed (běží, čeká na done) →
        smíření ho NESMÍ vyhodit (jinak by se ztratil rozdělaný uzel)."""
        graph = _simple_two_node_graph({"type": "agent"}, {"type": "agent"})
        state_dict = {
            "completed": [],
            "outcomes": {},
            "frontier": ["producer"],   # producer dispatchnut, ještě neběhl done
            "skipped": [],
            "flags": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        assert result["inflight"] == ["producer"], (
            f"legitimní inflight uzel (není completed) zmizel ze smíření: {result['inflight']}"
        )
        # AC-5 parita: inflight neprázdné → žádná stall diagnostika
        assert result["stall_diagnostics"] == []

    def test_mixed_ghost_and_legit_inflight(self):
        """Smíšený případ (zrcadlí reálný běh): jeden inflight uzel zplatnil (ghost),
        druhý ještě běží (legit). Smíření vyřadí jen ghost, legit přežije."""
        # ux-design = ghost (completed, ne-stale), qa = legit (dispatchnut, nehotov)
        nodes_raw = {
            "spec": {"type": "agent"},
            "ux-design": {"type": "agent"},
            "qa": {"type": "agent"},
        }
        edges_raw = [
            {"from": "spec", "to": "ux-design", "kind": "normal"},
            {"from": "ux-design", "to": "qa", "kind": "normal"},
        ]
        graph = make_graph(nodes_raw, edges_raw, entry="spec")
        state_dict = {
            "completed": ["spec", "ux-design"],
            "outcomes": {"spec": "PASS", "ux-design": "PASS"},
            "frontier": ["ux-design", "qa"],   # ux-design ghost, qa legit inflight
            "skipped": [],
            "flags": {},
            "epoch": 2,
            "node_versions": {"spec": 1, "ux-design": 2},  # ux-design ne-stale
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        assert "ux-design" not in result["inflight"], "ghost ux-design nebyl smířen ven"
        assert "qa" in result["inflight"], "legit qa nesmí ze smíření zmizet"

    def test_ghost_unblocks_terminal_reached(self):
        """Kořenový symptom: ghost v inflight blokoval terminal_reached (čeká na prázdný
        inflight). Po smíření, když je vše hotové až po terminal, terminal_reached==True."""
        nodes_raw = {
            "work": {"type": "agent"},
            "done": {"type": "terminal"},
        }
        edges_raw = [{"from": "work", "to": "done", "kind": "normal"}]
        graph = make_graph(nodes_raw, edges_raw, entry="work")
        state_dict = {
            "completed": ["work", "done"],
            "outcomes": {"work": "PASS", "done": "DONE"},
            "frontier": ["work"],   # ghost: work zplatnil, ale echo zůstalo
            "skipped": [],
            "flags": {},
            "epoch": 2,
            "node_versions": {"work": 1, "done": 2},
            "type_versions": {},
        }
        ft = make_frontier(graph, state_dict)
        result = ft.compute()

        assert result["inflight"] == [], f"ghost work blokuje inflight: {result['inflight']}"
        assert result["terminal_reached"] is True, (
            "terminal nedosažen — ghost v inflight blokoval uzávěr i po smíření"
        )
