"""Unit testy statewrite.py — engine zapisuje strojová fakta o uzavřené vlně do STATE.md.

Pokrývá (spec §Ověření): idempotence replay (2× → 1 záznam), FIFO N (N+1 → drží N),
marker in-place (okolní narativ bajt-přesně netknut), fail-soft (chybí STATE/marker →
neshodí), upsert pořadí, build_record fakta. I/O přes tmp STATE soubory v pytest tmp_path.
"""
import yaml
from statewrite import (
    END_MARKER,
    KEEP_N,
    START_MARKER,
    _count_return_loops,
    _count_return_loops_from_ledger,
    _parse_existing,
    _reached_terminal,
    backfill,
    build_record,
    build_record_from_ledger,
    record_closed_wave,
    upsert_record,
)

SAMPLE_STATE = """# proj — State

Živý stav projektu.

<!-- ENGINE:STATE START -->
<!-- komentář -->
```yaml
closed_waves: {}
```
<!-- ENGINE:STATE END -->

## Aktuální fokus

LIDSKÝ NARATIV — tenhle text engine NIKDY nesmí přepsat.
Druhý řádek příběhu.
"""


def _state(st_overrides=None):
    base = {
        "run": "w1", "status": "done", "wave_base": "abc123", "class": "feature",
        "completed": ["intake", "product", "done"], "last_outcome": "DONE",
        "counters": {"qa->web": 2, "spec-gate->product": 1},
        "flags": {"touches_db": True, "touches_server": False,
                  "touches_shared_ui": False, "has_ui": True},
    }
    base.update(st_overrides or {})
    return base


def _waves(text):
    """Vytáhni closed_waves mapu z bloku v textu."""
    import re
    m = re.search(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), text, re.S)
    assert m, "blok chybí"
    return _parse_existing(m.group(0))


# ── build_record: strojová fakta ──────────────────────────────────────────────
def test_build_record_machine_facts():
    rec = build_record(_state(), "w1")
    assert rec["status"] == "done"
    assert rec["wave_base"] == "abc123"
    assert rec["class"] == "feature"
    assert rec["nodes"] == 3
    assert rec["last_outcome"] == "DONE"
    assert rec["return_loops"] == 3          # 2 + 1
    assert rec["summary"] == "runs/w1/summary.md"
    assert rec["ledger"] == "runs/w1/ledger.yaml"
    assert rec["touches"] == {"touches_db": True, "touches_server": False,
                              "touches_shared_ui": False, "has_ui": True}
    assert "closed_at" in rec            # ISO timestamp přítomný


def test_build_record_no_human_prose():
    """Záznam NESMÍ nést lidskou větu — jen strojová fakta (žádné 'note'/'desc')."""
    rec = build_record(_state(), "w1")
    for forbidden in ("note", "desc", "summary_text", "narrative"):
        assert forbidden not in rec


# ── upsert: idempotence + FIFO + in-place ─────────────────────────────────────
def test_upsert_inserts_under_marker():
    out = upsert_record(SAMPLE_STATE, "w1", build_record(_state(), "w1"))
    waves = _waves(out)
    assert list(waves.keys()) == ["w1"]
    assert waves["w1"]["status"] == "done"


def test_upsert_idempotent_replay():
    """Replay téže vlny (2× done) → 1 záznam, ne duplikát (UPSERT dle klíče)."""
    out1 = upsert_record(SAMPLE_STATE, "w1", build_record(_state(), "w1"))
    rec2 = build_record(_state({"last_outcome": "ACK"}), "w1")
    out2 = upsert_record(out1, "w1", rec2)
    waves = _waves(out2)
    assert list(waves.keys()) == ["w1"]                 # pořád 1 klíč
    assert waves["w1"]["last_outcome"] == "ACK"         # přepsáno (latest-wins)


def test_upsert_fifo_keeps_n():
    """N+1 vln → blok drží posledních KEEP_N (nejstarší vypadne)."""
    text = SAMPLE_STATE
    for i in range(KEEP_N + 3):
        text = upsert_record(text, f"w{i}", build_record(_state(), f"w{i}"))
    waves = _waves(text)
    assert len(waves) == KEEP_N
    keys = list(waves.keys())
    assert keys[0] == f"w{3}"                            # první 3 vypadly
    assert keys[-1] == f"w{KEEP_N + 2}"                 # nejnovější poslední


def test_upsert_preserves_surrounding_text_byte_exact():
    """Lidský narativ mimo blok = bajt-přesně netknut (marker in-place)."""
    out = upsert_record(SAMPLE_STATE, "w1", build_record(_state(), "w1"))
    # vše PŘED START_MARKER beze změny
    pre = SAMPLE_STATE.split(START_MARKER)[0]
    assert out.startswith(pre)
    # vše ZA END_MARKER beze změny
    post = SAMPLE_STATE.split(END_MARKER)[1]
    assert out.endswith(post)
    assert "LIDSKÝ NARATIV — tenhle text engine NIKDY nesmí přepsat." in out
    assert "Druhý řádek příběhu." in out


def test_upsert_marker_missing_inserts_under_h1():
    """Chybí marker → engine vloží blok pod H1 (neselhává, fail-soft kontrakt)."""
    no_marker = "# proj — State\n\nNějaký text.\n\n## Fokus\nPříběh.\n"
    out = upsert_record(no_marker, "w1", build_record(_state(), "w1"))
    assert START_MARKER in out and END_MARKER in out
    assert out.startswith("# proj — State")
    assert "## Fokus\nPříběh." in out                   # původní text zachován
    waves = _waves(out)
    assert "w1" in waves


# ── record_closed_wave: I/O + fail-soft ───────────────────────────────────────
def test_record_writes_to_disk(tmp_path):
    sf = tmp_path / "STATE.md"
    sf.write_text(SAMPLE_STATE, encoding="utf-8")
    ok = record_closed_wave(run_id="w1", state_file=str(sf), run_state=_state())
    assert ok is True
    waves = _waves(sf.read_text(encoding="utf-8"))
    assert waves["w1"]["nodes"] == 3


def test_record_replay_on_disk_no_dup(tmp_path):
    sf = tmp_path / "STATE.md"
    sf.write_text(SAMPLE_STATE, encoding="utf-8")
    record_closed_wave(run_id="w1", state_file=str(sf), run_state=_state())
    record_closed_wave(run_id="w1", state_file=str(sf),
                       run_state=_state({"last_outcome": "ACK"}))
    waves = _waves(sf.read_text(encoding="utf-8"))
    assert list(waves.keys()) == ["w1"]
    assert waves["w1"]["last_outcome"] == "ACK"


def test_record_failsoft_missing_state(tmp_path, capsys):
    """Chybí STATE.md → WARN + False, NEvyhodí (terminál pokračuje)."""
    missing = tmp_path / "nope.md"
    ok = record_closed_wave(run_id="w1", state_file=str(missing), run_state=_state())
    assert ok is False
    assert "WARN" in capsys.readouterr().err


def test_record_failsoft_no_run_id(tmp_path, capsys):
    """Neznámý run-id → WARN + False, neselhává."""
    sf = tmp_path / "STATE.md"
    sf.write_text(SAMPLE_STATE, encoding="utf-8")
    ok = record_closed_wave(run_id=None, state_file=str(sf),
                            run_state=_state({"run": None}))
    assert ok is False
    assert "WARN" in capsys.readouterr().err


def test_record_failsoft_corrupt_block(tmp_path):
    """Poškozený yaml v bloku → engine ho přepíše čistým (neztratí terminál)."""
    bad = SAMPLE_STATE.replace("closed_waves: {}", "closed_waves: [: : broken")
    sf = tmp_path / "STATE.md"
    sf.write_text(bad, encoding="utf-8")
    ok = record_closed_wave(run_id="w1", state_file=str(sf), run_state=_state())
    assert ok is True
    waves = _waves(sf.read_text(encoding="utf-8"))
    assert "w1" in waves


def test_block_is_valid_yaml(tmp_path):
    """Vyrenderovaný blok je parsovatelný yaml (Watson ho čte strojově)."""
    sf = tmp_path / "STATE.md"
    sf.write_text(SAMPLE_STATE, encoding="utf-8")
    record_closed_wave(run_id="w1", state_file=str(sf), run_state=_state())
    import re
    text = sf.read_text(encoding="utf-8")
    m = re.search(r"```yaml\s*\n(.*?)\n```", text.split(START_MARKER)[1], re.S)
    data = yaml.safe_load(m.group(1))
    assert "closed_waves" in data and "w1" in data["closed_waves"]


# ── return_loops: PŘESNĚ z ledgeru (FAIL+returns_to), ne Σ counters ───────────
# Ledger fixture: 2 FAIL+returns_to (= 2 reálné smyčky) ALE counter resetnutý na 1.
# Σ counters dá 1 (dolní odhad); ledger dá pravdivé 2.
_LEDGER_TWO_LOOPS = [
    {"run": "wl", "node": "intake", "outcome": "PASS", "class": "feature",
     "flags": {"touches_db": False, "has_ui": True}},
    {"run": "wl", "node": "spec-gate", "outcome": "FAIL", "returns_to": "product"},
    {"run": "wl", "node": "product", "outcome": "PASS"},
    {"run": "wl", "node": "spec-gate", "outcome": "FAIL", "returns_to": "product"},
    {"run": "wl", "node": "product", "outcome": "PASS"},
    {"run": "wl", "node": "spec-gate", "outcome": "PASS"},
    {"run": "wl", "node": "l2-review", "outcome": "APPROVED"},
]


def _write_ledger(tmp_path, run_id, entries):
    rd = tmp_path / "runs" / run_id
    rd.mkdir(parents=True)
    (rd / "ledger.yaml").write_text(
        "\n---\n".join(yaml.safe_dump(e, sort_keys=False, allow_unicode=True) for e in entries),
        encoding="utf-8",
    )
    return rd


def test_count_return_loops_from_ledger_exact():
    """FAIL+returns_to záznamy = přesný počet smyček (2× spec-gate→product = 2)."""
    assert _count_return_loops_from_ledger(_LEDGER_TWO_LOOPS) == 2


def test_count_return_loops_ignores_non_fail():
    """PASS/FAIL bez returns_to se NEpočítá (jen FAIL s návratovou hranou = smyčka)."""
    entries = [
        {"node": "a", "outcome": "PASS"},
        {"node": "b", "outcome": "FAIL"},                       # bez returns_to → ne-loop
        {"node": "c", "outcome": "FAIL", "returns_to": "a"},    # loop
    ]
    assert _count_return_loops_from_ledger(entries) == 1


def test_live_return_loops_from_ledger_not_counters(tmp_path, monkeypatch):
    """Live build_record bere return_loops z LEDGERU (pravdivé 2), ne ze Σ counters (1)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    _write_ledger(tmp_path, "wl", _LEDGER_TWO_LOOPS)
    st = {"run": "wl", "status": "done", "completed": ["intake", "product", "spec-gate"],
          "last_outcome": "APPROVED", "counters": {"spec-gate->product": 1}, "flags": {}}
    assert _count_return_loops(st) == 2                          # ledger > counters
    assert build_record(st, "wl")["return_loops"] == 2


def test_live_return_loops_failsoft_to_counters(tmp_path, monkeypatch):
    """Chybí ledger → live return_loops padne zpět na Σ counters (fail-soft)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "runs").mkdir()                                  # žádný ledger pro 'wghost'
    st = {"run": "wghost", "counters": {"qa->web": 2, "spec-gate->product": 1}}
    assert _count_return_loops(st) == 3                          # 2 + 1 counters


# ── _reached_terminal: deterministická detekce „dojela na done" ───────────────
def test_reached_terminal_accepts():
    assert _reached_terminal([{"node": "done", "outcome": "DONE"}])
    assert _reached_terminal([{"node": "l2-review", "outcome": "APPROVED"}])
    assert _reached_terminal([{"node": "l2-review", "outcome": "ACK"}])
    assert _reached_terminal([{"node": "monitor", "outcome": "PASS"}])


def test_reached_terminal_rejects_non_terminal():
    """Planning ledger (feasibility) / DEFERRED (ui-system) NEdojely → ne-terminál."""
    assert not _reached_terminal([{"node": "feasibility", "outcome": "PASS"}])
    assert not _reached_terminal([{"node": "ui-system", "outcome": "PASS"}])
    assert not _reached_terminal([{"node": "l2-review", "outcome": "REJECTED"}])
    assert not _reached_terminal([])


# ── build_record_from_ledger: stejný tvar jako build_record, čteno z ledgeru ──
def test_build_record_from_ledger_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    _write_ledger(tmp_path, "wl", _LEDGER_TWO_LOOPS)
    rec = build_record_from_ledger("wl", _LEDGER_TWO_LOOPS)
    assert rec["status"] == "done"
    assert rec["class"] == "feature"
    assert rec["last_outcome"] == "APPROVED"
    assert rec["return_loops"] == 2
    assert rec["nodes"] == 4                                     # unikátní: intake/spec-gate/product/l2-review
    assert rec["touches"] == {"touches_db": False, "has_ui": True}
    assert rec["summary"] == "runs/wl/summary.md"
    assert rec["wave_base"] is None                             # historický ledger ho nenese
    for forbidden in ("note", "desc", "narrative"):            # žádná lidská věta
        assert forbidden not in rec


# ── backfill: fixture runs/ → blok naplněn, FIFO, idempotence, narativ netknut ─
def _make_terminal_ledger(i):
    return [
        {"run": f"bw{i}", "node": "intake", "outcome": "PASS", "class": "feature",
         "flags": {"has_ui": True}},
        {"run": f"bw{i}", "node": "l2-review", "outcome": "APPROVED"},
    ]


def test_backfill_populates_block(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    _write_ledger(tmp_path, "bw0", _make_terminal_ledger(0))
    _write_ledger(tmp_path, "bw1", _make_terminal_ledger(1))
    n = backfill()
    assert n == 2
    waves = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    assert set(waves) == {"bw0", "bw1"}
    assert waves["bw0"]["status"] == "done"


def test_backfill_skips_non_terminal(tmp_path, monkeypatch):
    """Vlna co nedojela na terminál (planning ledger) se NEbackfilluje."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    _write_ledger(tmp_path, "done1", _make_terminal_ledger(1))
    _write_ledger(tmp_path, "plan1",
                  [{"run": "plan1", "node": "feasibility", "outcome": "PASS", "class": "feature"}])
    backfill()
    waves = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    assert "done1" in waves and "plan1" not in waves


def test_backfill_fifo_keeps_n(tmp_path, monkeypatch):
    """Víc než KEEP_N terminálních vln → blok drží posledních KEEP_N (dle closed_at)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    import os
    import time
    for i in range(KEEP_N + 3):
        rd = _write_ledger(tmp_path, f"bw{i:02d}", _make_terminal_ledger(i))
        # rozliš mtime → deterministické pořadí closed_at (jinak by stejný mtime míchal FIFO)
        os.utime(rd / "ledger.yaml", (time.time() + i, time.time() + i))
    backfill()
    waves = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    assert len(waves) == KEEP_N
    assert "bw00" not in waves                                   # nejstarší vypadly
    assert f"bw{KEEP_N + 2:02d}" in waves                        # nejnovější drží


def test_backfill_idempotent(tmp_path, monkeypatch):
    """2× backfill = stejná množina klíčů (UPSERT dle wave-id, žádné duplikáty)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    _write_ledger(tmp_path, "bw0", _make_terminal_ledger(0))
    _write_ledger(tmp_path, "bw1", _make_terminal_ledger(1))
    backfill()
    first = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    backfill()
    second = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    assert list(first.keys()) == list(second.keys())
    assert first == second                                       # bajt-identický obsah faktů


def test_backfill_preserves_narrative_byte_exact(tmp_path, monkeypatch):
    """Lidský narativ pod markerem = bajt-přesně netknut (jen blok mezi markery se mění)."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "STATE.md").write_text(SAMPLE_STATE, encoding="utf-8")
    _write_ledger(tmp_path, "bw0", _make_terminal_ledger(0))
    backfill()
    out = (tmp_path / "STATE.md").read_text(encoding="utf-8")
    assert out.startswith(SAMPLE_STATE.split(START_MARKER)[0])
    assert out.endswith(SAMPLE_STATE.split(END_MARKER)[1])


def test_backfill_does_not_downgrade_wave_base(tmp_path, monkeypatch):
    """Backfill NEpřepíše existující (live) wave_base na null, když ho ledger nenese."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    # blok už nese live záznam s wave_base
    seeded = SAMPLE_STATE.replace(
        "closed_waves: {}",
        "closed_waves:\n  bw0:\n    status: done\n    wave_base: deadbeef\n    nodes: 9",
    )
    (tmp_path / "STATE.md").write_text(seeded, encoding="utf-8")
    _write_ledger(tmp_path, "bw0", _make_terminal_ledger(0))     # ledger BEZ wave_base
    backfill()
    waves = _waves((tmp_path / "STATE.md").read_text(encoding="utf-8"))
    assert waves["bw0"]["wave_base"] == "deadbeef"               # zachováno, ne null


def test_backfill_failsoft_missing_state(tmp_path, monkeypatch, capsys):
    """Chybí STATE.md → WARN + 0, neselhává."""
    monkeypatch.setenv("AGENTIC_RUN_ROOT", str(tmp_path))
    (tmp_path / "runs").mkdir()
    assert backfill(state_file=str(tmp_path / "nope.md")) == 0
    assert "WARN" in capsys.readouterr().err
