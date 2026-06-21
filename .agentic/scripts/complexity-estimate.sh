#!/usr/bin/env bash
# complexity-estimate.sh — levný odhad tieru složitosti (model-routing prior).
#
# Spočítá signály z daných souborů (nebo z working-tree diffu) a navrhne tier.
# NErozhoduje — dává orchestrátoru/Tonymu levný deterministický prior, který
# pak potvrdí úsudkem (viz flow.md §Model routing).
#
# Usage:
#   bash .agentic/scripts/complexity-estimate.sh [soubor ...]
#   (bez argumentů: vezme `git diff --name-only`)
set -euo pipefail

files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  mapfile -t files < <(git diff --name-only 2>/dev/null || true)
fi

nf=0; loc=0; sensitive=0
sens_re='contracts/|/security|migrations/|/auth|secret'

for f in "${files[@]:-}"; do
  [[ -z "$f" || ! -f "$f" ]] && continue
  nf=$((nf+1))
  l=$(wc -l < "$f" 2>/dev/null || echo 0); loc=$((loc+l))
  if echo "$f" | grep -Eiq "$sens_re"; then sensitive=1; fi
done

if   [[ $sensitive -eq 1 || $nf -gt 6 || $loc -gt 400 ]]; then tier="L";  model="opus (nebo dekompozice na S/M)"
elif [[ $nf -le 1 && $loc -lt 30 ]];                       then tier="XS"; model="haiku"
elif [[ $nf -le 2 && $loc -lt 150 ]];                      then tier="S";  model="sonnet"
else                                                            tier="M";  model="sonnet"
fi

echo "signály: files=$nf loc=$loc sensitive=$sensitive"
echo "→ návrh: tier=$tier  model=$model"
[[ $sensitive -eq 1 ]] && echo "  (dotčeny contracts/security/migrations/auth → nepodstřelovat)"
echo "Prior, ne verdikt — orchestrátor potvrdí dle flow.md §Model routing."
