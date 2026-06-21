#!/usr/bin/env bash
# model-usage.sh — skladba modelů + odhad úspory, DERIVOVÁNO Z LEDGERU.
#
# Zdroj pravdy = runs/<run>/ledger.yaml (engine ho plní z každého `done`). Routing
# (wave/agent/model/cost) engine zná deterministicky — NEčte se z ručního logu.
# Jediný úsudkový kousek `tier` (XS/S/M/L) nese envelope (pole `tier:`), zbytek se
# derivuje. Viz flow.md §Model routing a backlog determinism-audit N5.
#
# Usage:
#   bash .agentic/scripts/model-usage.sh [<run-id>]   # default: run z current-run.md
#   bash .agentic/scripts/model-usage.sh --ledger <cesta/ledger.yaml>
#
# Bez argumentu vezme run z current-run.md a dohledá runs/<run>/ledger.yaml.
set -euo pipefail

LEDGER=""
RUN_ID=""
case "${1:-}" in
  --ledger) LEDGER="${2:-}";;
  "") : ;;
  *) RUN_ID="$1";;
esac

# Dohledej ledger: explicitní --ledger > runs/<run-id> > run z current-run.md.
if [[ -z "$LEDGER" ]]; then
  if [[ -z "$RUN_ID" && -f current-run.md ]]; then
    RUN_ID="$(grep -E '^\s*run:' current-run.md | head -1 | sed -E 's/^\s*run:\s*//; s/\s*$//')"
  fi
  if [[ -n "$RUN_ID" ]]; then
    LEDGER="runs/$RUN_ID/ledger.yaml"
  fi
fi

if [[ -z "$LEDGER" || ! -f "$LEDGER" ]]; then
  echo "Ledger nenalezen${LEDGER:+: $LEDGER}."
  echo "Routing se derivuje z runs/<run>/ledger.yaml (engine ho plní z 'done')."
  echo "Spusť aspoň jeden 'done', nebo zadej --ledger <cesta>."
  exit 0
fi

python3 - "$LEDGER" <<'PY'
import sys, yaml
from collections import Counter, defaultdict

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    entries = [e for e in yaml.safe_load_all(fh) if e]

# Jen produkující uzly (mají agenta) — routery/joiny/human-gaty agenta nemají.
rows = [e for e in entries if e.get("agent")]
n = len(rows)

print(f"= Model routing usage ({path}) =")
print(f"dispatchů (uzlů s agentem): {n}")
if n == 0:
    sys.exit(0)

by_model = Counter()
by_tier = Counter()
unknown_tier = 0
weight = {"opus": 15, "sonnet": 3, "haiku": 1}
total_w = 0
weighted_nodes = 0

print("\n-- podle modelu --")
for e in rows:
    model = ((e.get("cost") or {}).get("model")) or "-"
    by_model[model] += 1
    tier = e.get("tier")
    if tier:
        by_tier[str(tier).strip()] += 1
    else:
        unknown_tier += 1
    w = weight.get(model)
    if w is not None:
        total_w += w
        weighted_nodes += 1
for m, c in sorted(by_model.items()):
    print(f"  {m:<8} {c}")

print("\n-- podle tieru (z envelope, ⊙ jediný úsudek) --")
if by_tier:
    for t, c in sorted(by_tier.items()):
        print(f"  {t:<4} {c}")
if unknown_tier:
    print(f"  (bez tier: {unknown_tier} — orchestrátor neuvedl 'tier:' v envelope)")

print("\n-- relativní cena (haiku=1, sonnet=3, opus=15) --")
if weighted_nodes:
    base = weighted_nodes * 15
    saving = 100 - (total_w * 100 / base) if base else 0
    print(f"  ~{total_w} jednotek ({weighted_nodes} uzlů; kdyby vše opus: {base} → úspora ~{saving:.0f}%)")
else:
    print("  neměřeno (žádný uzel nenese známý model v cost.model)")
PY
