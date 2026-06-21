#!/usr/bin/env python3
"""status.py — reportuje strojový stav běhu z current-run.md (z state.sh).

Orchestrátor (session-resume „hej Watsone") čte stav strojově místo prózy. Volitelně
validuje node id proti grafu.

CLI:   python3 status.py [current-run.md]
Exit:  0 = OK (idle/in_progress/done) | 1 = pozornost (blocked/awaiting/unknown) | 2 = chyba.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import find_graph, read_state, run_file_path
from graph import Graph


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    run_file = argv[0] if argv else run_file_path()
    graph_file = find_graph() or ""

    if not os.path.isfile(run_file):
        print(f"CHYBA: {run_file} neexistuje. Seed z templates/current-run.md.", file=sys.stderr)
        sys.exit(2)

    st, _txt, m = read_state(run_file)
    if m is None:
        print("CHYBA: v current-run.md chybí ```yaml stavový blok.", file=sys.stderr)
        sys.exit(2)

    def gg(k, d=None):
        return st.get(k, d)

    status = gg("status", "idle")
    active = gg("active_node")
    frontier = gg("frontier") or []
    completed = gg("completed") or []
    skipped = gg("skipped") or []
    counters = gg("counters") or {}
    aw = gg("awaiting_human")
    if isinstance(aw, list):
        awaiting = aw
    else:
        awaiting = [aw] if aw else []
    halt = gg("halt_gate")

    unknown = []
    if graph_file and os.path.isfile(graph_file):
        graph = Graph.load(graph_file)
        for n in [active] + list(frontier) + list(completed) + list(skipped):
            if n and n not in graph:
                unknown.append(n)

    print(f"run:            {gg('run') or '-'}")
    print(f"graph:          {gg('graph') or '-'}")
    print(f"status:         {status}")
    print(f"class:          {gg('class') or '-'}")
    print(f"active_node:    {active}")
    print(f"frontier(infl): {', '.join(frontier) if frontier else '-'}")
    print(f"completed:      {len(completed)} ({', '.join(completed) if completed else '-'})")
    print(f"skipped:        {', '.join(skipped) if skipped else '-'}")
    print(f"counters:       {', '.join(f'{k}={v}' for k, v in counters.items()) if counters else '-'}")
    print(f"awaiting_human: {', '.join(awaiting) if awaiting else '-'}")
    pending_deleg = gg("pending_delegations") or []
    if pending_deleg:
        deleg_gates = [d.get("gate", "?") for d in pending_deleg if isinstance(d, dict)]
        print(f"pending_deleg:  {', '.join(deleg_gates) if deleg_gates else '-'}")
    print(f"halt_gate:      {halt or '-'}")
    print(f"last_outcome:   {gg('last_outcome') or '-'}")
    findings = gg("findings") or []
    if findings:
        adv = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "advisory")
        print(f"findings:       {len(findings)} ({adv} advisory, {len(findings) - adv} blocking)")
    pending = {k: v for k, v in (gg("return_payload") or {}).items() if v}
    if pending:
        print("return_payload: " + "; ".join(f"{k}←{len(v)}" for k, v in pending.items()))
    mov = gg("model_overrides") or {}
    if mov:
        print("model_overrides:" + " " + ", ".join(f"{k}={v}" for k, v in mov.items()) + " (triage > graf)")
    print(f"note:           {gg('note') or '-'}")

    # Transparency: přepočti ŽIVÝ frontier ze stavu (ne jen echo inflightu). `frontier(infl)`
    # ukazuje jen rozdělaný uzel; tohle odhalí, co engine reálně považuje za otevřené —
    # včetně stale-reopnutých completed uzlů (recompute > inflight echo).
    if graph_file and os.path.isfile(graph_file):
        try:
            import frontier as _frontier
            fr = _frontier.frontier_for_state(st, graph_file)
            ready = [r["node"] for r in fr.get("ready", [])]
            judgment = [r["node"] for r in fr.get("judgment", [])]
            waiting = [r["node"] for r in fr.get("waiting", [])]
            infl = set(fr.get("inflight", []))
            completed_set = set(completed)
            # stale-reopened = uzel ŽIVÝ ve frontieru (ready/judgment/waiting), který byl
            # dřív v completed → staleness ho znovuotevřela (ne čerstvě nedosažený).
            stale_reopened = [n for n in (ready + judgment + waiting)
                              if n in completed_set and n not in infl]
            print(f"frontier-ready: {', '.join(ready) if ready else '-'}")
            if judgment:
                print(f"frontier-judg:  {', '.join(judgment)}")
            print(f"stale-reopened: {', '.join(stale_reopened) if stale_reopened else '-'}")
            print(f"terminal_reached: {str(fr.get('terminal_reached', False)).lower()}")
        except Exception as e:   # status nesmí spadnout kvůli transparency vrstvě
            print(f"frontier-recompute: ERROR ({type(e).__name__})")

    if unknown:
        print(f"WARN unknown-nodes: {', '.join(unknown)} (nejsou v {graph_file})")

    blocked_counters = [k for k, v in counters.items() if isinstance(v, int) and v >= 3]
    if blocked_counters:
        print(f"WARN blocker-loop: {', '.join(blocked_counters)} dosáhlo 3× (BLOCKER — eskaluj o roli výš)")

    if status in ("blocked", "awaiting_human") or halt or awaiting or blocked_counters or unknown:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
