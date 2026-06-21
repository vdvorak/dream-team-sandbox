#!/usr/bin/env bash
# design-token-scan.sh — deterministická detekce hardcoded barev / px hodnot v UI kódu.
# (Constitution §Filozofie #7 + Determinism checklist: grep-half design-auditu = mechanika
# skriptem, ne oko Edny. Edna bere exit-code/nálezy jako VSTUP a soudí jen hranici tam, kde
# regex nestačí; screenshot-half — kontrast z renderu — zůstává jejím úsudkem, sem nepatří.)
#
# CO HLEDÁ (grep-half, ne render): v UI zdrojácích (*.tsx/*.jsx/*.ts/*.css) přímé hodnoty,
# které mají být design-tokeny (`var(--color-*)`, `var(--space-*)`):
#   1) hex barvy — #rgb / #rrggbb / #rrggbbaa v hodnotách (mimo komentáře/var(...))
#   2) px hodnoty — \d+px (kandidát na --space-* token; 0px / 1px hairline povoleno)
#   3) rgb()/rgba()/hsl() literály v CSS hodnotách
# Allow: hodnoty uvnitř `var(--…)`, tokenové definice v souborech tokens.css (tam barvy SMÍ
# žít — jsou to definice tokenů, ne jejich obcházení), `transparent`/`currentColor`/`inherit`.
#
# DELTA SCOPE (FIX #1, vzor code-lint/format-check): --files FILE omezí sken na PRŮNIK
# (delta ∩ UI zdrojáky). Filtr je PER-SOUBOR (ne per-adresář): nezměněný soubor s pre-existing
# hardcoded barvou NEpadne (app-wide dluh řeší samostatný úklid, ne tahle vlna — AC-1/AC-2).
# Bez --files = full-scan (vědomý samostatný úklid). Skener git NEČTE — delta listy resolvuje
# preflight.sh (jediný vlastník delta logiky).
#
# PER-HUNK SCOPE (FIX N5): --added-lines MAP zúží nález na úroveň ŘÁDKU. MAP je seznam
# `path:lineno` (přidané `+` řádky vlny) a `path:*` (nový soubor = celý je přidaný), který spočítá
# preflight z `git diff --unified=0`. Když je MAP předaná, nález se udrží jen tehdy, leží-li na
# přidaném řádku (nebo v souboru s `path:*`); pre-existing dluh v JINAK dotčeném souboru (vlna
# sáhla na 3 řádky souboru se 41 starými hardcoded px) se NEvynoří jako blocking. Bez --added-lines
# = chování per-SOUBOR (zpětná kompat). Skener git NEČTE — mapu dodá preflight (vlastník delty).
#
# Usage: bash scripts/design-token-scan.sh [--root DIR] [--files LISTFILE] [--added-lines MAP]
# Exit:  0 = čisto / prázdný delta | 1 = nález | 2 = chyba
set -uo pipefail

ROOT="$PWD"; FILES_LIST=""; ADDED_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)        ROOT="$2"; shift 2;;
    --files)       FILES_LIST="$2"; shift 2;;
    --added-lines) ADDED_LIST="$2"; shift 2;;
    -h|--help) sed -n '2,32p' "$0"; exit 0;;
    *) echo "design-token-scan: neznámý argument: $1" >&2; exit 2;;
  esac
done
cd "$ROOT" || { echo "design-token-scan: root neexistuje: $ROOT" >&2; exit 2; }

# Per-hunk mapa (volitelná). Načti do dvou množin: ADDED["path:line"]=1 (konkrétní přidaný řádek)
# a WHOLE["path"]=1 (path:* = nový soubor, celý je přidaný). Filtr aplikujeme až na nálezy.
if [[ -n "$ADDED_LIST" ]]; then
  [[ -f "$ADDED_LIST" ]] || { echo "design-token-scan: --added-lines mapa neexistuje: $ADDED_LIST" >&2; exit 2; }
fi
# in_delta_line <file> <lineno> — vrací 0, leží-li nález na přidaném řádku (nebo path:* / bez mapy).
declare -A _ADDED_SET=(); declare -A _WHOLE_SET=(); _HAVE_MAP=0
if [[ -n "$ADDED_LIST" ]]; then
  _HAVE_MAP=1
  while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    entry="${entry#./}"
    if [[ "$entry" == *":*" ]]; then _WHOLE_SET["${entry%:*}"]=1
    else _ADDED_SET["$entry"]=1; fi
  done < "$ADDED_LIST"
fi
in_delta_line() {
  local f="${1#./}" ln="$2"
  [[ $_HAVE_MAP -eq 0 ]] && return 0          # bez mapy = per-soubor chování (zpětná kompat)
  [[ -n "${_WHOLE_SET[$f]:-}" ]] && return 0  # nový soubor → celý je přidaný
  [[ -n "${_ADDED_SET[$f:$ln]:-}" ]] && return 0
  return 1
}

# UI zdrojáky, které skenujeme (přípony). tokens.css je vyňatý (definice tokenů, ne obcházení).
is_ui_file() {
  local f="$1"
  case "$f" in
    */tokens.css|tokens.css) return 1;;            # definice tokenů — barvy tu SMÍ být
  esac
  case "$f" in
    *.tsx|*.jsx|*.ts|*.css) return 0;;
    *) return 1;;
  esac
}

# Delta scope: bez --files → full-scan (najdi UI soubory v repu); s --files → průnik s deltou.
SCAN_FILES=()
if [[ -n "$FILES_LIST" ]]; then
  [[ -f "$FILES_LIST" ]] || { echo "design-token-scan: --files seznam neexistuje: $FILES_LIST" >&2; exit 2; }
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    f="${f#./}"
    is_ui_file "$f" || continue
    [[ -f "$f" ]] || continue
    SCAN_FILES+=("$f")
  done < "$FILES_LIST"
  if [[ ${#SCAN_FILES[@]} -eq 0 ]]; then
    echo "design-token-scan: delta scope prázdný — žádný změněný UI zdroják (*.tsx/*.css) v této vlně, nic ke skenu."
    exit 0
  fi
else
  # Full-scan: najdi UI zdrojáky (mimo node_modules / build / engine / .claude / dist).
  while IFS= read -r f; do
    f="${f#./}"
    is_ui_file "$f" || continue
    SCAN_FILES+=("$f")
  done < <(find . \
             \( -path '*/node_modules/*' -o -path '*/build/*' -o -path '*/dist/*' \
                -o -path './.agentic/*' -o -path './.claude/*' -o -path '*/.dart_tool/*' \) -prune \
             -o -type f \( -name '*.tsx' -o -name '*.jsx' -o -name '*.ts' -o -name '*.css' \) -print)
  if [[ ${#SCAN_FILES[@]} -eq 0 ]]; then
    echo "design-token-scan: žádný UI zdroják (*.tsx/*.css) v projektu — nic ke skenu."
    exit 0
  fi
fi

# Regexy (per-řádek). Hex barva mimo var()/komentář; px hodnota (>1px, ne 0/1px hairline);
# rgb()/rgba()/hsl() literál. grep -E; allow řešíme post-filtrem.
P_HEX='#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b'
P_PX='(^|[^0-9a-zA-Z_-])([2-9]|[1-9][0-9]+)px\b'
P_FUNC='\b(rgb|rgba|hsl|hsla)\('

# scan_one <pattern> <label> — grep nad SCAN_FILES; vyhoď řádky s var(--…) (token-použití OK),
# čistě komentářové řádky a vyloženě tokenové definice (`--xxx:`). Vypíše file:line:LABEL:obsah.
scan_one() {
  local pat="$1" label="$2"
  grep -EnIH "$pat" "${SCAN_FILES[@]}" 2>/dev/null \
    | grep -vE ':[0-9]+:[[:space:]]*(//|\*|/\*)' \
    | grep -vE 'var\(--' \
    | grep -vE ':[0-9]+:[[:space:]]*--[A-Za-z0-9_-]+:' \
    | sed -E "s/^([^:]+:[0-9]+:)/\1${label}: /" || true
}

hex=$(scan_one "$P_HEX" "HARDCODED_COLOR")
px=$(scan_one "$P_PX" "HARDCODED_PX")
func=$(scan_one "$P_FUNC" "COLOR_FUNC")

raw=$(printf '%s\n%s\n%s\n' "$hex" "$px" "$func" | grep -vE '^[[:space:]]*$' | sort -u || true)

# Per-hunk filtr (FIX N5): drž jen nálezy na řádcích reálně přidaných vlnou (nebo path:* / bez mapy).
# Formát řádku nálezu: file:line:LABEL: obsah → uřízni file (do 1. ':') a line (do 2. ':').
suppressed=0
found=""
if [[ -n "$raw" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local_f="${line%%:*}"; rest="${line#*:}"; local_ln="${rest%%:*}"
    if in_delta_line "$local_f" "$local_ln"; then
      found+="${line}"$'\n'
    else
      suppressed=$((suppressed + 1))
    fi
  done <<< "$raw"
  found="${found%$'\n'}"
fi
[[ $suppressed -gt 0 ]] && echo "design-token-scan: $suppressed pre-existing nález(ů) mimo přidané řádky vlny POTLAČENO (per-hunk scope, N5) → advisory + app-wide cleanup backlog, ne blocking." >&2

if [[ -z "$found" ]]; then
  echo "design-token-scan: čisto (0 hardcoded barev/px na přidaných řádcích vlny; skenováno ${#SCAN_FILES[@]} UI souborů)."
  exit 0
fi

count=$(echo "$found" | grep -c '' || true)
echo "$found"
echo "---"
echo "design-token-scan: $count nálezů (hardcoded barva/px místo design-tokenu) ve ${#SCAN_FILES[@]} skenovaných souborech." >&2
echo "Nahraď literály tokeny (var(--color-*) / var(--space-*)); legitimní výjimky posoudí Edna (grep nestačí na hranici)." >&2
exit 1
