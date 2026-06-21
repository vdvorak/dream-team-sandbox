#!/usr/bin/env bash
# i18n-scan.sh — Detekce natvrdo psaných UI textů (i18n dluh) ve frontend komponentách.
#
# MECHANISMUS (nástroj dolů): grep kandidátů, úsudek (je to opravdu uživatelský text vs
# technický literál) dělá člověk/Leonard nad výstupem — stejně jako extraction-scan.sh.
# Cíl: vynutit, aby viditelné texty šly přes i18n vrstvu (t()), ne natvrdo v JSX.
#
# Hledá:
#   1) JSX text mezi tagy:  >Nějaký text<   (písmena, ne výraz {…})
#   2) Viditelné atributy:  placeholder|title|alt|aria-label|label="text s písmenem"
# Vynechává: řádky komentářů (* // /*), class=/className=, položky z allow-listu.
#
# Allow-list (volitelný, projektový): <root>/i18n-allow.txt — jeden literál/regex na řádek
# (porovnává se proti CELÉMU řádku nálezu; prázdné řádky a # komentáře ignorovány).
#
# Režim:
#   ADVISORY (default) — i18n scaffold (src/i18n/) NEexistuje → exit 0 + report kandidátů.
#   BLOCKER  — pokud scaffold existuje NEBO --strict → nálezy = exit 1.
#
# Usage: bash scripts/i18n-scan.sh [--root DIR] [--strict]
# Exit:  0 = čisto / advisory | 1 = blocker nález | 2 = chyba
set -uo pipefail

ROOT="$PWD"; STRICT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --strict) STRICT=1; shift;;
    -h|--help) sed -n '2,30p' "$0"; exit 0;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done
cd "$ROOT" || { echo "Root neexistuje: $ROOT" >&2; exit 2; }

# Kde hledat frontend komponenty (víc možných umístění)
SRC=""
for d in clients/web/src web/src src; do
  [[ -d "$d" ]] && { SRC="$d"; break; }
done
if [[ -z "$SRC" ]]; then
  echo "i18n-scan: žádný frontend src adresář (clients/web/src|web/src|src) — přeskočeno."
  exit 0
fi

# i18n scaffold přítomen? → přepni do BLOCKER režimu
if [[ -d "$SRC/i18n" ]] || [[ -f "$SRC/i18n/index.ts" ]]; then STRICT=1; fi

ALLOW="$ROOT/i18n-allow.txt"
allow_filter() {
  if [[ -f "$ALLOW" ]]; then
    grep -vEf <(grep -vE '^\s*(#|$)' "$ALLOW") 2>/dev/null || true
  else
    cat
  fi
}

# Vyfiltruj řádky komentářů (mechanicky). Pozor: vstup je `soubor:řádek:kód`, takže
# komentář se pozná až ZA prefixem `path:NN:`. class=/className= NEfiltrujeme — patterny
# matchují jen text mezi tagy a viditelné atributy, ne hodnoty class (jinak bychom ztratili
# reálné nálezy typu `<div class="…">Backlog is empty</div>`).
strip_noise() { grep -vE '^[^:]*:[0-9]+:[[:space:]]*(\*|//|/\*)'; }

files=$(find "$SRC" \( -name '*.tsx' -o -name '*.jsx' \) -not -path '*/node_modules/*' 2>/dev/null)
[[ -z "$files" ]] && { echo "i18n-scan: žádné .tsx/.jsx v $SRC — přeskočeno."; exit 0; }

# Pattern 1: text mezi tagy >Text< (resp. >Text{ pro text+výraz), obsahuje písmeno, bez <>{}
# uvnitř. Znak před `>` nesmí být `=` — jinak by šipka `() =>` dávala false-positive.
P_TEXT='[^=]>[[:space:]]*[A-Za-zÁ-Žá-ž][^<>{}]*[<{]'
# Pattern 2: viditelné atributy se string literálem obsahujícím písmeno
P_ATTR='(placeholder|title|alt|aria-label|label)=("[^"]*[A-Za-zÁ-Žá-ž][^"]*"|'"'"'[^'"'"']*[A-Za-zÁ-Žá-ž][^'"'"']*'"'"')'

found=$(echo "$files" | xargs grep -EnH "$P_TEXT|$P_ATTR" 2>/dev/null | strip_noise | allow_filter || true)

if [[ -z "$found" ]]; then
  echo "i18n-scan: čisto (0 kandidátů natvrdo psaného textu v $SRC)."
  exit 0
fi

count=$(echo "$found" | grep -c '' || true)
echo "$found"
echo "---"
echo "i18n-scan: $count kandidátů natvrdo psaného UI textu v $SRC."
if [[ $STRICT -eq 1 ]]; then
  echo "Režim BLOCKER (i18n scaffold přítomen nebo --strict): texty patří přes t() do locales/." >&2
  exit 1
else
  echo "Režim ADVISORY (i18n scaffold zatím neexistuje). Po zavedení src/i18n/ → BLOCKER."
  exit 0
fi
