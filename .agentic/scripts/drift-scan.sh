#!/usr/bin/env bash
# drift-scan.sh — detekce cross-project kontaminace + úniku secrets.
#
# Spouští se z root projektu (kde je .agentic/). MECHANISMUS (nástroj dolů).
# Judgment — co je reálná kontaminace vs historie/persona — dělá Vitek/člověk
# nad výstupem. Vzniklo z drift-align epizody (projekt scaffoldnutý klonem
# sourozence si tahá jeho identitu: PARKER_*, parker-web, parker_test, doménu…).
#
# Co dělá:
#   1) Odvodí "cizí otisky" = jména sourozeneckých projektů (../*) + jejich
#      `domain_keywords:` z project-config.md (pokud deklarované; jinak jen jména).
#   2) Grepne CIZÍ otisky v projektovém obsahu (odděleně .agentic/.claude =
#      framework snapshot → opraví re-sync). Filtruje personu "Peter Parker".
#   3) Grepne tvary live secrets (sk-, GOCSPX-, AWS, Slack, PEM) — jen názvy souborů.
#   4) Exit !=0 při nálezu v projektovém obsahu nebo secrets (gate-friendly).
#
# Usage:
#   bash .agentic/scripts/drift-scan.sh [--projects-dir DIR] [--foreign a,b,c] [--self NAME]

set -uo pipefail

PROJECT_ROOT="$PWD"
SELF="$(basename "$PROJECT_ROOT")"
PROJECTS_DIR="$(cd .. && pwd)"
FOREIGN_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --projects-dir) PROJECTS_DIR="$2"; shift 2 ;;
    --foreign) FOREIGN_OVERRIDE="$2"; shift 2 ;;
    --self) SELF="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── Odvození cizích otisků ─────────────────────────────────────────────────
declare -a FP=()
if [[ -n "$FOREIGN_OVERRIDE" ]]; then
  IFS=',' read -ra FP <<< "$FOREIGN_OVERRIDE"
else
  for d in "$PROJECTS_DIR"/*/; do
    name="$(basename "$d")"
    case "${name,,}" in
      "${SELF,,}"|dream-team|bootstrap) continue ;;   # přeskoč self + framework repa
    esac
    FP+=("$name")
    # domain_keywords z project-config.md (volitelné, degraduje na jen-jména)
    if [[ -f "$d/project-config.md" ]]; then
      kw="$(grep -iE '^domain_keywords:' "$d/project-config.md" 2>/dev/null | sed -E 's/^[^:]*:[[:space:]]*//')"
      if [[ -n "$kw" ]]; then
        IFS=',' read -ra extra <<< "$kw"
        for k in "${extra[@]}"; do
          k="$(echo "$k" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
          [[ -n "$k" ]] && FP+=("$k")
        done
      fi
    fi
  done
fi

if [[ ${#FP[@]} -eq 0 ]]; then
  echo "drift-scan: žádné cizí otisky k hledání (sám v $PROJECTS_DIR?)." >&2
  exit 0
fi

# regex alternation (escapuj regex-meta v otiscích)
PAT="$(printf '%s\n' "${FP[@]}" | sed -E 's/[][(){}.^$*+?\\|]/\\&/g' | paste -sd'|' -)"

EXCL="--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv --exclude-dir=__pycache__ --exclude-dir=dist --exclude-dir=build --exclude-dir=.pytest_cache"

echo "════════════════════════════════════════════════════════"
echo " drift-scan — $SELF"
echo " cizí otisky: ${FP[*]}"
echo "════════════════════════════════════════════════════════"

FOUND=0

# ── 1) Projektový obsah (mimo .agentic/.claude) ────────────────────────────
echo
echo "── Cizí otisky v PROJEKTOVÉM obsahu ──"
proj_hits="$(grep -rniIE "$PAT" "$PROJECT_ROOT" $EXCL \
  --exclude-dir=.agentic --exclude-dir=.claude \
  --exclude-dir=handoffs --exclude-dir=improvements 2>/dev/null | grep -viE 'Peter Parker' || true)"
if [[ -n "$proj_hits" ]]; then
  echo "$proj_hits" | sed "s#^$PROJECT_ROOT/##"
  FOUND=1
else
  echo "  (čisté)"
fi

# ── 2) Framework snapshot (.agentic/.claude) — opraví re-sync ──────────────
echo
echo "── Cizí otisky ve .agentic/.claude (framework — fix re-syncem, většinou persona) ──"
fw_count="$(grep -rniIE "$PAT" "$PROJECT_ROOT/.agentic" "$PROJECT_ROOT/.claude" $EXCL 2>/dev/null \
  | grep -viE 'Peter Parker' | wc -l | tr -d ' ')"
echo "  $fw_count řádků (není blocker — vyřeší agentic-sync z čistého frameworku)"

# ── 3) Tvary live secrets (jen názvy souborů, hodnoty neukazujeme) ─────────
echo
echo "── Možné live secrets (ověř, zda je soubor git-tracked!) ──"
SECRET_PAT='sk-[A-Za-z0-9_-]{20}|GOCSPX-[A-Za-z0-9_-]{6}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
sec_files="$(grep -rlIE "$SECRET_PAT" "$PROJECT_ROOT" $EXCL 2>/dev/null | sed "s#^$PROJECT_ROOT/##" || true)"
if [[ -n "$sec_files" ]]; then
  echo "$sec_files"
  FOUND=1
else
  echo "  (čisté)"
fi

echo
echo "════════════════════════════════════════════════════════"
if [[ $FOUND -ne 0 ]]; then
  echo " ⚠ NÁLEZ — projetí Vitkem/člověkem (kontaminace vs historie/persona/feature)."
  exit 1
fi
echo " ✓ Čisté."
exit 0
