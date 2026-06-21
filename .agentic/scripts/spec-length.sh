#!/usr/bin/env bash
# spec-length.sh — Spočítá řádky spec souboru (bez frontmatter a prázdných řádků na konci).
#
# Usage: scripts/spec-length.sh <feature>
# kde <feature> je název spec souboru bez přípony, nebo absolutní cesta.
#
# Příklad:
#   scripts/spec-length.sh manuscript-export
#   scripts/spec-length.sh ./.agentic/specs/manuscript-export.md
#
# Output: jeden řádek "<count>" (integer)
# Exit codes:
#   0 = OK (limit OK)
#   1 = WARNING (> 200 ř)
#   2 = BLOCKER (> 400 ř)

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <feature-name-or-path>" >&2
  exit 3
fi

input="$1"

# Resolve to file
if [[ -f "$input" ]]; then
  file="$input"
elif [[ -f "specs/${input}.md" ]]; then
  file="specs/${input}.md"
elif [[ -f ".agentic/specs/${input}.md" ]]; then
  file=".agentic/specs/${input}.md"
else
  echo "Spec file not found: $input" >&2
  exit 3
fi

# Strip frontmatter (between two ---), strip trailing blanks
count=$(awk '
  BEGIN { in_fm=0; skip=1 }
  NR==1 && /^---$/ { in_fm=1; next }
  in_fm && /^---$/ { in_fm=0; skip=0; next }
  in_fm { next }
  { print }
' "$file" | sed -e '$a\' | wc -l)

echo "$count"

if (( count > 400 )); then
  exit 2
elif (( count > 200 )); then
  exit 1
else
  exit 0
fi
