"""test_touches_server_ui.py — flow-consistency-hardening (2026-06-17, finding B).

Feature-level prořezávací flagy `touches_server` (gate backend) a `touches_shared_ui`
(gate ui-system), zrcadlí `touches_db` (gate db-schema). Cíl: web-only vlna už nepotřebuje
ruční `run.sh skip` backend/ui-system — architecture emituje flag, frontier vrstvu prořeže.

Pokrytá rizika z nálezu:
  R1  lightweight (architecture skipnuta) → flag chybí → frontier default = capability →
      NEprořezávat naslepo (zachová dnešní chování / explicitní skip).
  R2  security se touches_* NIKDY nevypne (žádný gate nad security uzlem/joinem).
  R3  flagy gatují produkující uzel; inactive producent je z _active_deps vyfiltrován →
      web zůstane ready (zpětně kompatibilní, žádný nový povinný vstup).
  R4  matice: server / no-server (web-only) / lightweight (chybějící architecture).

Pouští se z .agentic root: `cd .agentic && pytest scripts/pipeline/tests`.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from graph import Graph, make_node, Edge      # noqa: E402
from runstate import RunState                 # noqa: E402
from frontier import Frontier, Ctx            # noqa: E402
from predicate import Predicate               # noqa: E402


# ── helpery (parita s test_touches_db_stall.py) ─────────────────────────────────
def make_graph(nodes_raw: dict, edges_raw: list, entry: str | None = None) -> Graph:
    nodes = {nid: make_node(nid, raw) for nid, raw in nodes_raw.items()}
    edges = [Edge(e) for e in edges_raw]
    meta = {"entry": entry or (list(nodes_raw.keys())[0] if nodes_raw else None)}
    return Graph(nodes, edges, meta, {"nodes": nodes_raw, "edges": edges_raw, "meta": meta})


def make_frontier(graph: Graph, state_dict: dict, flags=None) -> Frontier:
    ctx = Ctx(graph=graph, artifacts=None, flags=dict(flags or {}), targets={"web"},
              targets_declared=True, agent_status={}, cls=None, outcome=None, role_status={})
    ctx.graph = graph
    state = RunState(state_dict)
    state.ensure_result_keys()
    return Frontier(graph, ctx, state, {})


# ── graf: architecture → backend / ui-system / web → code-lint (zrcadlí delivery.yaml) ──
def _make_web_track_graph() -> Graph:
    """architecture → {backend, ui-system, web}; ui-system → web; {backend,web} → code-lint.
    Gating zrcadlí delivery.yaml: backend when has_server&&touches_server,
    ui-system when has_ui&&touches_shared_ui, web when targets.web&&has_ui."""
    nodes_raw = {
        "architecture": {"type": "agent", "agent": "ted-architect"},
        "backend":   {"type": "agent", "agent": "bob-backend",
                      "when": "project.has_server && touches_server"},
        "ui-system": {"type": "agent", "agent": "leonard-ui",
                      "when": "spec.has_ui && touches_shared_ui"},
        "web":       {"type": "agent", "agent": "peter-web",
                      "when": "project.targets.web && spec.has_ui"},
        "code-lint": {"type": "gate", "agent": "vitek-quality"},
    }
    edges_raw = [
        {"from": "architecture", "to": "backend",
         "when": "project.has_server && touches_server && !(project.has_db && touches_db)"},
        {"from": "architecture", "to": "ui-system", "when": "spec.has_ui && touches_shared_ui"},
        {"from": "architecture", "to": "web"},
        {"from": "ui-system",    "to": "web"},
        {"from": "backend",      "to": "code-lint", "when": "PASS"},
        {"from": "web",          "to": "code-lint", "when": "PASS"},
    ]
    return make_graph(nodes_raw, edges_raw, entry="architecture")


def _arch_done_state(flags: dict) -> dict:
    return {
        "completed": ["architecture"],
        "outcomes": {"architecture": "PASS"},
        "frontier": [],
        "skipped": [],
        "flags": flags,
        "epoch": 1,
        "node_versions": {"architecture": 1},
        "type_versions": {},
    }


def _active(result: dict) -> list[str]:
    return ([r["node"] for r in result["ready"]] + [r["node"] for r in result["waiting"]]
            + result["auto_skip"] + result["inflight"])


# ── R4: matice server / no-server (web-only) ────────────────────────────────────
class TestTouchesServerMatrix:

    def test_full_stack_wave_runs_backend(self):
        """server vlna: touches_server=true → backend i web aktivní."""
        flags = {"has_server": True, "has_ui": True, "has_db": False, "touches_server": True,
                 "touches_shared_ui": True, "touches_db": False}
        ft = make_frontier(_make_web_track_graph(), _arch_done_state(flags), flags=flags)
        active = _active(ft.compute())
        assert "backend" in active
        assert "web" in active or "ui-system" in active

    def test_web_only_wave_prunes_backend(self):
        """web-only vlna: touches_server=false → backend MIMO frontier; web ready bez ručního skip."""
        flags = {"has_server": True, "has_ui": True, "has_db": False, "touches_server": False,
                 "touches_shared_ui": True, "touches_db": False}
        result = make_frontier(_make_web_track_graph(), _arch_done_state(flags), flags=flags).compute()
        active = _active(result)
        assert "backend" not in active, f"backend se objevil při touches_server=false: {active}"
        # ui-system má touches_shared_ui=true → web na něj čeká (waiting), ne stall
        assert "web" in active, f"web zmizel: {active}"
        assert result["stall_diagnostics"] == [], f"neočekávaný stall: {result['stall_diagnostics']}"

    def test_web_only_no_shared_ui_reaches_web_directly(self):
        """web-only + lokální komponenta: touches_server=false ∧ touches_shared_ui=false →
        backend i ui-system MIMO; web je READY přímo z architecture (žádný nový povinný vstup, R3)."""
        flags = {"has_server": True, "has_ui": True, "has_db": False, "touches_server": False,
                 "touches_shared_ui": False, "touches_db": False}
        result = make_frontier(_make_web_track_graph(), _arch_done_state(flags), flags=flags).compute()
        ready = [r["node"] for r in result["ready"]]
        active = _active(result)
        assert "backend" not in active and "ui-system" not in active, f"vrstva neprořezána: {active}"
        assert "web" in ready, f"web není ready při prořezu backend+ui-system: ready={ready}"
        assert result["stall_diagnostics"] == [], f"neočekávaný stall: {result['stall_diagnostics']}"


# ── R1: lightweight / chybějící flag → frontier default = capability (NEprořezávat) ─
class TestTouchesDefaultSafe:

    def test_missing_touches_server_defaults_to_has_server(self):
        """R1: flag chybí (architecture skipnuta lightweight cestou) → ctx.flag spadne na has_server
        → backend BĚŽÍ (žádný naslepý skip). Mirror: chybí touches_db → has_db."""
        # ŽÁDNÝ touches_* — jako po lightweight skipu architecture; project capability ano (has_db=False)
        flags = {"has_server": True, "has_ui": True, "has_db": False}
        result = make_frontier(_make_web_track_graph(), _arch_done_state(flags), flags=flags).compute()
        active = _active(result)
        assert "backend" in active, (
            f"backend prořezán při CHYBĚJÍCÍM touches_server (default musí být has_server=true): {active}")

    def test_missing_touches_shared_ui_defaults_to_has_ui(self):
        """R1: chybí touches_shared_ui → default has_ui → ui-system běží (žádný naslepý skip)."""
        flags = {"has_server": True, "has_ui": True, "has_db": False}
        result = make_frontier(_make_web_track_graph(), _arch_done_state(flags), flags=flags).compute()
        active = _active(result)
        assert "ui-system" in active, f"ui-system prořezán při chybějícím touches_shared_ui: {active}"

    def test_ctx_flag_fallback_values(self):
        """Jednotka: Ctx.flag() fallback touches_server→has_server, touches_shared_ui→has_ui."""
        graph = make_graph({}, [])
        ctx = Ctx(graph=graph, artifacts=None, flags={"has_server": True, "has_ui": False},
                  targets=set(), targets_declared=False, agent_status={}, cls=None,
                  outcome=None, role_status={})
        assert ctx.flag("touches_server") is True
        assert ctx.flag("touches_shared_ui") is False
        # explicitní flag přebíjí default
        ctx.flags["touches_server"] = False
        assert ctx.flag("touches_server") is False


# ── R2: security se touches_* NIKDY nevypne ─────────────────────────────────────
class TestSecurityNeverPruned:

    def test_security_node_has_no_touches_gate(self):
        """R2 (statická invarianta nad reálným delivery.yaml): security uzel NEMÁ žádný
        touches_* predikát (ani when, ani v audit-join.requires gate). Vypínat security
        feature-flagem je zakázané."""
        import yaml
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pipeline", "delivery.yaml")
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        sec = data["nodes"]["security"]
        sec_when = str(sec.get("when", ""))
        assert "touches_" not in sec_when, f"security.when obsahuje touches_* gate: {sec_when!r}"
        # security je bezpodmínečně v audit-join.requires (gating joinu by ho taky obešel)
        assert "security" in data["nodes"]["audit-join"]["requires"]

    def test_security_active_even_when_layers_pruned(self):
        """R2 dynamicky: i když touches_server=false ∧ touches_shared_ui=false, security
        (bez when) zůstává aktivní, jakmile na něj dorazí dataflow (qa PASS)."""
        nodes_raw = {
            "qa":       {"type": "gate", "agent": "joey-qa"},
            "security": {"type": "gate", "agent": "heimdall-security"},
        }
        edges_raw = [{"from": "qa", "to": "security", "when": "PASS", "kind": "fan-out"}]
        graph = make_graph(nodes_raw, edges_raw, entry="qa")
        flags = {"has_server": True, "has_ui": True, "touches_server": False,
                 "touches_shared_ui": False, "touches_db": False}
        state = {"completed": ["qa"], "outcomes": {"qa": "PASS"}, "frontier": [],
                 "skipped": [], "flags": flags, "epoch": 1,
                 "node_versions": {"qa": 1}, "type_versions": {}}
        result = make_frontier(graph, state, flags=flags).compute()
        assert "security" in [r["node"] for r in result["ready"]], (
            f"security není ready přes prořezané vrstvy: ready={[r['node'] for r in result['ready']]}")


# ── predicate: touches_* jsou deterministické strukturální atomy (ne judgment) ──
class TestTouchesPredicateAtoms:

    @pytest.mark.parametrize("flag", ["touches_server", "touches_shared_ui"])
    def test_structural_flag_atom(self, flag):
        """touches_* je StructuralFlagAtom (deterministický), ne FreeTextAtom (judgment)."""
        from predicate import StructuralFlagAtom
        p = Predicate.of(flag)
        atoms = list(p.atoms())
        assert len(atoms) == 1
        assert isinstance(atoms[0], StructuralFlagAtom), f"{flag} není strukturální atom: {atoms}"

    def test_architecture_pass_requires_all_touches(self):
        """Pilíř A rozšíření: architecture PASS musí deklarovat touches_server i touches_shared_ui
        (bool), ne jen touches_db. Chybí → validace selže; kompletní rodina → projde."""
        from result import validate_envelope
        from vocab import Vocabulary
        graph = make_graph({"architecture": {"type": "agent", "agent": "ted-architect"}},
                           [], entry="architecture")
        vocab = Vocabulary({})

        # jen touches_db → selže (chybí touches_server)
        env = {"run": "r1", "node": "architecture", "outcome": "PASS",
               "flags": {"touches_db": True}}
        with pytest.raises(SystemExit):
            validate_envelope(env, graph, vocab)

        # kompletní rodina → projde
        env_ok = {"run": "r1", "node": "architecture", "outcome": "PASS",
                  "flags": {"touches_db": True, "touches_server": True, "touches_shared_ui": False}}
        run, node, outcome, _ = validate_envelope(env_ok, graph, vocab)
        assert node == "architecture" and outcome == "PASS"

        # ne-bool touches_shared_ui → selže
        env_bad = {"run": "r1", "node": "architecture", "outcome": "PASS",
                   "flags": {"touches_db": True, "touches_server": True, "touches_shared_ui": "no"}}
        with pytest.raises(SystemExit):
            validate_envelope(env_bad, graph, vocab)

    def test_known_in_vocabulary(self):
        """touches_* jsou ve vocabulary.flags → C14 je neoznačí jako neznámé."""
        import yaml
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pipeline", "vocabulary.yaml")
        with open(path, encoding="utf-8") as fh:
            vocab = yaml.safe_load(fh)
        assert "touches_server" in vocab["flags"]
        assert "touches_shared_ui" in vocab["flags"]
