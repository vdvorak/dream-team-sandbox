"""Regresní test N3 — čistý loop-recovery povel `run.py resolve-loop <edge>`.

ROOT CAUSE (vlna #3/#4a): return-loop se 3× zopakoval → engine BLOCKED (circuit-breaker), ale
neměl ČISTÝ recovery — orchestrátor uvolňoval ručně re-emitem `done` cílového uzlu (PASS), což je
trik, ne API. Fix (N3): subcommand `resolve-loop <edge>`, který (1) vynuluje counter hrany,
(2) přepne status blocked→in_progress JEN když byl counter-blocked, (3) zapíše auditní intervenci
do ledgeru. KRITICKÉ: odmítne odblokování REJECTED-blocked běhu (constitution §8 tvrdý halt).

Testy jedou přes RunState (jednotka reset_counter) i přes run.py subprocess (CLI kontrakt +
ledger audit), hermeticky v tmp_path (NEsahá na reálné current-run.md / runs/).
"""

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from runstate import RunState  # noqa: E402

_RUN_PY = os.path.join(_CORE, "run.py")


# ── jednotka: RunState.reset_counter ─────────────────────────────────────────────
def test_reset_counter_zeroes_and_returns_prev():
    rs = RunState({"counters": {"spec-gate->product": 3}})
    prev = rs.reset_counter("spec-gate->product")
    assert prev == 3
    assert rs.st["counters"]["spec-gate->product"] == 0


def test_reset_counter_unknown_edge_returns_zero():
    rs = RunState({"counters": {}})
    assert rs.reset_counter("a->b") == 0
    assert "a->b" not in rs.st["counters"]   # neznámou hranu nezavádí


# ── CLI: resolve-loop přes run.py subprocess (hermetické tmp_path) ───────────────
def _seed_run(tmp_path, *, counters, status, note=None, run="t-run"):
    """Napiš tmp current-run.md s daným stavem; vrať cestu k souboru projektu (root = tmp_path)."""
    st_lines = [f"run: {run}", "graph: delivery", f"status: {status}", "active_node: null"]
    st_lines.append("counters:")
    for k, v in counters.items():
        st_lines.append(f"  {k}: {v}")
    if note is not None:
        st_lines.append(f"note: {note!r}")
    block = "\n".join(st_lines)
    p = tmp_path / "current-run.md"
    p.write_text(f"# current-run.md\n\n```yaml\n{block}\n```\n", encoding="utf-8")
    return p


def _resolve_loop(tmp_path, edge):
    """Spusť run.py resolve-loop <edge>. AGENTIC_RUN_ROOT=tmp_path izoluje stav (run_root je
    ukotven na umístění skriptu, NE cwd — bez env override by skript sahal na reálné current-run.md!)."""
    env = dict(os.environ, AGENTIC_RUN_ROOT=str(tmp_path))
    return subprocess.run([sys.executable, _RUN_PY, "resolve-loop", edge],
                          capture_output=True, text=True, cwd=str(tmp_path), env=env)


def _read_state(tmp_path):
    sys.path.insert(0, _CORE)
    from common import read_state
    return read_state(str(tmp_path / "current-run.md"))[0]


def test_resolve_loop_counter_blocked_unblocks(tmp_path):
    """3× loop → blocked → resolve-loop edge: counter=0, status=in_progress, audit záznam přítomen."""
    _seed_run(tmp_path, counters={"spec-gate->product": 3}, status="blocked",
              note="BLOCKER: spec-gate->product dosáhl 3× — eskaluj o roli výš (constitution)")
    res = _resolve_loop(tmp_path, "spec-gate->product")
    assert res.returncode == 0, f"resolve-loop selhal:\n{res.stdout}\n{res.stderr}"

    st = _read_state(tmp_path)
    assert st["counters"]["spec-gate->product"] == 0       # counter vynulován
    assert st["status"] == "in_progress"                   # odblokováno

    # audit záznam v ledgeru
    ledger = tmp_path / "runs" / "t-run" / "ledger.yaml"
    assert ledger.exists(), "ledger.yaml s auditní stopou nevznikl"
    txt = ledger.read_text(encoding="utf-8")
    assert "intervened: spec-gate->product" in txt
    assert "resolve-loop" in txt
    # finding stopa v current-run.md
    assert any(f.get("severity") == "intervention" for f in st.get("findings", []))


def test_resolve_loop_rejected_refuses(tmp_path):
    """REJECTED-blocked → resolve-loop ODMÍTNE (constitution §8 tvrdý halt). Stav netknutý."""
    _seed_run(tmp_path, counters={"spec-gate->product": 3}, status="blocked",
              note="product REJECTED — běh zastaven (constitution §8)")
    res = _resolve_loop(tmp_path, "spec-gate->product")
    assert res.returncode == 2, f"resolve-loop měl odmítnout REJECTED:\n{res.stdout}\n{res.stderr}"
    assert "REJECTED" in res.stderr

    st = _read_state(tmp_path)
    assert st["status"] == "blocked"                       # netknuté — pořád halt
    assert st["counters"]["spec-gate->product"] == 3       # counter netknutý


def test_resolve_loop_below_threshold_refuses(tmp_path):
    """Hrana, která nedosáhla prahu 3 (není counter-blocked) → ODMÍTNUTO (nic k odblokování)."""
    _seed_run(tmp_path, counters={"spec-gate->product": 1}, status="in_progress")
    res = _resolve_loop(tmp_path, "spec-gate->product")
    assert res.returncode == 2
    assert "není counter-blocked" in res.stderr
    st = _read_state(tmp_path)
    assert st["counters"]["spec-gate->product"] == 1       # netknuté


def test_resolve_loop_bad_edge_format(tmp_path):
    """Argument bez 'node->target' → chyba (formát hrany)."""
    _seed_run(tmp_path, counters={}, status="blocked", note="BLOCKER x")
    res = _resolve_loop(tmp_path, "not-an-edge")
    assert res.returncode == 2
    assert "není hrana" in res.stderr


def test_resolve_loop_missing_run_file(tmp_path):
    """Bez current-run.md → není co odblokovat (exit 2)."""
    res = _resolve_loop(tmp_path, "a->b")
    assert res.returncode == 2
    assert "chybí" in res.stderr


def test_resolve_loop_no_args_usage(tmp_path):
    env = dict(os.environ, AGENTIC_RUN_ROOT=str(tmp_path))
    res = subprocess.run([sys.executable, _RUN_PY, "resolve-loop"],
                         capture_output=True, text=True, cwd=str(tmp_path), env=env)
    assert res.returncode == 2
    assert "Usage" in res.stderr
