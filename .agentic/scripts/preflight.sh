#!/usr/bin/env bash
# preflight.sh — agregátor mechanických linterů PŘED úsudkem auditora (constitution
# §Scripted extraction first: mechanika scriptem, ne LLM). Jediný vstupní bod, který rané
# brány grafu volají, aby pustily „celou várku stroje najednou" s jasným exit-code.
#
# TŘI REŽIMY (které lintery běží):
#   --mode spec  — rané SPEC brány (gate uzel spec-gate): čistota/agnostika/line-refs/délka
#                  speců + i18n. Co stroj o specu chytí, než ho čte Sheldon (intrinsic úsudek).
#   --mode code  — lint uzel (gate uzel code-lint) PŘED T3 audity: format/style lint + file-size.
#                  „Linter to chytí, ne oko." Co stroj o kódu chytí, než ho čtou auditoři.
#   --mode audit — T3 audit uzly (design-audit/spec-audit): grep-half design-tokenů (hardcoded
#                  barvy/px) + VYPSÁNÍ delta seznamu, který auditor (Edna/Sheldon) bere jako
#                  SCOPE svého úsudku (screenshot-half kontrastu / spec↔contract mapping).
#                  Skenuje JEN deltu vlny → auditor neskenuje celý projekt okem od nuly (N1).
#
# AGREGACE: pustí každý relevantní linter, posbírá exit-kódy, vytiskne souhrn. Exit:
#   0 = všechny lintery zelené (brána PASS)
#   1 = aspoň jeden BLOCKING linter selhal (brána FAIL → return na vlastníka)
#   2 = chyba spuštění (neznámý režim / chybějící skript)
# ADVISORY lintery (file-size bez --strict, extraction) běh NEshazují — jen reportují.
#
# DELTA SCOPE (FIX #1): preflight je JEDINÝ vlastník delta-resolve logiky. Spočítá množinu souborů,
# které vlna změnila vůči bázi (`wave_base` = git ref při startu vlny), a předá ji skenerům přes
# `--files`. Skenery git NEČTĚOU. Báze: env WAVE_BASE → fallback grep `wave_base:` z current-run.md.
#   delta set = git diff --name-only $BASE  +  git diff --name-only --cached $BASE  +
#               git ls-files --others --exclude-standard   (sort -u)
#   (commit-on-done: během vlny jsou změny NEcommitnuté → bereme working-tree+index+untracked, ne range.)
#   Báze dostupná → DELTA (default). Báze chybí / ne-git / --full-scan → FULL-SCAN (zpětně kompat).
#   Prázdný delta → skenery hlásí „nic ke skenu" → PASS (vlna nezavlekla cizí dluh, AC-1/AC-2).
#
# PER-HUNK SCOPE (FIX N5): pro řádkové kontroly (design-token grep) nestačí per-SOUBOR granularita —
# dotkne-li se vlna souboru s pre-existing dluhem (např. 3 nová pravidla v FlowTab.css se 41 starými
# hardcoded px), per-soubor grep vynoří i staré řádky jako „in-delta" → falešná blokace. Preflight
# proto navíc spočítá ADDED-LINES MAPU (`path:lineno`, jen reálně PŘIDANÉ `+` řádky z
# `git diff --unified=0 $BASE`) a předá ji design-token-scanu přes `--added-lines`. Skener pak nález
# udrží jen na přidaných řádcích; starý dluh v dotčeném souboru = pre-existing (advisory + backlog),
# ne blocking. Skener git stále NEČTE — git parsuje JEN preflight (jediný vlastník delty).
# Untracked (nový) soubor nemá bázi → všechny jeho řádky jsou „přidané" → fallback: bez mapy pro
# ten soubor = celý soubor je in-delta (správně, je nový). format-check zůstává per-SOUBOR (prettier
# formátuje celý soubor — to je v pořádku; token-conformance je řádkový, proto per-hunk jen tam).
#
# Usage: bash .agentic/scripts/preflight.sh --mode spec|code|audit [--root DIR] [--strict]
#             [--delta | --full-scan] [--wave-base SHA]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$PWD"; MODE=""; STRICT=0; SCOPE="auto"; WAVE_BASE_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)      MODE="$2"; shift 2;;
    --root)      ROOT="$2"; shift 2;;
    --strict)    STRICT=1; shift;;
    --delta)     SCOPE="delta"; shift;;
    --full-scan) SCOPE="full"; shift;;
    --wave-base) WAVE_BASE_ARG="$2"; shift 2;;
    -h|--help) sed -n '2,42p' "$0"; exit 0;;
    *) echo "preflight: neznámý argument: $1" >&2; exit 2;;
  esac
done
case "$MODE" in spec|code|audit) ;; *) echo "preflight: --mode spec|code|audit povinný" >&2; exit 2;; esac

# ── delta-resolve: urči bázi vlny a spočítej delta seznam souborů ──────────────
# Priorita báze: --wave-base > env WAVE_BASE > grep `wave_base:` z current-run.md.
WAVE_BASE="${WAVE_BASE_ARG:-${WAVE_BASE:-}}"
if [[ -z "$WAVE_BASE" && -f "$ROOT/current-run.md" ]]; then
  WAVE_BASE="$(grep -m1 -oE '^wave_base:[[:space:]]*[0-9a-fA-F]{7,40}' "$ROOT/current-run.md" \
                 | grep -oE '[0-9a-fA-F]{7,40}$' || true)"
fi
DELTA_FILE=""    # cesta k seznamu změněných souborů (prázdná = full-scan)
ADDED_FILE=""    # cesta k added-lines mapě `path:lineno` / `path:*` (prázdná = bez per-hunk filtru)

# build_added_lines_map <out> — pro každý TRACKED změněný soubor vypíše `path:lineno` za každý
# přidaný (`+`) řádek (z `git diff --unified=0 $BASE`); pro UNTRACKED (nový) soubor `path:*`
# (bez báze → všechny řádky jsou „přidané"). Soubor se samými delecemi nemá žádný `+` řádek →
# není v mapě → jeho (pre-existing) řádky nejsou in-delta. git parsuje JEN tady (vlastník delty).
build_added_lines_map() {
  local out="$1" f
  # 1) tracked změny (working-tree + index) vůči bázi — parsuj hunk headers @@ -a +bStart,bCount @@
  {
    git -C "$ROOT" diff --unified=0 "$WAVE_BASE" 2>/dev/null
    git -C "$ROOT" diff --unified=0 --cached "$WAVE_BASE" 2>/dev/null
  } | awk '
      /^\+\+\+ /        { path=$2; sub(/^b\//,"",path); next }
      /^@@ /            {
        # @@ -oldStart[,oldCount] +newStart[,newCount] @@
        plus=$3; sub(/^\+/,"",plus)
        n=split(plus, a, ","); start=a[1]+0; cnt=(n>1 ? a[2]+0 : 1)
        for (i=0; i<cnt; i++) if (path!="" && path!="/dev/null") print path ":" (start+i)
      }
    ' | sort -u >> "$out"
  # 2) untracked (nové) soubory — nemají bázi → celý soubor je „přidaný"
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    printf '%s:*\n' "$f" >> "$out"
  done < <(git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null)
}

resolve_delta() {
  # full-scan vynucen, nebo není báze, nebo není git → žádný --files (full-scan fallback)
  if [[ "$SCOPE" == "full" ]]; then echo "preflight: scope=full-scan (vynuceno --full-scan)"; return; fi
  if [[ -z "$WAVE_BASE" ]]; then echo "preflight: scope=full-scan (báze wave_base nedostupná → fallback)"; return; fi
  if ! git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    echo "preflight: scope=full-scan (mimo git repo → fallback)"; return
  fi
  if ! git -C "$ROOT" cat-file -e "${WAVE_BASE}^{commit}" 2>/dev/null; then
    echo "preflight: scope=full-scan (wave_base '$WAVE_BASE' není platný commit → fallback)"; return
  fi
  DELTA_FILE="$(mktemp)"
  {
    git -C "$ROOT" diff --name-only "$WAVE_BASE" 2>/dev/null
    git -C "$ROOT" diff --name-only --cached "$WAVE_BASE" 2>/dev/null
    git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null
  } | grep -vE '^[[:space:]]*$' | sort -u > "$DELTA_FILE"
  local n; n=$(grep -c '' "$DELTA_FILE" || echo 0)
  echo "preflight: scope=delta (wave_base=${WAVE_BASE:0:12}, $n změněných souborů vlny)"
  # Per-hunk mapa (jen přidané řádky) — pro řádkové kontroly (design-token).
  ADDED_FILE="$(mktemp)"
  build_added_lines_map "$ADDED_FILE"
  local m; m=$(grep -c '' "$ADDED_FILE" || echo 0)
  echo "preflight: added-lines mapa = $m přidaných řádků (per-hunk scope pro design-token)."
}
resolve_delta
FILES_ARGS=()
[[ -n "$DELTA_FILE" ]] && FILES_ARGS=(--files "$DELTA_FILE")
ADDED_ARGS=()
[[ -n "$ADDED_FILE" ]] && ADDED_ARGS=(--added-lines "$ADDED_FILE")
cleanup() {
  [[ -n "$DELTA_FILE" && -f "$DELTA_FILE" ]] && rm -f "$DELTA_FILE"
  [[ -n "$ADDED_FILE" && -f "$ADDED_FILE" ]] && rm -f "$ADDED_FILE"
}
trap cleanup EXIT

fails=0          # počet BLOCKING linterů, které spadly
ran=0            # počet reálně spuštěných linterů (ne-skip)
summary=""

# run_linter <jmeno> <blocking|advisory> <skript> [args…]
# blocking: nenulový exit zvedne $fails. advisory: jen report.
run_linter() {
  local name="$1" sev="$2" script="$3"; shift 3
  local path="$HERE/$script"
  if [[ ! -x "$path" ]]; then
    echo "preflight: linter '$name' chybí nebo není spustitelný ($path)" >&2
    [[ "$sev" == "blocking" ]] && fails=$((fails + 1))
    return
  fi
  echo "── [$name] ($sev) ─────────────────────────────────"
  if bash "$path" "$@"; then
    summary+=$(printf '  PASS  %-22s %s\n' "$name" "$sev")$'\n'
  else
    local rc=$?
    summary+=$(printf '  FAIL  %-22s %s (exit %d)\n' "$name" "$sev" "$rc")$'\n'
    [[ "$sev" == "blocking" ]] && fails=$((fails + 1))
  fi
  ran=$((ran + 1))
}

echo "preflight: mode=$MODE root=$ROOT strict=$STRICT scope=${SCOPE}${DELTA_FILE:+ (delta)}"

if [[ "$MODE" == "spec" ]]; then
  # Rané spec brány: co stroj chytí o specu, než ho čte Sheldon.
  # spec-agnostic dostane delta seznam (--files); skenuje jen specs/** v deltě (jinak full-scan).
  run_linter spec-agnostic blocking spec-agnostic-scan.sh --root "$ROOT" "${FILES_ARGS[@]}"
  run_linter find-line-refs blocking find-line-refs.sh "$ROOT/specs"
  run_linter i18n-scan      advisory i18n-scan.sh --root "$ROOT"
  # N2 (advisory): raná data-availability — AC jmenuje pole bez krytí v kontraktu/typu.
  # Skript dá PRIOR (kandidáti); Sheldon/Vision soudí hranici (odvozené/přejmenované). NEblokuje.
  run_linter data-availability advisory data-availability-scan.sh --root "$ROOT" "${FILES_ARGS[@]}"
  # spec-length je per-feature (bere argument); preflight ji nechává Sheldonovi přes
  # spec-length.sh <feature> — délka je intrinsic kontrola s prahy WARNING/BLOCKER.
elif [[ "$MODE" == "code" ]]; then
  # Lint uzel PŘED T3 audity: co stroj chytí o kódu, než ho čtou auditoři.
  # format-check + file-size dostanou delta seznam (--files); skenují jen změněné stack soubory.
  run_linter format-check blocking format-check.sh --root "$ROOT" "${FILES_ARGS[@]}"
  if [[ $STRICT -eq 1 ]]; then
    run_linter file-size blocking file-size.sh --root "$ROOT" --strict "${FILES_ARGS[@]}"
  else
    run_linter file-size advisory file-size.sh --root "$ROOT" "${FILES_ARGS[@]}"
  fi
else
  # T3 audit uzly (design-audit/spec-audit): N1 delta-scope. Grep-half design-tokenů běží
  # mechanicky (in-delta hardcoded barva/px = blocking nález vlny). Delta seznam se VYPÍŠE,
  # aby auditor (Edna screenshot-half kontrastu / Sheldon spec↔contract mapping) skenoval
  # JEN deltu vlny — out-of-delta vizuální nález = advisory + app-wide cleanup backlog (agent def).
  run_linter design-token blocking design-token-scan.sh --root "$ROOT" "${FILES_ARGS[@]}" "${ADDED_ARGS[@]}"
  echo "── [audit-delta-scope] (informativní) ──────────────"
  if [[ -n "$DELTA_FILE" && -f "$DELTA_FILE" ]]; then
    echo "Auditor (Edna/Sheldon) skenuje POUZE těchto $(grep -c '' "$DELTA_FILE") změněných souborů vlny:"
    sed 's/^/  · /' "$DELTA_FILE"
    echo "Nálezy mimo tento seznam = pre-existing dluh → advisory + app-wide cleanup backlog, NE blocking return."
  else
    echo "Bez wave_base → full-scan fallback: auditor skenuje celý relevantní scope (zpětná kompat)."
  fi
fi

echo "═══════════════════════════════════════════════════"
printf '%s' "$summary"
echo "preflight[$MODE]: spuštěno=$ran, blocking-fails=$fails"
if [[ $fails -gt 0 ]]; then
  echo "preflight: FAIL — mechanická brána neprošla (return na vlastníka před úsudkem)." >&2
  exit 1
fi
echo "preflight: PASS — mechanika zelená, úsudek (Sheldon/auditoři) může pokračovat."
exit 0
