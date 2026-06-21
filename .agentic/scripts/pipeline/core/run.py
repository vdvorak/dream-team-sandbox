#!/usr/bin/env python3
"""run.py — jednotný vstup do pipeline runneru (deterministický executor) (z run.sh).

Sjednocuje start/active/skip/status/next/drive/done/summary/check/scaffold. „Runner"
executor z VISION §Most (LLM orchestrátor / runner / app = vyměnitelné executory nad
stejným grafem+stavem). `drive` importuje frontier přímo (konec subprocess+JSON).

CLI: python3 run.py <subcommand> [args]
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import frontier
from common import find_graph, load_graph, read_state, write_state
from graph import Graph
from runstate import RunState

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)  # scripts/pipeline/ (kde leží .sh shimy)

USAGE = """run.py — jednotný vstup do pipeline runneru.

Subcommands:
  start <run-id>       seedne current-run.md (frontier model)
  active <node>        nastaví active_node (ruční override)
  skip <node>          judged-skip: frontier přestane uzel počítat jako producenta
  status [run-file]    kde běh stojí
  next [args]          další uzel(y) (--emit frontier / --from …)
  drive                frontier executor: READY množina jako akce
  done <envelope>      /done: zaznamenej výstup uzlu, posuň stav (+ commit-on-done)
  resolve-loop <edge>  N3 recovery: vědomě vynuluj counter hrany 'node->target', odblokuj
                       counter-blocked běh (NE REJECTED), zapiš auditní intervenci do ledgeru
  repair [run-id]      rekonstruuj current-run.md z runs/<run>/ledger.yaml (replay, idempotentní)
  checkpoint           engine-native snapshot current-run.md mimo working tree (.agentic/.checkpoint/)
  summary [run-id]     cost + čas per issue
  check                integrita grafu C1–C13
  scaffold [args]      resolve scaffoldu
"""


def on_terminal(state: RunState) -> None:
    """Vlna dojela na terminál (status=done) → engine zapíše strojová fakta o uzavřené
    vlně do STATE.md a vygeneruje runs/<wave>/summary.md (odkaz z machine bloku).

    KRITICKÉ fail-soft (constitution-style, vzor git_head): obě operace degradují na WARN
    a NIKDY nevyhodí výjimku ven — terminál se nesmí shodit kvůli STATE.md / summary I/O.
    Hook patří SEM (jediné místo, kde drive reálně nastaví status=done), ne do result.py.
    """
    import ledger
    import statewrite
    run_id = state.get("run")
    try:
        ledger.generate_summary(run_id, write=True)   # fail-soft: chybí ledger → None
    except Exception as e:  # noqa: BLE001 — terminál nesmí spadnout kvůli summary
        print(f"summary: WARN — generování summary.md selhalo ({e}); terminál pokračuje.",
              file=sys.stderr)
    statewrite.record_closed_wave(run_id=run_id, run_state=state.st)   # sám fail-soft


def git_head() -> str | None:
    """`git rev-parse HEAD` jako wave_base (FIX #1). Selhání (mimo git / no commits) → None
    → start NIKDY nefailuje kvůli gitu; brány degradují na full-scan."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
        sha = out.stdout.strip()
        return sha if out.returncode == 0 and sha else None
    except (OSError, subprocess.SubprocessError):
        return None


# ── mutace current-run.md (start/active/skip) ─────────────────────────────────
def _start_capture_baseline() -> list[str] | None:
    """Při `start` zachyť commit baseline-exclusion set + vypiš ADVISORY o stavu tree.

    Dřív byl tu TVRDÝ clean-tree guard (commit-on-done dělal `git add -A`, špinavý tree by
    se zametl). Teď commit-on-done stageuje BASELINE-EXCLUSION: zachytíme cesty dirty/untracked
    PŘED vlnou a commit_node je nikdy nestageuje. Pre-existing stav je tím vyloučen
    KONSTRUKCÍ → tvrdé odmítnutí ztratilo důvod a degradovalo by start v repu s trvalými
    runtime artefakty (runs/fixture-*, .tmp/ …). Proto jen ADVISORY: vypiš, kolik cest
    vyloučíme, ale neodmítej. Vypínač AGENTIC_NODE_COMMIT=0 → engine necommituje, baseline
    je zbytečná (vrať None). Mimo git → None (fail-soft, jako git_head)."""
    import nodecommit
    if not nodecommit.commit_enabled():
        return None
    baseline = nodecommit.capture_baseline()
    if baseline is None:
        return None   # mimo git / nelze zjistit → fail-soft
    if baseline:
        print(f"start: ADVISORY — {len(baseline)} cest je dirty/untracked PŘED vlnou; "
              f"commit-on-done je vyloučí z node-commitů (nezamete je). "
              f"Pre-existing stav vlna nevlastní.", file=sys.stderr)
    return baseline


def mutate_state(mode: str, val: str) -> None:
    graph_file = find_graph()
    entry = "intake"
    if graph_file and os.path.isfile(graph_file):
        entry = (load_graph(graph_file).get("meta", {}) or {}).get("entry", "intake")
    rf = common.run_file_path()
    st = read_state(rf)[0]
    if mode == "start":
        # commit-on-done baseline-exclusion: zachyť dirty/untracked PŘED vlnou (ADVISORY,
        # už NE tvrdý guard) → commit_node tyhle cesty nezamete do node-commitů.
        baseline = _start_capture_baseline()
        # FIX #4: jediný zdroj defaultu = RunState.fresh_result (vč. counters={} → nová vlna
        # NEDĚDÍ countery předchozí vlny; in-wave guard se počítá od nuly). FIX #1: wave_base =
        # git HEAD při startu. start jen přepíše active_node na entry (fresh_result má None).
        st = RunState.fresh_result(val, wave_base=git_head())
        st["active_node"] = entry
        if baseline is not None:   # mimo git / commit vypnut → None: klíč vůbec neukládáme
            st["commit_baseline"] = baseline
    elif mode == "active":
        st["active_node"] = val
        st.setdefault("status", "in_progress")
    elif mode == "skip":
        sk = st.get("skipped") or []
        if val not in sk:
            sk.append(val)
        st["skipped"] = sk
        fr = st.get("frontier") or []   # judged-skip uzel nesmí zůstat inflight (jinak běh visí)
        if val in fr:
            fr.remove(val)
        st["frontier"] = fr
        st.setdefault("status", "in_progress")
    write_state(rf, st)
    print(f"current-run.md: {mode} → run={st.get('run')} active_node={st.get('active_node')}")


# ── resolve-loop — N3 clean loop-recovery (vědomá orchestrátorská intervence) ──
def _audit_intervention(run: str | None, edge: str, prev_count: int, ts: str) -> None:
    """Zapiš auditní stopu intervence do runs/<run>/ledger.yaml (append-only, jako result.py).
    Bez `run` (neznámý běh) audit přeskočíme — stav je už přepnut, jen nemáme kam stopu psát."""
    if not run:
        print("resolve-loop: WARN — stav bez 'run', auditní stopa do ledgeru přeskočena.", file=sys.stderr)
        return
    rec = {"intervened": edge, "kind": "resolve-loop", "prev_count": prev_count, "at": ts}
    ledger_dir = common.runs_dir(run)
    os.makedirs(ledger_dir, exist_ok=True)
    ledger = os.path.join(ledger_dir, "ledger.yaml")
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("---\n")
        common.yaml.safe_dump(rec, fh, sort_keys=False, allow_unicode=True)
    print(f"ledger: auditní intervence připsána → {ledger}")


def resolve_loop(edge: str) -> None:
    """N3: vědomě vynuluj return counter hrany `edge` (formát 'node->target') a odblokuj běh.

    KRITICKÉ (constitution §8 tvrdý halt): odblokuje JEN counter-blocked běh, NIKDY REJECTED-blocked.
    Counter-blocked rozeznáme: status == 'blocked' AND counter dané hrany dosáhl prahu (>=3).
    REJECTED / BLOCKER bez counteru → odmítnuto (exit 2), člověk musí řešit příčinu, ne uvolnit smyčku.
    """
    from datetime import datetime, timezone
    rf = common.run_file_path()
    if not os.path.isfile(rf):
        print("resolve-loop: current-run.md chybí — není co odblokovat.", file=sys.stderr)
        sys.exit(2)
    state = RunState(read_state(rf)[0])
    state.ensure_result_keys()

    if "->" not in edge:
        print(f"resolve-loop: '{edge}' není hrana ve formátu 'node->target'.", file=sys.stderr)
        sys.exit(2)

    counters = state.get("counters") or {}
    count = int(counters.get(edge, 0))
    # REJECTED-blocked guard: tvrdý halt z constitution §8 NESMÍ jít uvolnit resolve-loopem.
    note = (state.note or "")
    is_rejected = "REJECTED" in note
    if is_rejected:
        print(f"resolve-loop: ODMÍTNUTO — běh je blocked z REJECTED (constitution §8 tvrdý halt): "
              f"{note}. Loop-recovery uvolňuje JEN counter-blocked smyčky, ne REJECTED. "
              f"Vyřeš příčinu rejectu, neuvolňuj counter.", file=sys.stderr)
        sys.exit(2)
    if count < 3:
        # Buď hrana neexistuje, nebo nedosáhla prahu → není to counter-block této hrany.
        print(f"resolve-loop: ODMÍTNUTO — hrana '{edge}' není counter-blocked (counter={count}, "
              f"práh=3). Není co odblokovat; zkontroluj 'run.py status' / counters.", file=sys.stderr)
        sys.exit(2)

    ts = datetime.now(timezone.utc).isoformat()
    prev = state.reset_counter(edge)          # vynuluj counter (vrátí předchozí hodnotu)
    if state.status == "blocked":             # přepni JEN counter-blocked stav (REJECTED už odmítnut výš)
        state.status = "in_progress"
        state.note = f"resolve-loop: {edge} odblokováno (counter {prev}→0) @ {ts}"
    run = state.get("run")
    state.add_finding(edge, "intervention", None, f"resolve-loop counter {prev}->0 @ {ts}")
    write_state(rf, state.st)
    _audit_intervention(run, edge, prev, ts)
    print(f"resolve-loop: {edge} counter {prev}→0, status={state.status}. "
          f"Pokračuj run.py drive.")


# ── drive — frontier executor ─────────────────────────────────────────────────
def partition_ready(ready: list, graph: Graph) -> dict[str, list]:
    """Roztřiď ready uzly dle node.drive_category (polymorfně) místo string-žebříku nad `type`.
    Pořadí v každém kbelíku = pořadí v ready (faithful k dřívějšímu `by(type)` filtru)."""
    cats: dict[str, list] = {"JOIN": [], "TERMINAL": [], "BLOCKING_GATE": [],
                             "FREE_GATE": [], "WORKER": [], "ROUTER": []}
    for r in ready:
        nd = graph.get(r["node"])
        cat = nd.drive_category(r.get("blocking")) if nd else None
        if cat in cats:
            cats[cat].append(r)
    return cats


def print_dispatch(workers: list, g_free: list, state: RunState) -> None:
    """Vytiskni FRONTIER dispatch řádky (workery s modelem + re-flow payloadem, free human-gaty).
    Selftest parsuje NODE = první token po 'DISPATCH '/'HUMAN-GATE ' (= klíč pro done) — node MUSÍ
    zůstat první token; zbytek řádky (→ agent:…, model:…) je volný. DISPATCH cíl invokace = agent:
    short (cast binding role→persona, který engine vyřešil), NE node-id; role≠persona se liší."""
    print(f"FRONTIER ({len(workers) + len(g_free)} ready, {len(state.inflight)} inflight):")
    rp = state.get("return_payload") or {}
    mov = state.get("model_overrides") or {}
    for w in workers:
        gm = w.get("model", "-")
        om = mov.get(w["node"])
        model = f"{om}*" if om else gm
        print(f"  DISPATCH {w['node']:18} → agent:{w.get('agent', '-'):16} model:{model}")
        for sig in rp.get(w["node"], []):
            print(f"      ↻ re-flow finding: {sig}")
    for g in g_free:
        print(f"  HUMAN-GATE {g['node']:16} level:{g.get('level') or '-'} blocking:false "
              f"interaction:{g.get('interaction') or '-'}")
    print("→ invokuj subagenta přes jeho agent: short z řádky výše (cast binding, NE node-id; "
          "role≠persona: design-audit→edna-design). Víc workerů = paralelně; gaty po lidském vstupu. "
          "Po každém: run.py done <envelope> (klíč = node). Pak run.py drive.")


def _auto_checkpoint(state: RunState) -> None:
    """Engine-native checkpoint (§6.1) PŘED rizikovým krokem (dispatch agenta / halt na gate).
    Levný snapshot current-run.md mimo working tree → poslední dobrý stav nezávislý na gitu,
    než agent něco rozhodí. Fail-soft (resilience.checkpoint sám WARN-uje, nikdy nevyhodí)."""
    import resilience
    try:
        resilience.checkpoint(quiet=True)
    except Exception as e:  # noqa: BLE001 — checkpoint je doplněk, dispatch se nesmí shodit
        print(f"checkpoint: WARN — auto-checkpoint selhal ({e}); pokračuji.", file=sys.stderr)


def _commit_engine_advance(state: RunState, node: str, outcome: str) -> None:
    """commit-on-done pro engine-interní advance (auto-skip / join / terminal), které
    NEjdou přes result.main (a tedy přes jeho commit_node). Syntetický envelope nese jen
    node/run/outcome — stejná konvence message jako live done. Fail-soft.

    Baseline-exclusion: commit_baseline ze stavu (zachycený při `start`) → engine-advance
    stageuje jen wave-změny, ne pre-existing haraburdí."""
    import nodecommit
    env = {"run": state.get("run"), "node": node, "outcome": outcome, "agent": "engine"}
    try:
        nodecommit.commit_node(env, baseline=state.get("commit_baseline"))
    except Exception as e:  # noqa: BLE001 — commit je doplněk, advance se nesmí shodit
        print(f"commit-on-done: WARN — commit engine-advance '{node}' selhal ({e}).", file=sys.stderr)


def drive() -> None:
    rf = common.run_file_path()
    if not os.path.isfile(rf):
        print("DRIVE: current-run.md chybí — nejdřív `run.py start <run-id>`.", file=sys.stderr)
        sys.exit(2)
    state = RunState(read_state(rf)[0])
    state.ensure_drive_keys()
    graph = Graph.load(common.require_graph())

    def write() -> None:
        write_state(rf, state.st)

    if state.status == "done":
        print("DONE: běh uzavřen.")
        sys.exit(0)
    if state.status == "blocked":
        note = state.note or "běh blokován (REJECTED / 3× counter / BLOCKER)"
        print(f"BLOCKED: {note}. Orchestrátor musí zasáhnout — po vyřešení uprav stav a spusť run.py drive.")
        sys.exit(1)
    if state.halt_gate:
        gate = state.halt_gate
        print(f"HALT (blocking gate): {gate} — destruktivní krok, čeká na explicitní ano/ne. "
              f"Po lidském vstupu: run.py done <envelope> (APPROVED|REJECTED).")
        sys.exit(0)

    for _guard in range(200):
        j = frontier.frontier_for_state(state.st)
        cats = partition_ready(j.get("ready") or [], graph)
        joins, terminals, routers = cats["JOIN"], cats["TERMINAL"], cats["ROUTER"]
        workers = cats["WORKER"]
        g_block, g_free = cats["BLOCKING_GATE"], cats["FREE_GATE"]

        # FIX #2 lehká dráha: uzly s pravdivým skip_if (feasibility/architecture na improvement
        # bez stack-impactu a bez nového kontraktu) → auto-PASS bez dispatchu / AI mid-wave.
        auto_skip = j.get("auto_skip") or []
        if auto_skip:
            for nid in auto_skip:
                state.mark_completed(nid)
                state.set_outcome(nid, "PASS")
                state.active_node = nid
            write()
            # commit-on-done i pro engine-interní advance (auto-skip nemá result.main cestu).
            for nid in auto_skip:
                _commit_engine_advance(state, nid, "PASS")
            print(f"AUTO-SKIP (lehká dráha): {', '.join(auto_skip)} → PASS (skip_if splněn).")
            continue

        # Prioritní žebřík (joins → terminals → blocking-gate → workers+free-gate → routers →
        # judgment → inflight → terminal_reached → BLOCKED) je POLICY EXECUTORU — explicitní.
        if joins:
            for jn in joins:
                n = jn["node"]
                state.mark_completed(n)
                state.set_outcome(n, "PASS")
                state.active_node = n
            write()
            for jn in joins:
                _commit_engine_advance(state, jn["node"], "PASS")
            continue

        if terminals:
            n = terminals[0]["node"]
            state.mark_completed(n)
            state.set_outcome(n, "DONE")
            state.active_node = n
            state.status = "done"
            write()
            on_terminal(state)   # engine → STATE.md machine blok + summary.md (fail-soft)
            # terminal commit: uzavření vlny (STATE.md/summary.md jsou už zapsané on_terminal výš).
            _commit_engine_advance(state, n, "DONE")
            print(f"DONE: dosažen terminal '{n}' — běh u konce.")
            sys.exit(0)

        if g_block:
            g = g_block[0]
            n = g["node"]
            _auto_checkpoint(state)   # snapshot PŘED halt na blocking gate (rizikový krok)
            state.add_inflight(n)
            state.halt_gate = n
            state.active_node = n
            write()
            print(f"HALT (blocking gate): {n} interaction:{g.get('interaction') or '-'} "
                  f"level:{g.get('level') or '-'} — explicitní ano/ne. Po vstupu: run.py done <envelope>.")
            sys.exit(0)

        if workers or g_free:
            _auto_checkpoint(state)   # snapshot PŘED dispatchem agenta (§6.1 engine-native checkpoint)
            for w in workers + g_free:
                state.add_inflight(w["node"])
            for g in g_free:
                state.add_awaiting(g["node"])
            state.active_node = (workers or g_free)[0]["node"]
            write()
            print_dispatch(workers, g_free, state)
            sys.exit(0)

        if routers:
            n = routers[0]["node"]
            print(f"DECIDE: klasifikuj '{n}' (feature | bugfix | improvement) → "
                  f"run.py done <envelope> (outcome PASS, class: <třída>).")
            sys.exit(0)

        judgment = j.get("judgment") or []
        if judgment:
            print("DECIDE: ready prázdné, čeká úsudek nad judgment hranou — invokuj přes agent: short "
                  "(NE node-id), nebo run.py skip <node>:")
            for c in judgment:
                print(f"  - {c['node']:18} → agent:{c.get('agent', '-'):16} (type:{c.get('type')})")
            sys.exit(0)

        inflight = j.get("inflight") or []
        if inflight:
            print(f"INFLIGHT: čeká na dokončení dispatchnutých uzlů: {', '.join(inflight)}. "
                  f"Po run.py done pokračuj run.py drive.")
            sys.exit(0)
        if j.get("terminal_reached"):
            state.status = "done"
            write()
            on_terminal(state)   # engine → STATE.md machine blok + summary.md (fail-soft)
            _commit_engine_advance(state, state.active_node or "terminal", "DONE")
            print("DONE: běh u konce.")
            sys.exit(0)
        print("BLOCKED: frontier prázdný, nic ready/inflight/judgment a není terminal — "
              "graf drhne (potřeba return / oprava). Zkontroluj outcomes/graf.")
        sys.exit(1)

    print("DRIVE: překročen guard 200 iterací (cyklus v auto-advance?).", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "help"
    rest = argv[1:]

    if cmd == "start":
        if not rest:
            print("Usage: run.py start <run-id>", file=sys.stderr)
            sys.exit(2)
        mutate_state("start", rest[0])
    elif cmd == "active":
        if not rest:
            print("Usage: run.py active <node>", file=sys.stderr)
            sys.exit(2)
        mutate_state("active", rest[0])
    elif cmd == "skip":
        if not rest:
            print("Usage: run.py skip <node>", file=sys.stderr)
            sys.exit(2)
        mutate_state("skip", rest[0])
    elif cmd == "resolve-loop":
        if not rest:
            print("Usage: run.py resolve-loop <edge>  (formát 'node->target', např. 'spec-gate->product')",
                  file=sys.stderr)
            sys.exit(2)
        resolve_loop(rest[0])
    elif cmd == "repair":
        import resilience
        # BUG B: run-id = první NE-flag argument (ne rest[0]) — jinak `repair --dry-run`
        # bez run-id vezme "--dry-run" jako run-id a hledá neexistující run.
        run_id = next((a for a in rest if not a.startswith("--")), "")
        sys.exit(resilience.repair(run_id, dry_run="--dry-run" in rest))
    elif cmd == "checkpoint":
        import resilience
        if "--restore" in rest:
            sys.exit(0 if resilience.restore_checkpoint() else 2)
        sys.exit(0 if resilience.checkpoint() is not None else 2)
    elif cmd == "drive":
        drive()
    elif cmd == "status":
        import status
        status.main(rest)
    elif cmd == "next":
        frontier.main(rest)
    elif cmd == "done":
        import result
        result.main(rest)
    elif cmd == "summary":
        import ledger
        ledger.main(rest)
    elif cmd == "check":
        import check
        check.main(rest)
    elif cmd == "scaffold":
        # resolver (Fáze 3) — zatím přes sourozenecký .sh shim
        sys.exit(subprocess.run(["bash", os.path.join(PARENT, "scaffold.sh"), *rest]).returncode)
    elif cmd in ("help", "-h", "--help"):
        print(USAGE)
    else:
        print(f"Neznámý subcommand: {cmd}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
