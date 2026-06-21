#!/usr/bin/env bash
# detach-template.sh — Po klonu dream-team jako .agentic/ odpojí git historii.
#
# Po `git clone https://github.com/.../dream-team .agentic` má .agentic/ vlastní
# .git pointer. Pokud nechceš mít template repo jako submodule, tento script
# odpojí historii — .agentic/ se stane součástí parent projektu.
#
# Usage:
#   cd <your-project-root>
#   bash .agentic/scripts/setup/detach-template.sh
#
# Po dokončení:
#   - .agentic/.git je smazán
#   - Změny v .agentic/ budou tracked v parent gitu

set -euo pipefail

# Detect .agentic location (current dir? parent?)
if [[ -d ".agentic/.git" ]]; then
  target=".agentic"
elif [[ -d ".git" ]] && [[ -f "constitution.md" ]] && [[ -d "agents" ]]; then
  # Pravděpodobně spuštěno přímo z .agentic/
  target="."
else
  echo "Nelze najít .agentic/.git — jsi v projektu se .agentic/ adresářem?" >&2
  exit 1
fi

if [[ ! -d "${target}/.git" ]]; then
  echo "${target}/.git neexistuje — možná už odpojeno?" >&2
  exit 0
fi

echo "Odpojuju git historii z ${target}/"
rm -rf "${target}/.git"

echo "Hotovo. ${target}/ je teď součástí parent projektu."
echo
echo "Doporučeno:"
echo "  git add ${target}"
echo "  git commit -m \"agentic flow: clone dream-team template\""
