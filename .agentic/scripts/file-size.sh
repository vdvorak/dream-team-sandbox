#!/usr/bin/env bash
# file-size.sh — ADVISORY hint na přerostlé zdrojové soubory (signál single-responsibility).
#
# MECHANISMUS (nástroj dolů): počet řádků je jen PRIOR; jestli soubor reálně dělá víc věcí
# posuzuje Vitek/člověk nad výstupem. NEBLOKUJE (exit 0) — ledaže --strict (gate-friendly).
# Bere disciplínu „velký soubor = kandidát na rozdělení" z hlavy a dává ji stroji.
#
# Skenuje zdrojové soubory (py/ts/tsx/js/jsx/dart/java), vynechává testy, generované,
# node_modules/.venv/build/dist a vendorovaný framework snapshot (.agentic/.claude).
#
# Prahy (řádky):  WARN > --warn (default 300) | kandidát-na-split > --max (default 500)
#
# Delta scope (FIX #1): --files FILE omezí sken na PRŮNIK (delta ∩ zdrojáky). Pre-existing
# přerostlé soubory mimo delta vlny tak nepadnou do reportu (AC-1/AC-2). Bez --files = full-scan
# (dnešní chování). Logika prahů je beze změny — mění se jen scope vstupu.
#
# Usage: bash scripts/file-size.sh [--root DIR] [--warn N] [--max N] [--strict] [--files LISTFILE]
# Exit:  0 = vždy (advisory) / prázdný delta | 1 = --strict a existuje soubor > max | 2 = chyba
set -uo pipefail

ROOT="$PWD"; WARN=300; MAX=500; STRICT=0; FILES_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --warn) WARN="$2"; shift 2;;
    --max)  MAX="$2"; shift 2;;
    --strict) STRICT=1; shift;;
    --files) FILES_LIST="$2"; shift 2;;
    -h|--help) sed -n '2,20p' "$0"; exit 0;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done
cd "$ROOT" || { echo "Root neexistuje: $ROOT" >&2; exit 2; }

# Množina zdrojáků, které prahy zvažují (full-scan: find přes repo s vyloučeními).
mapfile -t found_files < <(find . \
  \( -path '*/node_modules/*' -o -path '*/.venv/*' -o -path '*/venv/*' \
     -o -path '*/build/*' -o -path '*/dist/*' -o -path '*/.git/*' \
     -o -path './.agentic/*' -o -path './.claude/*' \
     -o -name '*test*' -o -name '*spec*' -o -name '*.schema.ts' \) -prune -o \
  \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \
     -o -name '*.dart' -o -name '*.java' \) -type f -print 2>/dev/null)

# Delta scope: zúž na PRŮNIK delta-seznamu a kandidátů z find (zachová vyloučení testů/vendoru).
# Prázdný průnik → nic ke skenu → advisory PASS (exit 0).
if [[ -n "$FILES_LIST" ]]; then
  [[ -f "$FILES_LIST" ]] || { echo "file-size: --files seznam neexistuje: $FILES_LIST" >&2; exit 2; }
  declare -A _delta=()
  while IFS= read -r f; do [[ -n "$f" ]] && _delta["${f#./}"]=1; done < "$FILES_LIST"
  files=()
  for f in "${found_files[@]}"; do [[ -n "${_delta["${f#./}"]:-}" ]] && files+=("$f"); done
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "file-size: delta scope prázdný — žádný změněný zdroják v této vlně, nic ke skenu."
    exit 0
  fi
else
  files=("${found_files[@]}")
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "file-size: žádné zdrojové soubory ke skenu."
  exit 0
fi

over_max=0; over_warn=0; report=""
for f in "${files[@]}"; do
  n=$(wc -l < "$f" 2>/dev/null || echo 0)
  if (( n > MAX )); then
    report+=$(printf '%6d  BLOCKER  %s\n' "$n" "$f")$'\n'; over_max=$((over_max+1))
  elif (( n > WARN )); then
    report+=$(printf '%6d  WARN     %s\n' "$n" "$f")$'\n'; over_warn=$((over_warn+1))
  fi
done

if [[ -z "$report" ]]; then
  echo "file-size: čisto (žádný zdrojový soubor > ${WARN} ř)."
  exit 0
fi

# Seřaď sestupně dle počtu řádků
echo "$report" | grep -vE '^$' | sort -rn
echo "---"
echo "file-size: ${over_max}× > ${MAX} ř (kandidát na rozdělení), ${over_warn}× > ${WARN} ř (WARN)."
if [[ $STRICT -eq 1 && $over_max -gt 0 ]]; then exit 1; fi
exit 0
