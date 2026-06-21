"""Regresní test — `run.py checkpoint`: engine-native snapshot mimo working tree, idempotentní.

Z backlog/agent-command-guardrails.md §6.1: engine sám checkpointuje current-run.md (+ ledger
HEAD pointer) do runtime cesty mimo working tree (.agentic/.checkpoint/, gitignored). Cíl:
poslední dobrý stav nezávislý na gitu, který agent (git stash/reset) nerozhodí.

Hermetické: AGENTIC_RUN_ROOT izoluje run_root → checkpoint_dir = tmp/.agentic/.checkpoint/.
NEsahá na reálný stav. Žádný git.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

import resilience  # noqa: E402

_RUN_PY = os.path.join(_CORE, "run.py")

_CURRENT = """\
# current-run.md

```yaml
run: r1
status: in_progress
active_node: work
completed:
- intake
```
"""


def _seed_current(tmp_path):
    (tmp_path / "current-run.md").write_text(_CURRENT, encoding="utf-8")


def _seed_ledger(tmp_path, run="r1", n=2):
    rd = tmp_path / "runs" / run
    rd.mkdir(parents=True)
    body = "".join(f"---\nrun: {run}\nnode: n{i}\noutcome: PASS\n" for i in range(n))
    (rd / "ledger.yaml").write_text(body, encoding="utf-8")


def _run(tmp_path, *args):
    env = dict(os.environ, AGENTIC_RUN_ROOT=str(tmp_path))
    return subprocess.run([sys.executable, _RUN_PY, *args],
                          capture_output=True, text=True, cwd=str(tmp_path), env=env)


def _cp_dir(tmp_path):
    return tmp_path / ".agentic" / ".checkpoint"


def test_checkpoint_writes_snapshot_outside_working_tree(tmp_path, monkeypatch):
    """Snapshot current-run.md + meta.yaml do .agentic/.checkpoint/ (mimo working tree)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    _seed_current(tmp_path)
    _seed_ledger(tmp_path, n=2)
    out = resilience.checkpoint()
    assert out is not None
    snap = _cp_dir(tmp_path) / "current-run.snapshot.md"
    meta = _cp_dir(tmp_path) / "meta.yaml"
    assert snap.is_file() and meta.is_file()
    # snapshot je doslovná kopie current-run.md
    assert snap.read_text(encoding="utf-8") == (tmp_path / "current-run.md").read_text(encoding="utf-8")
    # meta zná run + ledger HEAD pozici
    from common import yaml
    m = yaml.safe_load(meta.read_text(encoding="utf-8"))
    assert m["run"] == "r1"
    assert m["active_node"] == "work"
    assert m["ledger_entries"] == 2


def test_checkpoint_is_idempotent(tmp_path, monkeypatch):
    """Opakovaný checkpoint nad stejným stavem → snapshot byte-identický (přepíše posledním)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    _seed_current(tmp_path)
    _seed_ledger(tmp_path)
    resilience.checkpoint(quiet=True)
    first = (_cp_dir(tmp_path) / "current-run.snapshot.md").read_text(encoding="utf-8")
    resilience.checkpoint(quiet=True)
    second = (_cp_dir(tmp_path) / "current-run.snapshot.md").read_text(encoding="utf-8")
    assert first == second


def test_checkpoint_no_current_run_is_noop(tmp_path, monkeypatch):
    """Chybí current-run.md → None (fail-soft, nesmí shodit dispatch), žádný snapshot."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    assert resilience.checkpoint(quiet=True) is None
    assert not (_cp_dir(tmp_path) / "current-run.snapshot.md").exists()


def test_restore_recovers_corrupted_current_run(tmp_path, monkeypatch):
    """Po checkpointu: rozbij current-run.md → restore obnoví poslední dobrý stav."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    _seed_current(tmp_path)
    _seed_ledger(tmp_path)
    resilience.checkpoint(quiet=True)
    (tmp_path / "current-run.md").write_text("GARBAGE — agent rozhodil stav", encoding="utf-8")
    assert resilience.restore_checkpoint() is True
    assert "active_node: work" in (tmp_path / "current-run.md").read_text(encoding="utf-8")


def test_restore_without_snapshot_returns_false(tmp_path, monkeypatch):
    """Bez snapshotu restore vrátí False (volající padne na repair z ledgeru)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    assert resilience.restore_checkpoint() is False


def test_checkpoint_cli_subcommand(tmp_path):
    """run.py checkpoint přes subprocess (CLI kontrakt) → exit 0 + snapshot vznikne."""
    _seed_current(tmp_path)
    _seed_ledger(tmp_path)
    res = _run(tmp_path, "checkpoint")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert (_cp_dir(tmp_path) / "current-run.snapshot.md").is_file()


def test_checkpoint_cli_restore(tmp_path):
    """run.py checkpoint --restore obnoví stav přes CLI."""
    _seed_current(tmp_path)
    _seed_ledger(tmp_path)
    assert _run(tmp_path, "checkpoint").returncode == 0
    (tmp_path / "current-run.md").write_text("BROKEN", encoding="utf-8")
    res = _run(tmp_path, "checkpoint", "--restore")
    assert res.returncode == 0
    assert "active_node: work" in (tmp_path / "current-run.md").read_text(encoding="utf-8")
