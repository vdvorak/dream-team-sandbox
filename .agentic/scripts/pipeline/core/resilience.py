#!/usr/bin/env python3
"""resilience.py — engine-native resilience: `repair` (replay z ledgeru) + `checkpoint`.

Párová dvojice z backlog/agent-command-guardrails.md §6 (prevence + zotavení):

- **repair**  — rekonstruuje current-run.md z runs/<run>/ledger.yaml. Ledger je
  append-only zdroj pravdy (každý done = envelope dokument); replay envelope přes
  STEJNOU advance_state logiku z result.py → stav je deterministicky odvozený z
  ledgeru, ne ručně sestavený. IDEMPOTENTNÍ: opakovaný repair nad stejným ledgerem
  dá bajt-identický current-run.md (ledger se nemění, replay je čistá funkce).
  Dnes se to dělalo ručně (`start` + replay `done`) — povýšeno na první-třídní příkaz.

- **checkpoint** — levný engine-native snapshot current-run.md + reference na ledger
  do runtime cesty MIMO working tree (.agentic/.checkpoint/, gitignored). Cíl: engine
  drží poslední dobrý stav nezávisle na gitu (git stash/reset v agent-shellu se k němu
  nedostane). IDEMPOTENTNÍ: opakovaný checkpoint přepíše posledním (atomicky).

Obojí běží jako ENGINE příkaz (run.sh repair / run.sh checkpoint), mimo agent-shell.

CLI:  python3 resilience.py repair [run-id] [--run-file …] [--dry-run]
      python3 resilience.py checkpoint [--run-file …] [--restore]
Exit: 0 = OK | 2 = chyba (chybí ledger / current-run.md).
"""
import argparse
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import require_graph, write_state, yaml
from graph import Graph
from runstate import RunState


# ── checkpoint ────────────────────────────────────────────────────────────────
def checkpoint_dir() -> str:
    """Runtime cesta pro snapshoty — pod .agentic/, MIMO working tree (gitignored).

    Ukotveno na run_root() (kořen projektu, cwd-nezávislý jako current-run.md), takže
    checkpoint sedí vedle stavu, který zálohuje. AGENTIC_RUN_ROOT v selftestu izoluje
    do mktemp → testy nikdy nepíšou do reálného .agentic/.checkpoint/."""
    return os.path.join(common.run_root(), ".agentic", ".checkpoint")


def checkpoint(run_file: str | None = None, *, quiet: bool = False) -> str | None:
    """Snapshot current-run.md + reference na aktuální ledger do checkpoint_dir().

    IDEMPOTENTNÍ: vždy přepíše current-run.snapshot.md posledním stavem (atomicky tmp +
    os.replace). meta.yaml drží run-id + ledger pozici (počet záznamů) + čas — levný
    HEAD pointer (ledger je append-only, stačí znát, kolik záznamů snapshot viděl).

    FAIL-SOFT: chybí current-run.md → WARN + None (není co checkpointovat; nesmí shodit
    dispatch). Vrací cestu ke snapshotu, nebo None když nebyl co dělat."""
    rf = run_file or common.run_file_path()
    if not os.path.isfile(rf):
        if not quiet:
            print("checkpoint: current-run.md chybí — není co zálohovat (no-op).", file=sys.stderr)
        return None

    st = common.state_only(rf)
    run_id = (st or {}).get("run")

    cp_dir = checkpoint_dir()
    os.makedirs(cp_dir, exist_ok=True)

    snap = os.path.join(cp_dir, "current-run.snapshot.md")
    tmp = snap + ".tmp"
    shutil.copyfile(rf, tmp)
    os.replace(tmp, snap)

    # ledger HEAD pozice = počet append-only dokumentů (levný pointer, ledger se needituje)
    ledger_count = 0
    ledger_path = None
    if run_id:
        ledger_path = os.path.join(common.runs_dir(run_id), "ledger.yaml")
        if os.path.isfile(ledger_path):
            try:
                ledger_count = sum(
                    1 for d in yaml.safe_load_all(open(ledger_path, encoding="utf-8")) if d
                )
            except (OSError, yaml.YAMLError):
                ledger_count = 0

    meta = {
        "run": run_id,
        "active_node": (st or {}).get("active_node"),
        "status": (st or {}).get("status"),
        "ledger": ledger_path,
        "ledger_entries": ledger_count,
        "checkpointed_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = os.path.join(cp_dir, "meta.yaml")
    meta_tmp = meta_path + ".tmp"
    with open(meta_tmp, "w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, sort_keys=False, allow_unicode=True)
    os.replace(meta_tmp, meta_path)

    if not quiet:
        print(f"checkpoint: snapshot → {snap} (run={run_id} active={meta['active_node']} "
              f"ledger_entries={ledger_count})")
    return snap


def restore_checkpoint(run_file: str | None = None) -> bool:
    """Obnov current-run.md z posledního snapshotu (rychlý rollback). Vrať True/False.

    Levná první linie před plným `repair`: snapshot je doslovná kopie posledního dobrého
    current-run.md. Když chybí, vrať False (volající padne na repair z ledgeru)."""
    rf = run_file or common.run_file_path()
    snap = os.path.join(checkpoint_dir(), "current-run.snapshot.md")
    if not os.path.isfile(snap):
        print("checkpoint: žádný snapshot k obnově (.agentic/.checkpoint/ prázdný).", file=sys.stderr)
        return False
    tmp = rf + ".tmp"
    shutil.copyfile(snap, tmp)
    os.replace(tmp, rf)
    print(f"checkpoint: current-run.md obnoven ze snapshotu → {rf}")
    return True


# ── repair (replay z ledgeru) ───────────────────────────────────────────────────
def _resolve_run_id(run_id: str, run_file: str) -> str:
    """run-id z argumentu, jinak z current-run.md."""
    if run_id:
        return run_id
    if os.path.isfile(run_file):
        return (common.state_only(run_file) or {}).get("run") or ""
    return ""


def _ledger_entries(run_id: str) -> list[dict]:
    """Append-only dokumenty z runs/<run>/ledger.yaml. Chybí → FileNotFoundError."""
    ledger = os.path.join(common.runs_dir(run_id), "ledger.yaml")
    if not os.path.isfile(ledger):
        raise FileNotFoundError(ledger)
    return [e for e in yaml.safe_load_all(open(ledger, encoding="utf-8")) if e]


def _is_done_envelope(entry: dict) -> bool:
    """Done envelope (replayovatelný) vs auditní záznam (resolve-loop intervence).

    result.append_ledger píše envelope s povinným `node` + `outcome`. resolve-loop píše
    intervenci s `kind: resolve-loop` + `intervened` (BEZ node/outcome). Repair replayuje
    JEN done envelope; intervence se neaplikují (counter reset je orchestrátorský zásah,
    ne výrobní krok — replay výroby ho legitimně ignoruje, ledger ho drží jako audit)."""
    if not isinstance(entry, dict):
        return False
    if entry.get("kind") == "resolve-loop":
        return False
    return bool(entry.get("node")) and bool(entry.get("outcome"))


def rebuild_state(run_id: str, graph: Graph) -> dict:
    """Deterministicky rekonstruuj stav přehráním ledger envelope přes result.advance_state.

    Začni z čistého fresh_result (jako `start`), pak pro každý done envelope v pořadí
    zápisu zopakuj STEJNOU stavovou mutaci jako live /done. Reuse result.py → repair se
    nikdy nerozejde s živým chováním (jeden zdroj outcome-handlerů). Píše do dočasného
    run_file, který na konci přečteme — advance_state je file-orientované, tak ho krmíme
    izolovaným souborem v checkpoint_dir, aby repair neměl meziprodukt v reálném stavu."""
    import result  # lazy: result importuje vocab/graph; drž import lokálně jako run.py

    entries = _ledger_entries(run_id)

    # Dočasný pracovní run_file (mimo reálný current-run.md) — advance_state je file-based.
    work_dir = checkpoint_dir()
    os.makedirs(work_dir, exist_ok=True)
    work_file = os.path.join(work_dir, "repair.work.md")

    # wave_base: z prvního envelope, který ho nese (start ho ukládá do stavu, ale ledger
    # ho nemá per-záznam) → ponech None když ledger neví; repair neobnovuje git ref, jen
    # výrobní stav. wave_base je provenance, ne výrobní fakt — degraduje na full-scan.
    seed = RunState.fresh_result(run_id)
    common.write_state(work_file, seed)

    replayed = 0
    last_node = None
    for env in entries:
        if not _is_done_envelope(env):
            continue
        # Replay = validace + derive + advance, ale BEZ append_ledger (ledger je vstup).
        node = env.get("node")
        outcome = env.get("outcome")
        if node not in graph:
            # Uzel zmizel z grafu po zápisu (graf se změnil) — přeskoč, neshazuj repair.
            continue
        node_def = graph.nodes[node]
        # derive_outputs/validate jako live done, ať stav (flags, agent, phase) sedí.
        result.derive_outputs(env, node_def, outcome)
        result.advance_state(work_file, run_id, node, outcome, env, graph, node_def)
        replayed += 1
        last_node = node

    rebuilt = common.state_only(work_file)
    # úklid pracovního souboru (idempotence: nezůstává meziprodukt)
    try:
        os.remove(work_file)
    except OSError:
        pass
    rebuilt["_repair_replayed"] = replayed   # vnitřní pomocná stopa (odstraní se před zápisem)
    rebuilt["_repair_last_node"] = last_node
    return rebuilt


def repair(run_id: str = "", run_file: str | None = None, *, dry_run: bool = False) -> int:
    """run.sh repair — rekonstruuj current-run.md z ledgeru (replay). Idempotentní.

    Exit 0 = OK; 2 = chybí ledger / nelze určit run-id."""
    rf = run_file or common.run_file_path()
    rid = _resolve_run_id(run_id, rf)
    if not rid:
        print("repair: nelze určit run-id (zadej argument nebo měj current-run.md s `run`).",
              file=sys.stderr)
        return 2

    graph = Graph.load(require_graph())

    try:
        rebuilt = rebuild_state(rid, graph)
    except FileNotFoundError as e:
        print(f"repair: chybí ledger {e} — není z čeho replayovat run '{rid}'.", file=sys.stderr)
        return 2

    replayed = rebuilt.pop("_repair_replayed", 0)
    last_node = rebuilt.pop("_repair_last_node", None)

    if dry_run:
        print(f"repair (dry-run): run={rid} replayed={replayed} done-envelope, "
              f"active_node={rebuilt.get('active_node')} status={rebuilt.get('status')} "
              f"completed={len(rebuilt.get('completed') or [])} — NEZAPSÁNO.")
        return 0

    write_state(rf, rebuilt)
    print(f"repair: current-run.md rekonstruován z ledgeru → run={rid} "
          f"replayed={replayed} done-envelope, active_node={rebuilt.get('active_node')} "
          f"status={rebuilt.get('status')} completed={len(rebuilt.get('completed') or [])} "
          f"(last={last_node}).")
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_repair = sub.add_parser("repair", help="replay current-run.md z ledgeru")
    p_repair.add_argument("run_id", nargs="?", default="")
    p_repair.add_argument("--run-file", default=None)
    p_repair.add_argument("--dry-run", action="store_true")

    p_cp = sub.add_parser("checkpoint", help="snapshot current-run.md mimo working tree")
    p_cp.add_argument("--run-file", default=None)
    p_cp.add_argument("--restore", action="store_true", help="obnov current-run.md ze snapshotu")

    args = ap.parse_args(argv)

    if args.cmd == "repair":
        sys.exit(repair(args.run_id, args.run_file, dry_run=args.dry_run))
    elif args.cmd == "checkpoint":
        if args.restore:
            sys.exit(0 if restore_checkpoint(args.run_file) else 2)
        sys.exit(0 if checkpoint(args.run_file) is not None else 2)


if __name__ == "__main__":
    main()
