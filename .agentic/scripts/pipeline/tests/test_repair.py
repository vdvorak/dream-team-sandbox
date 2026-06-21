"""Regresní test — `run.py repair`: replay current-run.md z ledgeru, idempotentní.

Z backlog/agent-command-guardrails.md §6.2: repair povyšuje ruční „start + replay done"
na první-třídní engine příkaz. Ledger (append-only envelope) je zdroj pravdy → repair z něj
deterministicky obnoví stav přes STEJNOU result.advance_state logiku (žádné druhé pravidlo).

Hermetické: AGENTIC_RUN_ROOT + PIPELINE_GRAPH izolují stav i graf do tmp_path → NEsahá na
reálné current-run.md / runs/ / delivery.yaml. Žádný git.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

_RUN_PY = os.path.join(_CORE, "run.py")

_GRAPH = """\
meta: {entry: intake}
nodes:
  intake: {type: router}
  work:   {type: agent, agent: bob-backend, outputs: []}
  audit:  {type: agent, agent: joey-qa, outputs: []}
  done:   {type: terminal}
edges:
  - {from: intake, to: work,  kind: normal}
  - {from: work,   to: audit, kind: normal}
  - {from: audit,  to: done,  kind: normal}
"""
_ARTIFACTS = "artifacts: {}\n"


def _seed_graph(tmp_path):
    pdir = tmp_path / "pipeline"
    pdir.mkdir()
    (pdir / "delivery.yaml").write_text(_GRAPH, encoding="utf-8")
    (pdir / "artifacts.yaml").write_text(_ARTIFACTS, encoding="utf-8")
    return pdir / "delivery.yaml"


def _seed_ledger(tmp_path, run, docs):
    rd = tmp_path / "runs" / run
    rd.mkdir(parents=True)
    body = ""
    for d in docs:
        body += "---\n"
        for k, v in d.items():
            body += f"{k}: {v}\n"
    (rd / "ledger.yaml").write_text(body, encoding="utf-8")
    return rd / "ledger.yaml"


def _run(tmp_path, graph, *args):
    env = dict(os.environ, AGENTIC_RUN_ROOT=str(tmp_path), PIPELINE_GRAPH=str(graph))
    return subprocess.run([sys.executable, _RUN_PY, *args],
                          capture_output=True, text=True, cwd=str(tmp_path), env=env)


def _read_state(tmp_path):
    from common import read_state
    return read_state(str(tmp_path / "current-run.md"))[0]


def test_repair_rebuilds_from_ledger(tmp_path):
    """Replay 2 PASS envelope → current-run.md obnoven: completed, outcomes, active_node, in_progress."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [
        {"run": "r1", "node": "intake", "outcome": "PASS", "class": "improvement"},
        {"run": "r1", "node": "work", "agent": "bob-backend", "outcome": "PASS"},
    ])
    res = _run(tmp_path, graph, "repair", "r1")
    assert res.returncode == 0, f"repair selhal:\n{res.stdout}\n{res.stderr}"

    st = _read_state(tmp_path)
    assert st["run"] == "r1"
    assert st["completed"] == ["intake", "work"]
    assert st["outcomes"] == {"intake": "PASS", "work": "PASS"}
    assert st["active_node"] == "work"
    assert st["status"] == "in_progress"
    assert st["class"] == "improvement"


def test_repair_is_idempotent(tmp_path):
    """Dvojí repair nad stejným ledgerem → bajt-identický current-run.md (čistá funkce z ledgeru)."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [
        {"run": "r1", "node": "intake", "outcome": "PASS"},
        {"run": "r1", "node": "work", "outcome": "PASS"},
    ])
    assert _run(tmp_path, graph, "repair", "r1").returncode == 0
    first = (tmp_path / "current-run.md").read_text(encoding="utf-8")
    assert _run(tmp_path, graph, "repair", "r1").returncode == 0
    second = (tmp_path / "current-run.md").read_text(encoding="utf-8")
    assert first == second, "repair NENÍ idempotentní — opakování změnilo stav"


def test_repair_replays_fail_returns_to(tmp_path):
    """FAIL s returns_to → repair zopakuje re-flow: cíl un-completnut, counter bumpnut."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [
        {"run": "r1", "node": "intake", "outcome": "PASS"},
        {"run": "r1", "node": "work", "outcome": "PASS"},
        {"run": "r1", "node": "audit", "outcome": "FAIL", "returns_to": "work",
         "signature": "qa-broke"},
    ])
    assert _run(tmp_path, graph, "repair", "r1").returncode == 0
    st = _read_state(tmp_path)
    # audit FAIL→work un-completne work (re-flow); counter audit->work = 1
    assert "work" not in st["completed"], "re-flow měl un-completnout work"
    assert st["counters"].get("audit->work") == 1


def test_repair_dry_run_does_not_write(tmp_path):
    """--dry-run vypíše plán, ale current-run.md NEvznikne."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [{"run": "r1", "node": "intake", "outcome": "PASS"}])
    res = _run(tmp_path, graph, "repair", "r1", "--dry-run")
    assert res.returncode == 0
    assert "dry-run" in res.stdout
    assert not (tmp_path / "current-run.md").exists(), "dry-run NESMÍ zapsat stav"


def test_repair_run_id_from_current_run(tmp_path):
    """Bez argumentu repair vezme run-id z existujícího current-run.md."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [{"run": "r1", "node": "intake", "outcome": "PASS"}])
    (tmp_path / "current-run.md").write_text(
        "# x\n\n```yaml\nrun: r1\nstatus: in_progress\nactive_node: null\n```\n",
        encoding="utf-8")
    res = _run(tmp_path, graph, "repair")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert _read_state(tmp_path)["completed"] == ["intake"]


def test_repair_dry_run_without_run_id_does_not_mistake_flag(tmp_path):
    """BUG B: `repair --dry-run` (bez run-id) NESMÍ vzít '--dry-run' jako run-id.

    run-id se vezme z current-run.md, flag se rozpozná jako flag. Před fixem run.py main()
    bral rest[0] == '--dry-run' jako run-id → 'chybí ledger --dry-run' / exit 2."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [{"run": "r1", "node": "intake", "outcome": "PASS"}])
    (tmp_path / "current-run.md").write_text(
        "# x\n\n```yaml\nrun: r1\nstatus: in_progress\nactive_node: null\n```\n",
        encoding="utf-8")
    res = _run(tmp_path, graph, "repair", "--dry-run")
    assert res.returncode == 0, f"flag se mylně bere jako run-id:\n{res.stdout}\n{res.stderr}"
    assert "dry-run" in res.stdout
    assert "run=r1" in res.stdout, f"run-id se měl vzít z current-run.md:\n{res.stdout}"
    # dry-run nesmí přepsat stav (zůstává původní 'null' active_node, ne replayed)
    assert _read_state(tmp_path).get("completed") in (None, []), "dry-run NESMÍ zapsat stav"


def test_repair_dry_run_with_run_id_before_flag(tmp_path):
    """run-id PŘED flagem stále funguje (regrese ochrana fixu BUG B)."""
    graph = _seed_graph(tmp_path)
    _seed_ledger(tmp_path, "r1", [{"run": "r1", "node": "intake", "outcome": "PASS"}])
    res = _run(tmp_path, graph, "repair", "r1", "--dry-run")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "run=r1" in res.stdout and "dry-run" in res.stdout


def test_repair_missing_ledger_fails_cleanly(tmp_path):
    """Chybí ledger → exit 2, žádný stav vymyšlený z ničeho."""
    graph = _seed_graph(tmp_path)
    res = _run(tmp_path, graph, "repair", "ghost")
    assert res.returncode == 2
    assert "chybí ledger" in res.stderr


def test_repair_ignores_resolve_loop_audit_records(tmp_path):
    """Repair replayuje JEN done envelope; auditní resolve-loop záznam (bez node/outcome) ignoruje."""
    graph = _seed_graph(tmp_path)
    rd = tmp_path / "runs" / "r1"
    rd.mkdir(parents=True)
    (rd / "ledger.yaml").write_text(
        "---\nrun: r1\nnode: intake\noutcome: PASS\n"
        "---\nintervened: audit->work\nkind: resolve-loop\nprev_count: 3\nat: 2026-01-01\n"
        "---\nrun: r1\nnode: work\noutcome: PASS\n",
        encoding="utf-8")
    assert _run(tmp_path, graph, "repair", "r1").returncode == 0
    st = _read_state(tmp_path)
    assert st["completed"] == ["intake", "work"]   # audit záznam nepřidal žádný uzel
