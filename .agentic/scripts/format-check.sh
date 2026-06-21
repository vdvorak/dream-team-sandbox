#!/usr/bin/env bash
# format-check.sh — deterministická kontrola formátu + style-lintu per stack.
#
# MECHANISMUS (constitution I4: mechanická konzistence scriptem, ne LLM). Vitek gate
# ji spustí; non-zero = porušení → implementátor pustí `--fix` (taky script). Detekuje
# přítomné stacky a pustí jejich nástroje v CHECK módu:
#   python (ruff) · TS/JS (prettier + eslint) · dart (dart format + analyze) · java (spotless)
#
# Delta scope (FIX #1): --files FILE omezí sken na PRŮNIK (delta ∩ stack zdrojáky). Filtr je
# PER-SOUBOR, ne per-adresář: každé stack větvi předáme přímý seznam změněných souborů (delta
# ∩ stack adresář ∩ relevantní přípony) a nástroj kontroluje JEN je (prettier --check <soubory>,
# eslint <soubory>, ruff check <.py>, dart na cesty, spotless -PspotlessFiles). Stack adresář bez
# změněného souboru se PŘESKOČÍ; nezměněné soubory uvnitř dotčeného adresáře se NESKENUJÍ →
# pre-existing format dluh mimo deltu vlny neblokuje (AC-1/AC-2). Bez --files = full-scan (dnešní
# chování). Logika nástrojů (ruff/prettier/eslint/…) je beze změny — mění se jen scope vstupu.
#
# Usage: bash .agentic/scripts/format-check.sh [--root DIR] [--fix] [--files LISTFILE]
# Exit:  0 = čisto / prázdný delta | 1 = nález | 2 = chyba
set -uo pipefail
ROOT="$PWD"; FIX=0; FILES_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --fix)  FIX=1; shift;;
    --files) FILES_LIST="$2"; shift 2;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done
cd "$ROOT" || exit 2
fails=0
RUFF="ruff"; command -v ruff >/dev/null 2>&1 || RUFF="python3 -m ruff"   # PATH nebo modul

# Delta scope: načti změněné soubory. DELTA=0 (bez --files) → full-scan (dnešní chování).
# DELTA=1 → každá stack větev si vyžádá svůj PER-SOUBOR průnik přes stack_files().
DELTA=0; CHANGED=()
if [[ -n "$FILES_LIST" ]]; then
  [[ -f "$FILES_LIST" ]] || { echo "format-check: --files seznam neexistuje: $FILES_LIST" >&2; exit 2; }
  DELTA=1
  while IFS= read -r f; do [[ -n "$f" ]] && CHANGED+=("$f"); done < "$FILES_LIST"
fi
# stack_files <dir> <ext1> [ext2 …] — vytiskne (jeden path na řádek, RELATIVNĚ k <dir>) změněné
# soubory delty, které leží pod <dir> a mají některou z přípon. Filtr je per-soubor, ne per-adresář:
# nezměněné soubory uvnitř <dir> se nevypíšou → nástroj je nedostane → pre-existing dluh nepadne.
# Cesty jsou relativní k <dir>, protože každá stack větev nástroj pouští z `cd "$d"`.
stack_files() {
  local dir="${1#./}"; shift
  local f rel ext
  for f in "${CHANGED[@]:-}"; do
    [[ -z "$f" ]] && continue
    rel="${f#./}"
    if [[ "$dir" == "." ]]; then :
    elif [[ "$rel" == "$dir/"* ]]; then rel="${rel#"$dir"/}"
    else continue; fi
    for ext in "$@"; do
      # Skip deleted files — they appear in git diff --name-only but don't exist on disk.
      # Passing non-existent paths to linters causes false-positive exit code 2.
      if [[ "$rel" == *".$ext" ]]; then
        [[ -f "${dir:+$dir/}$rel" ]] && { printf '%s\n' "$rel"; break; }
      fi
    done
  done
}

# ── python (ruff) ──
while IFS= read -r d; do
  [[ -n "$d" ]] || continue
  if [[ $DELTA -eq 1 ]]; then
    mapfile -t pf < <(stack_files "$d" py)
    [[ ${#pf[@]} -eq 0 ]] && { echo "[python] $d — mimo delta, přeskočeno"; continue; }
    echo "[python] $d (${#pf[@]} změněných)"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && $RUFF format "${pf[@]}" && $RUFF check --fix "${pf[@]}") || fails=$((fails + 1))
    else (cd "$d" && $RUFF format --check "${pf[@]}" && $RUFF check "${pf[@]}") || fails=$((fails + 1)); fi
  else
    echo "[python] $d"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && $RUFF format . && $RUFF check --fix .) || fails=$((fails + 1))
    else (cd "$d" && $RUFF format --check . && $RUFF check .) || fails=$((fails + 1)); fi
  fi
done < <(find . -name pyproject.toml -not -path '*/node_modules/*' -not -path '*/.venv/*' \
           -not -path './.agentic/*' -not -path './.claude/*' \
           -exec dirname {} \; | sort -u)

# ── TS/JS (prettier + eslint) ──
while IFS= read -r d; do
  [[ -n "$d" ]] || continue
  [[ -f "$d/.prettierrc.json" || -f "$d/eslint.config.mjs" ]] || continue
  if [[ $DELTA -eq 1 ]]; then
    mapfile -t tf < <(stack_files "$d" ts tsx js jsx)
    [[ ${#tf[@]} -eq 0 ]] && { echo "[ts] $d — mimo delta, přeskočeno"; continue; }
    echo "[ts] $d (${#tf[@]} změněných)"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && npx prettier --write "${tf[@]}" && npx eslint "${tf[@]}") || fails=$((fails + 1))
    else (cd "$d" && npx prettier --check "${tf[@]}" && npx eslint "${tf[@]}") || fails=$((fails + 1)); fi
  else
    echo "[ts] $d"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && npx prettier --write "src/**/*.{ts,tsx}" && npx eslint .) || fails=$((fails + 1))
    else (cd "$d" && npx prettier --check "src/**/*.{ts,tsx}" && npx eslint .) || fails=$((fails + 1)); fi
  fi
done < <(find . -name package.json -not -path '*/node_modules/*' \
           -not -path './.agentic/*' -not -path './.claude/*' \
           -exec dirname {} \; | sort -u)

# ── dart/flutter ──
while IFS= read -r d; do
  [[ -n "$d" ]] || continue
  if [[ $DELTA -eq 1 ]]; then
    mapfile -t df < <(stack_files "$d" dart)
    [[ ${#df[@]} -eq 0 ]] && { echo "[dart] $d — mimo delta, přeskočeno"; continue; }
    echo "[dart] $d (${#df[@]} změněných)"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && dart format "${df[@]}") || fails=$((fails + 1))
    else (cd "$d" && dart format --output=none --set-exit-if-changed "${df[@]}" && dart analyze "${df[@]}") || fails=$((fails + 1)); fi
  else
    echo "[dart] $d"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && dart format .) || fails=$((fails + 1))
    else (cd "$d" && dart format --output=none --set-exit-if-changed . && dart analyze) || fails=$((fails + 1)); fi
  fi
done < <(find . -name pubspec.yaml -not -path '*/.dart_tool/*' \
           -not -path './.agentic/*' -not -path './.claude/*' \
           -exec dirname {} \; | sort -u)

# ── java (gradle spotless) ──
while IFS= read -r d; do
  [[ -n "$d" ]] || continue
  [[ -f "$d/gradlew" ]] || continue
  if [[ $DELTA -eq 1 ]]; then
    mapfile -t jf < <(stack_files "$d" java)
    [[ ${#jf[@]} -eq 0 ]] && { echo "[java] $d — mimo delta, přeskočeno"; continue; }
    echo "[java] $d (${#jf[@]} změněných)"
    # spotless -PspotlessFiles bere komma-oddělený seznam regexů matchovaných na absolutní cesty.
    # Každý změněný soubor escapneme (tečka → \.) a anchorujeme koncem řetězce.
    sf=""; for j in "${jf[@]}"; do esc="${j//./\\.}"; sf="${sf:+$sf,}.*${esc}\$"; done
    if [[ $FIX -eq 1 ]]; then (cd "$d" && ./gradlew spotlessApply -q -PspotlessFiles="$sf") || fails=$((fails + 1))
    else (cd "$d" && ./gradlew spotlessCheck -q -PspotlessFiles="$sf") || fails=$((fails + 1)); fi
  else
    echo "[java] $d"
    if [[ $FIX -eq 1 ]]; then (cd "$d" && ./gradlew spotlessApply -q) || fails=$((fails + 1))
    else (cd "$d" && ./gradlew spotlessCheck -q) || fails=$((fails + 1)); fi
  fi
done < <(find . -name build.gradle -not -path '*/build/*' -exec dirname {} \; | sort -u)

echo "format-check: fails=$fails"
[[ $fails -eq 0 ]]
