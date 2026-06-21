"""Integrace: terminál `done` → engine zapíše STATE.md machine blok + summary.md (dogfood).

Ověřuje refaktor ledger.generate_summary (volatelný z terminálu, fail-soft) a run.on_terminal
hook dohromady — že po dojetí na terminál se machine blok reálně naplní a summary vznikne.
Izolace přes AGENTIC_RUN_ROOT (jako selftest) — žádný zápis do reálného repo stavu.
"""

import ledger
import run as runmod

SAMPLE_STATE = """# proj — State

<!-- ENGINE:STATE START -->
```yaml
closed_waves: {}
```
<!-- ENGINE:STATE END -->

## Aktuální fokus
příběh
"""

LEDGER_DOC = """---
run: wdog
node: intake
agent: vision-po
outcome: PASS
cost: {model: sonnet, input_tokens: 100, output_tokens: 50, credits: 0.5}
time: {seconds: 12}
---
run: wdog
node: done
outcome: DONE
cost: {model: sonnet, input_tokens: 0, output_tokens: 0, credits: 0}
time: {seconds: 0}
"""


def _state():
    return {"run": "wdog", "status": "done", "wave_base": "deadbeef",
            "class": "improvement", "completed": ["intake", "done"],
            "last_outcome": "DONE", "counters": {}, "flags": {"has_ui": True}}


# ── ledger.generate_summary — volatelný z terminálu + fail-soft ───────────────
def test_generate_summary_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    rd = tmp_path / "runs" / "wdog"
    rd.mkdir(parents=True)
    (rd / "ledger.yaml").write_text(LEDGER_DOC, encoding="utf-8")
    out = ledger.generate_summary("wdog", write=True)
    assert out is not None and "Run summary — wdog" in out
    assert (rd / "summary.md").is_file()


def test_generate_summary_failsoft_no_ledger(tmp_path, monkeypatch):
    """Chybí ledger → None, NEvyhodí (terminál nesmí spadnout kvůli summary)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    assert ledger.generate_summary("ghost", write=True) is None


# ── run.on_terminal — dogfood: terminál naplní machine blok + summary ─────────
def test_on_terminal_dogfood(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    rd = tmp_path / "runs" / "wdog"
    rd.mkdir(parents=True)
    (rd / "ledger.yaml").write_text(LEDGER_DOC, encoding="utf-8")

    from runstate import RunState
    runmod.on_terminal(RunState(_state()))

    # machine blok naplněn
    import statewrite
    state_text = (tmp_path / "STATE.md").read_text(encoding="utf-8")
    import re
    m = re.search(re.escape(statewrite.START_MARKER) + r".*?" + re.escape(statewrite.END_MARKER),
                  state_text, re.S)
    waves = statewrite._parse_existing(m.group(0))
    assert "wdog" in waves
    assert waves["wdog"]["status"] == "done"
    assert waves["wdog"]["summary"] == "runs/wdog/summary.md"
    # summary vygenerováno
    assert (rd / "summary.md").is_file()
    # lidský narativ netknut
    assert "## Aktuální fokus\npříběh" in state_text


def test_on_terminal_failsoft_missing_state(tmp_path, monkeypatch, capsys):
    """Chybí STATE.md i ledger → on_terminal NEvyhodí (terminál dojede)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    from runstate import RunState
    runmod.on_terminal(RunState(_state()))   # nesmí raise
    assert "WARN" in capsys.readouterr().err
