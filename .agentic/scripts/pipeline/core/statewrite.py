#!/usr/bin/env python3
"""statewrite.py — engine zapisuje STROJOVÁ fakta o uzavřené vlně do STATE.md (fail-soft).

Když vlna dojede na terminál `done` (run.py drive() terminals větev), STATE.md
nesmí zastarat: engine sám připíše strojová fakta (wave-id, closed_at, status,
wave_base, class, touches_* flagy, počet uzlů, last_outcome, return-loopy, odkazy
na summary/ledger). ŽÁDNÁ lidská věta — jen odkaz na runs/<wave>/summary.md; prózu
píše člověk pod markerem a engine se jí NIKDY nedotkne.

Marker-delimitovaná sekce <!-- ENGINE:STATE START --> … <!-- ENGINE:STATE END -->
hned pod H1; engine ji přepisuje IN-PLACE (atomický tmp + os.replace). Blok drží
mapu wave-id → fakta: UPSERT (replay téže vlny = přepis klíče, ne duplikát) +
FIFO posledních KEEP_N vln. Plná historie zůstává v runs/ + gitu.

FAIL-SOFT (constitution-style, vzor git_head()): chybí STATE.md / I/O chyba →
WARN a vrať False, NIKDY neshazuj terminál. Marker když chybí → vlož pod H1.

CLI (dev/diagnostika):  python3 statewrite.py [--state-file STATE.md] [--run-id …]
CLI (backfill):         python3 statewrite.py backfill [--state-file STATE.md] [--dry-run]
"""
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import state_only, yaml

# Posledních N uzavřených vln v bloku (FIFO); starší vypadnou (historie v runs/ + git).
# Jediná konstanta — nehardcodovat napříč moduly (spec §FIFO).
KEEP_N = 10

START_MARKER = "<!-- ENGINE:STATE START -->"
END_MARKER = "<!-- ENGINE:STATE END -->"
# Region mezi markery (včetně markerů samotných) — replace in-place; okolní text netknut.
_BLOCK_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.S
)
# Touches-rodina flagů, které se do faktu propisují (architecture je zdroj pravdy).
_TOUCHES = ("touches_db", "touches_server", "touches_shared_ui", "has_ui")


def state_file_path() -> str:
    """Kanonická cesta k STATE.md (kořen projektu, cwd-nezávislá — jako run_file_path)."""
    return os.path.join(common.run_root(), "STATE.md")


def _read_ledger_entries(run_id: str) -> list:
    """Přečti záznamy ledgeru runs/<run>/ledger.yaml (multi-doc yaml). Chybí/poškozený → [].
    Tolerantní (fail-soft): ledger je jen zdroj přesnějšího return_loops; bez něj se padne
    zpět na counters. NIKDY nevyhazuje (terminál se nesmí shodit)."""
    ledger_f = os.path.join(common.runs_dir(run_id), "ledger.yaml")
    if not os.path.isfile(ledger_f):
        return []
    try:
        return [e for e in yaml.safe_load_all(open(ledger_f, encoding="utf-8")) if e]
    except (OSError, yaml.YAMLError):
        return []


def _count_return_loops_from_ledger(entries: list) -> int:
    """Přesný počet return-loopů z ledgeru = Σ záznamů FAIL s `returns_to` (stejný princip
    jako ledger.py `loops`: každá FAIL+returns_to dvojice = jedna re-flow smyčka hrany).

    Pravdivější než Σ counters: counter drží AKTUÁLNÍ stav hrany (resolve-loop ho nuluje),
    takže Σ counters je jen dolní odhad. Ledger je append-only historie → spočítá VŠECHNY
    smyčky, co reálně proběhly, bez ohledu na pozdější reset counteru."""
    total = 0
    for e in entries:
        if e.get("outcome") == "FAIL" and e.get("returns_to"):
            total += 1
    return total


def _count_return_loops(st: dict) -> int:
    """return_loops pro live zápis: PŘESNĚ z ledgeru (FAIL+returns_to), stejný zdroj jako
    backfill (determinismová konzistence — Σ counters byl jen dolní odhad). Chybí-li ledger
    (fail-soft), padni zpět na Σ counters z current-run.md."""
    run_id = st.get("run")
    if run_id:
        entries = _read_ledger_entries(run_id)
        if entries:
            return _count_return_loops_from_ledger(entries)
    counters = st.get("counters") or {}
    total = 0
    for v in counters.values():
        try:
            total += int(v)
        except (TypeError, ValueError):
            continue
    return total


def build_record(st: dict, run_id: str) -> dict:
    """Strojová fakta o uzavřené vlně — vše odvoditelné z current-run.md stavu (+ ledger
    pro přesný return_loops). ŽÁDNÁ lidská věta. Odkazy relativní (kořen projektu) → přenositelné."""
    flags = st.get("flags") or {}
    rec: dict = {
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "status": st.get("status"),
        "wave_base": st.get("wave_base"),
        "class": st.get("class"),
        "nodes": len(st.get("completed") or []),
        "last_outcome": st.get("last_outcome"),
        "return_loops": _count_return_loops(st),
        "summary": f"runs/{run_id}/summary.md",
        "ledger": f"runs/{run_id}/ledger.yaml",
    }
    touches = {f: common.coerce_flag(flags[f]) for f in _TOUCHES if f in flags}
    if touches:
        rec["touches"] = touches
    return rec


def _parse_existing(block_body: str) -> dict:
    """Vytáhni existující mapu wave-id → fakta z těla bloku (yaml). Nevalidní/prázdné → {}.
    Tolerantní: poškozený blok engine přepíše čistým (fail-soft, neztratí terminál)."""
    m = re.search(r"```yaml\s*\n(.*?)\n```", block_body, re.S)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    waves = data.get("closed_waves") if isinstance(data, dict) else None
    return waves if isinstance(waves, dict) else {}


def _render_block(waves: dict) -> str:
    """Vyrenderuj marker blok z mapy wave-id → fakta. Pořadí = insertion (FIFO)."""
    payload = {"closed_waves": waves}
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    return (
        f"{START_MARKER}\n"
        f"<!-- Strojově psané enginem na terminálu `done` (statewrite.py) — NEEDITUJ ručně.\n"
        f"     Uzavřené vlny = FAKTA o tom, co je hotové; lidský narativ pod markerem je pro PŘÍBĚH. -->\n"
        f"```yaml\n{body}```\n"
        f"{END_MARKER}"
    )


def upsert_record(state_text: str, run_id: str, record: dict) -> str:
    """Vrať nový text STATE.md s UPSERT záznamu do ENGINE:STATE bloku (+ FIFO KEEP_N).

    - Blok existuje → přečti mapu, UPSERT klíč run_id (replay = přepis, ne duplikát),
      ořízni na posledních KEEP_N, nahraď blok IN-PLACE (okolní text bajt-přesně netknut).
    - Blok chybí → vlož čerstvý hned pod H1 (jako write_state vloží stavový blok).
    - H1 chybí → vlož na začátek souboru.
    """
    m = _BLOCK_RE.search(state_text)
    if m:
        waves = _parse_existing(m.group(0))
    else:
        waves = {}

    # UPSERT: existující klíč přepiš in-place (drží pozici → stabilní pořadí pro replay);
    # nový klíč připoj na konec (nejnovější = poslední).
    if run_id in waves:
        waves[run_id] = record
    else:
        waves[run_id] = record
    # FIFO: drž posledních KEEP_N (dict zachovává insertion order v py3.7+).
    if len(waves) > KEEP_N:
        keep_keys = list(waves.keys())[-KEEP_N:]
        waves = {k: waves[k] for k in keep_keys}

    new_block = _render_block(waves)

    if m:
        return state_text[: m.start()] + new_block + state_text[m.end():]

    # Marker chybí → vlož pod H1 (první řádek začínající "# ").
    lines = state_text.split("\n")
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            break
    head = "\n".join(lines[:insert_at])
    tail = "\n".join(lines[insert_at:])
    sep_before = "\n" if head and not head.endswith("\n") else ""
    return f"{head}{sep_before}\n{new_block}\n{tail}" if head else f"{new_block}\n{tail}"


def record_closed_wave(run_id: str | None = None,
                       state_file: str | None = None,
                       run_state: dict | None = None) -> bool:
    """Zapiš strojová fakta o uzavřené vlně do STATE.md (fail-soft). Vrať True = zapsáno.

    Pořadí zdrojů: explicitní run_state > current-run.md. run_id explicitní > st['run'].
    Každá chyba (chybí STATE.md / I/O / chybí run_id) → WARN na stderr a vrať False.
    NIKDY nevyhazuje výjimku ven (terminál se NESMÍ shodit — vzor git_head()).
    """
    try:
        st = run_state if run_state is not None else state_only(common.run_file_path())
        run_id = run_id or (st or {}).get("run")
        if not run_id:
            print("statewrite: WARN — neznámý run-id (current-run.md neudává 'run'), "
                  "STATE.md machine blok nezapsán.", file=sys.stderr)
            return False

        sf = state_file or state_file_path()
        if not os.path.isfile(sf):
            print(f"statewrite: WARN — {sf} neexistuje, machine blok nezapsán "
                  "(terminál pokračuje).", file=sys.stderr)
            return False

        record = build_record(st, run_id)
        text = open(sf, encoding="utf-8").read()
        new_text = upsert_record(text, run_id, record)

        tmp = sf + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp, sf)
        print(f"STATE.md: machine blok ENGINE:STATE ← uzavřená vlna {run_id} "
              f"(nodes={record['nodes']}, status={record['status']}).")
        return True
    except OSError as e:
        print(f"statewrite: WARN — I/O chyba při zápisu STATE.md ({e}), "
              "machine blok nezapsán (terminál pokračuje).", file=sys.stderr)
        return False


# ── BACKFILL: dopočti strojový blok z historie runs/ (ledger-driven) ──────────
#
# Mechanika auto-zápisu (record_closed_wave) drží jen vlny uzavřené PO jejím vzniku.
# Starší uzavřené vlny v bloku chybí (uzavřely se dřív). Backfill je jednorázová,
# OPAKOVATELNÁ a idempotentní rekonstrukce: projde runs/, najde vlny co dojely na
# terminál, a doplní je stejným tvarem záznamu jako build_record — jen čtené z ledgeru
# (historické vlny nemají current-run.md snapshot).
#
# „Vlna dojela na terminál" detekuje deterministicky poslední záznam ledgeru:
#   - node `done`                                     → terminál grafu
#   - node `l2-review` s outcome ACK | APPROVED        → schválená dodávka (→ done)
#   - node `monitor` s outcome PASS                    → post-deploy OK (→ done)
# Cokoli jiného (planning ledger končící na feasibility, DEFERRED vlna na ui-system)
# = NEdojela → NEbackfillovat (graf-pravda, ne text).

# Terminálně-akceptující outcome pro daný poslední uzel (deterministická tabulka).
_TERMINAL_ACCEPT = {
    "done": {"DONE", "PASS"},
    "l2-review": {"ACK", "APPROVED"},
    "monitor": {"PASS"},
}


def _reached_terminal(entries: list) -> bool:
    """Dojela vlna na terminál `done`? Deterministicky z posledního ledger záznamu
    (poslední node + jeho akceptující outcome dle _TERMINAL_ACCEPT). Prázdný ledger → False."""
    if not entries:
        return False
    last = entries[-1]
    node = last.get("node")
    outcome = last.get("outcome")
    return outcome in _TERMINAL_ACCEPT.get(node, set())


def _first_with(entries: list, key: str) -> dict:
    """První záznam nesoucí daný klíč (typicky intake nese class/flags). Žádný → {}."""
    for e in entries:
        if key in e and e[key] is not None:
            return e
    return {}


def _ledger_mtime_iso(run_id: str) -> str:
    """closed_at pro historickou vlnu = mtime ledger.yaml (nejlepší dostupný strojový čas;
    historický ledger nenese vlastní closed-timestamp). ISO UTC, deterministické z FS."""
    ledger_f = os.path.join(common.runs_dir(run_id), "ledger.yaml")
    ts = os.path.getmtime(ledger_f)
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_record_from_ledger(run_id: str, entries: list) -> dict:
    """Strojová fakta o HISTORICKÉ uzavřené vlně — stejný tvar jako build_record, ale
    čtené z ledgeru (žádný current-run.md snapshot). ŽÁDNÁ lidská věta.

    Odvození:
      status       = 'done' (vlna prošla _reached_terminal — volající to garantuje)
      wave_base    = ledger záznam, pokud ho nese (jen novější vlny); jinak None
      class        = z prvního záznamu s `class` (intake)
      nodes        = počet UNIKÁTNÍCH uzlů v ledgeru (re-flow opakování nepočítá 2×)
      last_outcome = outcome posledního záznamu
      return_loops = přesně z ledgeru (FAIL+returns_to) — stejný zdroj jako live
      touches      = z prvního záznamu s flags (intake), jen _TOUCHES rodina
    """
    intake = _first_with(entries, "class")
    flags = (_first_with(entries, "flags").get("flags")) or {}
    wave_base_rec = _first_with(entries, "wave_base")
    unique_nodes = {e.get("node") for e in entries if e.get("node")}
    rec: dict = {
        "closed_at": _ledger_mtime_iso(run_id),
        "status": "done",
        "wave_base": wave_base_rec.get("wave_base"),
        "class": intake.get("class"),
        "nodes": len(unique_nodes),
        "last_outcome": entries[-1].get("outcome"),
        "return_loops": _count_return_loops_from_ledger(entries),
        "summary": f"runs/{run_id}/summary.md",
        "ledger": f"runs/{run_id}/ledger.yaml",
    }
    touches = {f: common.coerce_flag(flags[f]) for f in _TOUCHES if f in flags}
    if touches:
        rec["touches"] = touches
    return rec


def _discover_closed_waves() -> list[tuple[str, dict]]:
    """Projdi runs/, vrať (run_id, record) pro vlny co dojely na terminál, SEŘAZENO dle
    closed_at (mtime ledgeru) vzestupně → upsert v tomto pořadí dá FIFO „nejnovější poslední".
    Vlny bez ledgeru / co nedojely na terminál se přeskočí (ne-finding, prostě nejsou done)."""
    runs_root = os.path.join(common.run_root(), "runs")
    found: list[tuple[str, dict]] = []
    if not os.path.isdir(runs_root):
        return found
    for run_id in sorted(os.listdir(runs_root)):
        if not os.path.isdir(os.path.join(runs_root, run_id)):
            continue
        entries = _read_ledger_entries(run_id)
        if not _reached_terminal(entries):
            continue
        found.append((run_id, build_record_from_ledger(run_id, entries)))
    found.sort(key=lambda rc: rc[1]["closed_at"])
    return found


def _ensure_summary(run_id: str) -> None:
    """Zajisti runs/<run>/summary.md (odkaz z bloku nesmí mířit do prázdna). Chybí → vygeneruj
    z ledgeru (ledger.generate_summary, fail-soft). Chybí data pro summary → ticho, neselhává;
    odkaz pak ukazuje na neexistující soubor, ale backfill faktů projde (spec §Úkol 1)."""
    summary_f = os.path.join(common.runs_dir(run_id), "summary.md")
    if os.path.isfile(summary_f):
        return
    try:
        import ledger
        ledger.generate_summary(run_id, write=True)   # fail-soft: vrátí None když nejde
    except Exception as e:  # noqa: BLE001 — backfill nesmí spadnout kvůli summary
        print(f"backfill: WARN — summary.md pro {run_id} se nepodařilo vygenerovat ({e}).",
              file=sys.stderr)


def backfill(state_file: str | None = None, dry_run: bool = False) -> int:
    """Jednorázová/opakovatelná rekonstrukce strojového bloku z historie runs/ (idempotentní).

    Projde runs/, najde vlny co dojely na terminál (ledger-driven), pro každou zajistí
    summary.md a UPSERTne záznam do ENGINE:STATE bloku (replay nepřidá duplikát; FIFO KEEP_N
    drží posledních 10 dle closed_at). Vrať počet upsertnutých vln. dry_run → jen vypiš, nezapisuj.

    FAIL-SOFT jako record_closed_wave: chybí STATE.md / I/O chyba → WARN + návrat 0."""
    sf = state_file or state_file_path()
    if not os.path.isfile(sf):
        print(f"backfill: WARN — {sf} neexistuje, blok nedoplněn.", file=sys.stderr)
        return 0

    waves = _discover_closed_waves()
    if not waves:
        print("backfill: žádná uzavřená vlna (terminál) v runs/ — blok beze změny.")
        return 0

    text = open(sf, encoding="utf-8").read()
    m = _BLOCK_RE.search(text)
    existing = _parse_existing(m.group(0)) if m else {}
    for run_id, record in waves:
        # Non-destruktivní upsert: ledger je zdroj pravdy faktů, ale wave_base historický
        # ledger většinou nenese (jen novější vlny) — když ho předchozí (live) záznam MĚL,
        # nepřepiš ho na null (backfill nesmí DEGRADOVAT lepší živá data).
        if record.get("wave_base") is None:
            prev = existing.get(run_id) or {}
            if prev.get("wave_base") is not None:
                record["wave_base"] = prev["wave_base"]
        if not dry_run:
            _ensure_summary(run_id)
        text = upsert_record(text, run_id, record)

    if dry_run:
        print(f"backfill (dry-run): {len(waves)} terminálních vln by se upsertlo "
              f"(FIFO drží posledních {KEEP_N}):")
        for run_id, _ in waves:
            print(f"  - {run_id}")
        return len(waves)

    tmp = sf + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, sf)
    print(f"backfill: {len(waves)} terminálních vln upsertnuto do ENGINE:STATE "
          f"(FIFO drží posledních {KEEP_N}).")
    return len(waves)


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(add_help=True)
    sub = ap.add_subparsers(dest="cmd")

    bf = sub.add_parser("backfill", help="dopočítej blok z historie runs/ (idempotentní)")
    bf.add_argument("--state-file", default=None)
    bf.add_argument("--dry-run", action="store_true")

    ap.add_argument("--state-file", default=None)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    if args.cmd == "backfill":
        backfill(state_file=args.state_file, dry_run=args.dry_run)
        sys.exit(0)

    ok = record_closed_wave(run_id=args.run_id, state_file=args.state_file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
