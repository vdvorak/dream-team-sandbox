#!/usr/bin/env bash
# extraction-scan.sh — ADVISORY detekce opakovaných bloků (candidate auto-detekce, „C").
#
# Doplněk `catalog-conformance.sh`: ten VYNUCUJE známé komponenty (raw varianta = BLOCKER);
# tenhle NAVRHUJE nové. Najde bloky kódu opakované >=N× (copy-paste divů/widgetů/řádků) →
# kandidáti na extrakci do Extraction Candidates (constitution §Reuse §Operační mechanismus).
#
# Stabilita: doslovný match po normalizaci whitespace (žádné fuzzy „podobné" → nízká
# false-positive cena). NEBLOKUJE — jen reportuje (exit 0 vždy). Bere disciplínu „všimnout
# si 3. výskytu" z hlavy a dává ji stroji.
#
# Usage: bash .agentic/scripts/extraction-scan.sh [--root DIR] [--window N] [--min-repeats N]
# Exit:  0 vždy (advisory) | 2 = chyba
set -uo pipefail
ROOT="$PWD"; WINDOW=5; MINREP=3
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --window) WINDOW="$2"; shift 2;;
    --min-repeats) MINREP="$2"; shift 2;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done

ES_ROOT="$ROOT" ES_WINDOW="$WINDOW" ES_MINREP="$MINREP" python3 <<'PY'
import os, re, sys
from collections import defaultdict

root = os.environ["ES_ROOT"]
W = int(os.environ["ES_WINDOW"]); MINREP = int(os.environ["ES_MINREP"])
EXCL = {".agentic", ".claude", "node_modules", "build", "dist", ".git", ".venv", "__pycache__", "generated"}
EXTS = {".tsx", ".ts", ".jsx", ".js", ".dart", ".py", ".java", ".vue", ".svelte"}
# Přeskoč triviální/strukturní řádky (import, komentář, jen závorky/interpunkce).
SKIP = re.compile(r'^\s*(import |from |//|#|/\*|\*/?|[\{\}\(\)\[\];,]+\s*$)')
MINCHARS = 40   # min. významný obsah okna (anti-trivia)

files = []
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d not in EXCL]
    for f in fns:
        if os.path.splitext(f)[1] in EXTS:
            files.append(os.path.join(dp, f))

# Okno = W po sobě jdoucích VÝZNAMNÝCH řádků; klíč = jejich normalizovaný obsah (exact).
buckets = defaultdict(list)   # norm-tuple -> [(file, start_line, preview)]
for f in sorted(files):
    try:
        raw = open(f, encoding="utf-8", errors="ignore").read().splitlines()
    except OSError:
        continue
    sig = [(i + 1, ln.strip()) for i, ln in enumerate(raw) if ln.strip() and not SKIP.match(ln)]
    for j in range(len(sig) - W + 1):
        win = sig[j:j + W]
        norm = tuple(s for _, s in win)
        if sum(len(s) for s in norm) < MINCHARS:
            continue
        buckets[norm].append((os.path.relpath(f, root), win[0][0], norm[0]))

cands = []
for norm, locs in buckets.items():
    uniq = sorted(set(locs))
    if len(uniq) >= MINREP:
        cands.append((len(uniq), uniq))
cands.sort(key=lambda c: -c[0])

print(f"extraction-scan: zdrojů={len(files)}, okno={W} řádků, práh={MINREP}× (advisory)")
if not cands:
    print("  (žádný opakovaný blok ≥ práh — nic k extrakci)"); sys.exit(0)

seen = set(); shown = 0
for cnt, locs in cands:
    sigkey = locs[0][2][:60]          # dedupe překrývajících se oken se stejným začátkem
    if sigkey in seen:
        continue
    seen.add(sigkey); shown += 1
    where = ", ".join(f"{fl}:{ln}" for fl, ln, _ in locs[:6])
    print(f"  [{cnt}×] „{locs[0][2][:70]}…\"  → {where}")
    if shown >= 20:
        print("  … (zkráceno)"); break
print("Návrh: zvaž extrakci opakovaných bloků → zapiš do extraction-candidates.md (constitution §Reuse).")
sys.exit(0)
PY
