#!/usr/bin/env bash
# spec-agnostic-scan.sh — Detekce technických názvů a HTTP kódů ve speckách.
# (Constitution §Spec je stack-, agent- a impl-agnostická: spec popisuje CO a PROČ doménovým
# jazykem pro netechnického PO — ŽÁDNÝ technický název.) Rozšiřuje filozofii find-line-refs.sh.
#
# MECHANISMUS (nástroj dolů): grep nálezů; úsudek (legitimní produktové rozhodnutí typu
# „storage = Postgres, PO rozhodl" vs. únik implementace) řeší allow-list + Sheldon/člověk.
#
# Hledá ve specs/*.md (a .agentic/specs/) tyto kategorie technických názvů:
#   1) Názvy technologií — výchozí seznam + projektový override
#   2) HTTP status kódy v textu (200/201/4xx/5xx) v kontextu HTTP/status/vrací/kód
#   3) API endpointy / cesty — `/api/...` a HTTP slovesa s cestou (`POST /...`, `GET /...`)
#   4) Odkazy na soubory s kódovými/engine příponami v textu (`.sh|.py|.yaml|.yml`)
#   5) Odkazy na soubory `.md` (engine artefakty / rules / stack / contracts / cross-spec)
#      — KROMĚ strukturálně předepsaného `acceptance/<feature>.md` (vyžaduje ústava)
#   6) Modulové reference — `core.<x>` / `core/<x>` / `server.<x>` / `server/<x>`
#   7) Cesty na kontrakty — `contracts/...`
#
# POZOR — doménové pojmy NEPADAJÍ: „stav běhu", „graf flow", „engine", „seznam issues" apod.
# jsou běžná slova bez tečka-přípony / cesty / slovesa-s-cestou → regexy je necílí. Cílem jsou
# technické názvy (cesty, přípony souborů, moduly, endpointy), ne obyčejná doménová slova.
#
# Konfigurace (volitelné, projektové, override výchozího seznamu):
#   <root>/spec-forbidden-terms.txt — termy (regex/řádek) navíc k výchozím
#   <root>/spec-agnostic-allow.txt  — řádky/termy k prominutí (legitimní výjimky)
#   (oba: # komentáře a prázdné řádky se ignorují)
#
# Delta scope (FIX #1): --files FILE omezí sken na PRŮNIK (seznam ∩ vlastní doména = specs/**).
# Pre-existing dluh MIMO delta vlny tak nepadne do nálezů (AC-1/AC-2). Bez --files = full-scan
# (dnešní chování). Skener git NEČTE — delta listy resolvuje preflight.sh (jediný zdroj delta logiky).
#
# Usage: bash scripts/spec-agnostic-scan.sh [--root DIR] [--dir SPECDIR] [--files LISTFILE]
# Exit:  0 = čisto / prázdný delta | 1 = nález (po allow-listu) | 2 = chyba
set -uo pipefail

ROOT="$PWD"; SPECDIR=""; FILES_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --dir) SPECDIR="$2"; shift 2;;
    --files) FILES_LIST="$2"; shift 2;;
    -h|--help) sed -n '2,32p' "$0"; exit 0;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done
cd "$ROOT" || { echo "Root neexistuje: $ROOT" >&2; exit 2; }

# Najdi spec adresáře (víc možných umístění; oba projedeme, pokud existují)
DIRS=()
if [[ -n "$SPECDIR" ]]; then
  DIRS+=("$SPECDIR")
else
  for d in specs .agentic/specs; do [[ -d "$d" ]] && DIRS+=("$d"); done
fi
if [[ ${#DIRS[@]} -eq 0 ]]; then
  echo "spec-agnostic-scan: žádný spec adresář (specs/|.agentic/specs/) — přeskočeno."
  exit 0
fi

# Delta scope: vyfiltruj delta-seznam na .md soubory uvnitř spec adresářů (vlastní doména).
# Prázdný průnik → nic ke skenu → PASS (vlna nezměnila žádný spec).
SCAN_FILES=()
if [[ -n "$FILES_LIST" ]]; then
  if [[ ! -f "$FILES_LIST" ]]; then
    echo "spec-agnostic-scan: --files seznam neexistuje: $FILES_LIST" >&2; exit 2
  fi
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    [[ "$f" == *.md ]] || continue
    for d in "${DIRS[@]}"; do
      if [[ "$f" == "$d/"* ]] && [[ -f "$f" ]]; then SCAN_FILES+=("$f"); break; fi
    done
  done < "$FILES_LIST"
  if [[ ${#SCAN_FILES[@]} -eq 0 ]]; then
    echo "spec-agnostic-scan: delta scope prázdný — žádný změněný spec (specs/**) v této vlně, nic ke skenu."
    exit 0
  fi
fi

# Výchozí zakázané termy (stack-specifické názvy). Projektový soubor je rozšiřuje.
DEFAULT_TERMS='FastAPI|SolidJS|React|Vue|Angular|Postgres|PostgreSQL|asyncpg|SQLAlchemy|Alembic|aiosqlite|SQLite|pydantic|uvicorn|Flask|Django|Express|Next\.js|Tailwind|Redis|MongoDB|Kafka|gRPC'
TERMS="$DEFAULT_TERMS"
EXTRA="$ROOT/spec-forbidden-terms.txt"
if [[ -f "$EXTRA" ]]; then
  while IFS= read -r t; do
    [[ -z "$t" || "$t" =~ ^[[:space:]]*# ]] && continue
    TERMS="$TERMS|$t"
  done < "$EXTRA"
fi

# HTTP status kód v kontextu (vyhne se náhodným číslům typu „2026" nebo „200 znaků")
P_HTTP='(HTTP|status|stavov|vrací|odpovídá|návratov|kód)[^.]{0,30}\b(100|101|2[0-9][0-9]|3[0-9][0-9]|4[0-9][0-9]|5[0-9][0-9])\b'

# (3) API endpointy / cesty: HTTP sloveso následované cestou, nebo `/api/...`.
#     Sloveso musí stát na hranici slova (ne uvnitř jiného slova), cesta začíná písmenem/`{`.
P_ENDPOINT='(^|[^A-Za-z])(POST|GET|PUT|DELETE|PATCH|HEAD|OPTIONS)[[:space:]]+/[A-Za-z{]|/api/[A-Za-z{]'

# (4) Soubory s kódovou/engine příponou (.sh/.py/.yaml/.yml) — názvy skriptů, modulů, kontraktů,
#     engine artefaktů (run.sh, core/runstate.py, delivery.yaml, interactions.yaml, …).
P_FILEREF='[A-Za-z0-9_-]+(/[A-Za-z0-9_*{}.-]+)*\.(sh|py|yaml|yml)\b'

# (5) Soubory s příponou .md — engine artefakty (current-run.md), rules/stack/contracts/cross-spec
#     odkazy, FEASIBILITY.md atd. Strukturálně předepsaný `acceptance/<feature>.md` (ústava §spec
#     template: „Viz acceptance/<feature>.md") se NEpočítá — odfiltruje se na úrovni tokenu níže.
P_MDREF='[A-Za-z0-9_-]+(/[A-Za-z0-9_*{}.-]+)*\.md\b'
# Strukturální allow (ústavou předepsaný spec→acceptance odkaz). Token-level, ne řádkový —
# řádek smí mít i zakázaný .md token vedle acceptance/ a stále musí padnout.
ALLOW_MD_TOKEN='^[^:]*:[0-9]+:acceptance/[A-Za-z0-9_-]+\.md$'

# (6) Modulové reference: core.<x> / core/<x> / server.<x> / server/<x> (engine moduly, kód).
P_MODULE='(^|[^A-Za-z0-9_])(core|server)[./][A-Za-z_][A-Za-z0-9_.]*'

# (7) Cesty na kontrakty: contracts/... (OpenAPI / contract soubory).
P_CONTRACTS='(^|[^A-Za-z0-9_/-])contracts/[A-Za-z0-9_./-]+'

ALLOW="$ROOT/spec-agnostic-allow.txt"
allow_filter() {
  if [[ -f "$ALLOW" ]]; then
    grep -vEf <(grep -vE '^\s*(#|$)' "$ALLOW") 2>/dev/null || true
  else
    cat
  fi
}

# Sken: skip frontmatter? Specky mívají frontmatter; ponecháme — termy ve frontmatteru
# (např. „stack: …") jsou taky relevantní. grep řádkově.
# sg <extra-flags> <pattern> — grep buď nad delta seznamem souborů (SCAN_FILES), nebo
# rekurzivně nad spec adresáři (full-scan). Logika regexů je IDENTICKÁ — mění se jen scope vstupu.
sg() {
  local flags="$1"; local pat="$2"
  if [[ ${#SCAN_FILES[@]} -gt 0 ]]; then
    grep -EnIH $flags "$pat" "${SCAN_FILES[@]}" 2>/dev/null || true
  else
    grep -rEnIH $flags "$pat" "${DIRS[@]}" --include='*.md' 2>/dev/null || true
  fi
}
raw=$(sg "-i" "$TERMS")
http=$(sg "" "$P_HTTP")
endpoint=$(sg "" "$P_ENDPOINT")
fileref=$(sg "" "$P_FILEREF")
module=$(sg "" "$P_MODULE")
contracts=$(sg "" "$P_CONTRACTS")

# .md odkazy: token-level grep (-o), odfiltruj strukturální acceptance/<feature>.md,
# zbylé tokeny převeď zpět na řádkové hlášení (file:line:<token>).
mdref=$(sg "-o" "$P_MDREF" | grep -vE "$ALLOW_MD_TOKEN" || true)

found=$(printf '%s\n%s\n%s\n%s\n%s\n%s\n%s\n' \
          "$raw" "$http" "$endpoint" "$fileref" "$module" "$contracts" "$mdref" \
          | grep -vE '^$' | sort -u | allow_filter || true)

if [[ -z "$found" ]]; then
  echo "spec-agnostic-scan: čisto (0 technických názvů — stack / HTTP kód / endpoint / soubor / modul / contract — v ${DIRS[*]})."
  exit 0
fi

count=$(echo "$found" | grep -c '' || true)
echo "$found"
echo "---"
echo "spec-agnostic-scan: $count nálezů (po allow-listu) v ${DIRS[*]}."
echo "Legitimní produktová rozhodnutí přidej do spec-agnostic-allow.txt; jinak přeformuluj spec agnosticky." >&2
exit 1
