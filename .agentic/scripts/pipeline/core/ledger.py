#!/usr/bin/env python3
"""ledger.py — agreguje cost + čas běhu z runs/<run>/ledger.yaml (z ledger.sh).

Na konci issue (= run) řekne: jak dlouho to trvalo a kolik to stálo. Sečte čas
(wall-clock + compute), kredity, tokeny; rozpad per model / per uzel; return loops.
Volitelně dopočítá odhad kreditů z tokenů přes pipeline/model-prices.yaml. Zapíše summary.md.

CLI:   python3 ledger.py [<run-id>] [--no-write]   (bez run-id → `run` z current-run.md)
Exit:  0 = OK | 2 = chyba (chybí ledger).
"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import state_only, yaml


def _resolve_run_id(run_id: str = "") -> str:
    """run-id z argumentu, jinak z current-run.md. Prázdné = chyba."""
    if run_id:
        return run_id
    rf = common.run_file_path()
    if os.path.isfile(rf):
        return (state_only(rf) or {}).get("run") or ""
    return ""


def render_summary(run_id: str) -> str:
    """Vyrenderuj run summary (cost + čas + per model/uzel + return loops) jako markdown.
    Čistá funkce nad ledgerem — volatelná z terminálu (run.py drive) i z CLI (main).
    Vyhodí FileNotFoundError když ledger chybí (volající rozhodne fail-hard vs fail-soft)."""
    prices_f = ""
    for p in (".agentic/pipeline/model-prices.yaml", "pipeline/model-prices.yaml"):
        if os.path.isfile(p):
            prices_f = p
            break

    ledger = os.path.join(common.runs_dir(run_id), "ledger.yaml")
    if not os.path.isfile(ledger):
        raise FileNotFoundError(ledger)

    entries = [e for e in yaml.safe_load_all(open(ledger, encoding="utf-8")) if e]

    prices: dict = {}
    if prices_f and os.path.isfile(prices_f):
        prices = (yaml.safe_load(open(prices_f, encoding="utf-8")) or {}).get("prices", {}) or {}

    def to_dt(v: object) -> datetime | None:
        if isinstance(v, datetime):
            return v
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except Exception:
            return None

    def dur(sec: float) -> str:
        sec = int(sec or 0)
        h, r = divmod(sec, 3600)
        m, s = divmod(r, 60)
        return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    tot_cred = tot_in = tot_out = tot_sec = 0.0
    est_cred = 0.0
    unmeasured_cost = 0   # uzly bez měřené ceny i bez odhadu (= neměřeno, ne „zdarma")
    unmeasured_time = 0   # uzly bez měřeného času (seconds==0 a žádné started/ended)
    starts, ends = [], []
    per_model: dict = {}
    loops: dict = {}
    rows = []

    for e in entries:
        cost = e.get("cost") or {}
        t = e.get("time") or {}
        model = cost.get("model") or "-"
        cin = int(cost.get("input_tokens") or 0)
        cout = int(cost.get("output_tokens") or 0)
        cred = float(cost.get("credits") or 0)
        sec = int(t.get("seconds") or 0)
        tot_in += cin
        tot_out += cout
        tot_cred += cred
        tot_sec += sec
        pr = prices.get(model)
        node_est = (cin / 1e6 * pr["input"] + cout / 1e6 * pr["output"]) if pr else 0.0
        est_cred += node_est
        # Priorita měřeno > odhad > neměřeno: má uzel JAKOUKOLI cenovou stopu (kredity
        # nebo aspoň tokeny pro odhad)? Pokud ne → neměřeno (NEpočítá se jako falešná úspora).
        if cred <= 0 and cin <= 0 and cout <= 0:
            unmeasured_cost += 1
        s, en = to_dt(t.get("started")), to_dt(t.get("ended"))
        if s:
            starts.append(s)
        if en:
            ends.append(en)
        if sec <= 0 and not (s and en):
            unmeasured_time += 1
        pm = per_model.setdefault(model, [0, 0, 0, 0.0])
        pm[0] += 1
        pm[1] += cin
        pm[2] += cout
        pm[3] += cred
        if e.get("outcome") == "FAIL" and e.get("returns_to"):
            k = f"{e['node']}->{e['returns_to']}"
            loops[k] = loops.get(k, 0) + 1
        rows.append((e.get("node", "-"), e.get("agent", "-"), model, e.get("outcome", "-"), sec, cred, node_est))

    n_entries = len(entries)
    wall = int((max(ends) - min(starts)).total_seconds()) if starts and ends else 0
    last_outcome = entries[-1].get("outcome") if entries else "-"

    L = []
    L.append(f"# Run summary — {run_id}\n")
    L.append(f"uzlů: {len(entries)}   poslední outcome: {last_outcome}\n")
    L.append("## Čas")
    L.append(f"- wall-clock: {dur(wall)} (min started → max ended)")
    L.append(f"- compute (Σ uzly): {dur(tot_sec)}")
    if unmeasured_time:
        L.append(f"- ⚠ neměřeno: {unmeasured_time}/{n_entries} uzlů bez naměřeného času "
                 f"(telemetrie chyběla — NEzapočítáno, ne „0 s práce\")")
    L.append("")
    L.append("## Cost")
    # Honest priorita: měřené kredity > odhad z ceníku > neměřeno. Když nic z toho,
    # NEhlásit falešnou nulu jako úsporu — explicitně označit „neměřeno".
    if tot_cred > 0:
        L.append(f"- kredity (měřené): {tot_cred:.2f}")
    elif prices and est_cred > 0:
        L.append("- kredity (měřené): neměřeno — žádný uzel nenese cost.credits")
    else:
        L.append("- kredity: neměřeno (chybí telemetrie i podklad pro odhad)")
    if prices and est_cred > 0:
        L.append(f"- kredity (odhad z tokenů, indikativní): {est_cred:.2f}")
    if unmeasured_cost:
        L.append(f"- ⚠ neměřeno: {unmeasured_cost}/{n_entries} uzlů bez ceny i tokenů "
                 f"(NEzapočítáno jako úspora — telemetrie chyběla)")
    L.append(f"- tokeny: in {int(tot_in)} / out {int(tot_out)}\n")
    L.append("## Per model")
    L.append("| model | uzlů | in | out | kredity |")
    L.append("|---|---|---|---|---|")
    for mdl, (n, i, o, c) in sorted(per_model.items()):
        L.append(f"| {mdl} | {n} | {i} | {o} | {c:.2f} |")
    L.append("")
    L.append("## Per uzel")
    L.append("| uzel | agent | model | outcome | čas | kredity |")
    L.append("|---|---|---|---|---|---|")
    for node, agent, mdl, oc, sec, cred, est in rows:
        if cred:
            cval = f"{cred:.2f}"
        elif est:
            cval = f"~{est:.2f}"
        else:
            cval = "0.00"
        L.append(f"| {node} | {agent} | {mdl} | {oc} | {dur(sec)} | {cval} |")
    if loops:
        L.append("\n## Return loops")
        for k, v in sorted(loops.items()):
            flag = " ⚠ BLOCKER (3×)" if v >= 3 else ""
            L.append(f"- {k}: {v}{flag}")

    return "\n".join(L) + "\n"


def write_summary(run_id: str, text: str) -> str:
    """Atomicky zapiš summary.md do runs/<run_id>/ (tmp + os.replace). Vrať cestu."""
    summary = os.path.join(common.runs_dir(run_id), "summary.md")
    tmp = summary + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, summary)
    return summary


def generate_summary(run_id: str | None = None, write: bool = True) -> str | None:
    """Vygeneruj (a volitelně zapiš) summary.md pro vlnu. Volatelné z terminálu (drive).

    FAIL-SOFT: chybí run-id / chybí ledger → vrať None (NEvyhazuje). Terminál tak nikdy
    nespadne kvůli summary; CLI main() si fail-hard řeší sám přes exit kódy."""
    run_id = _resolve_run_id(run_id or "")
    if not run_id:
        return None
    try:
        text = render_summary(run_id)
    except FileNotFoundError:
        return None
    if write:
        write_summary(run_id, text)
    return text


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("run_id", nargs="?", default="")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)

    run_id = _resolve_run_id(args.run_id or "")
    if not run_id:
        print("CHYBA: nezadán run-id a current-run.md neudává run.", file=sys.stderr)
        sys.exit(2)

    try:
        out = render_summary(run_id)
    except FileNotFoundError as e:
        print(f"CHYBA: {e} neexistuje.", file=sys.stderr)
        sys.exit(2)

    print(out)
    if not args.no_write:
        summary = write_summary(run_id, out)
        print(f"→ zapsáno {summary}")


if __name__ == "__main__":
    main()
