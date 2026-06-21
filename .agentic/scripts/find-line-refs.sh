#!/usr/bin/env bash
# find-line-refs.sh — Detekce zakázaných odkazů na čísla řádků v dokumentech
# (Constitution §6: "Žádné odkazy na čísla řádků" — path:NNN, „řádek NNN",
# „line NNN" v persistentních dokumentech).
#
# Usage: scripts/find-line-refs.sh <file-or-dir>
#
# Hledá patterny:
#   - path:NNN          (např. server/main.py:42)
#   - „řádek NNN"       (české)
#   - „line NNN"        (anglické)
#   - „line N-M"        (range)
#
# Output: file:line:match — pokud něco najde
# Exit 0 = clean, exit 1 = violations found
#
# Příklad:
#   scripts/find-line-refs.sh .agentic/specs/
#   scripts/find-line-refs.sh CONSTITUTION.md

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <file-or-dir>" >&2
  exit 2
fi

target="$1"

# Patterny:
# 1) path s příponou + : + číslice: foo.py:42, ../bar.md:1
# 2) "řádek <N>", "line <N>", "line N-M"
pattern='([a-zA-Z_./-]+\.[a-zA-Z]+):[0-9]+|řádek [0-9]+|line [0-9]+(-[0-9]+)?'

if grep -rEn --include='*.md' "$pattern" "$target" 2>/dev/null; then
  echo "---" >&2
  echo "Violations found (Constitution §6: žádné odkazy na čísla řádků)" >&2
  exit 1
fi

exit 0
