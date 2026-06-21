#!/usr/bin/env bash
# rules-section.sh — Extrahuje jednu §sekci z markdown souboru.
#
# Usage: scripts/rules-section.sh <file> <section-name>
#
# Hledá řádek začínající "## <section-name>" (case-insensitive) a tiskne až
# do dalšího "## " nebo do konce souboru. Hodí se pro načtení jen relevantní
# sekce velkého rules/stack souboru místo celého souboru (per Constitution
# §Scripted extraction first).
#
# Příklad:
#   scripts/rules-section.sh rules/backend.md "Validace"
#   scripts/rules-section.sh .agentic/stack/server.md "FormStore"

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <file> <section-name>" >&2
  exit 1
fi

file="$1"
section="$2"

if [[ ! -f "$file" ]]; then
  echo "File not found: $file" >&2
  exit 2
fi

# Najdi sekci (## <section>) až k dalšímu ##
awk -v s="$section" '
  BEGIN { IGNORECASE=1; in_section=0 }
  /^## / {
    if (in_section) { exit }
    # Trim "## " prefix, lowercase compare ignore-case
    hdr = $0
    sub(/^## /, "", hdr)
    if (tolower(hdr) == tolower(s) || index(tolower(hdr), tolower(s)) > 0) {
      in_section=1
      print
      next
    }
  }
  in_section { print }
' "$file"
