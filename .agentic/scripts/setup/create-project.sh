#!/usr/bin/env bash
# create-project.sh — bootstrap nového agentic projektu jedním příkazem.
#
# Zřetězí greenfield setup z USAGE §Scénář A: vytvoří adresář + git, naklonuje
# dream-team jako .agentic/, odpojí template historii, nastaví IDE adaptér(y) a
# udělá initial commit. Pak už jen spustíš IDE a řekneš „Chci založit projekt"
# (Watson dokončí obsah — project-config, scaffoldy, Vision).
#
# Usage:
#   create-project <název> [--claude] [--cursor] [--aider] [--into <parent-dir>] [--source <dream-team>]
#
# Příklady:
#   create-project muj-projekt --claude
#   create-project muj-projekt --claude --into ~/dev/AI
#
# Přepínače:
#   --claude|--cursor|--aider   IDE adaptér (lze i víc; default = --claude)
#   --into <dir>                kam projekt založit (default = aktuální adresář)
#   --source <dir>             odkud vzít engine (default = repo, kde leží tento script)
#
# Tip: alias create-project='bash ~/dev/AI/dream-team/scripts/setup/create-project.sh'
#
# Exit: 0 = OK | 2 = chyba vstupu/prostředí

set -euo pipefail

usage() { sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

NAME=""; INTO="$PWD"; SOURCE=""; IDES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude) IDES+=(claude-code); shift;;
    --cursor) IDES+=(cursor); shift;;
    --aider)  IDES+=(aider); shift;;
    --into)   INTO="${2:?--into chce adresář}"; shift 2;;
    --source) SOURCE="${2:?--source chce cestu}"; shift 2;;
    -h|--help) usage; exit 0;;
    --*) echo "Neznámý přepínač: $1" >&2; usage; exit 2;;
    *)   if [[ -z "$NAME" ]]; then NAME="$1"; shift
         else echo "Nečekaný argument: $1" >&2; exit 2; fi;;
  esac
done

[[ -n "$NAME" ]] || { echo "CHYBA: chybí název projektu." >&2; usage; exit 2; }
[[ "$NAME" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "CHYBA: název smí obsahovat jen [A-Za-z0-9._-]." >&2; exit 2; }
[[ ${#IDES[@]} -gt 0 ]] || IDES=(claude-code)   # default

# engine source = repo, kde leží tento script (scripts/setup/ → ../..); lze přebít --source
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SOURCE:-$(cd "$HERE/../.." && pwd)}"
[[ -f "$SOURCE/constitution.md" && -d "$SOURCE/agents" ]] \
  || { echo "CHYBA: '$SOURCE' nevypadá jako dream-team (chybí constitution.md / agents/)." >&2; exit 2; }

INTO="$(cd "$INTO" 2>/dev/null && pwd)" || { echo "CHYBA: parent adresář neexistuje: $INTO" >&2; exit 2; }
TARGET="$INTO/$NAME"
[[ -e "$TARGET" ]] && { echo "CHYBA: cíl už existuje: $TARGET" >&2; exit 2; }

command -v git >/dev/null || { echo "CHYBA: git není v PATH." >&2; exit 2; }

echo "▶ Zakládám '$NAME'"
echo "    cíl:    $TARGET"
echo "    engine: $SOURCE"
echo "    IDE:    ${IDES[*]}"

mkdir -p "$TARGET"; cd "$TARGET"
git init -q

echo "▶ Klonuju engine jako .agentic/ …"
git clone -q "$SOURCE" .agentic

echo "▶ Odpojuju template historii …"
bash .agentic/scripts/setup/detach-template.sh >/dev/null

for ide in "${IDES[@]}"; do
  echo "▶ IDE adaptér: $ide …"
  bash ".agentic/scripts/setup/setup-${ide}.sh" >/dev/null
done

echo "▶ Initial commit …"
git add -A
git commit -qm "agentic: bootstrap z dream-team template (${IDES[*]})" >/dev/null

echo
echo "✅ Hotovo: $TARGET"
echo
echo "Dál:"
echo "    cd $TARGET"
for ide in "${IDES[@]}"; do
  case "$ide" in
    claude-code) echo "    claude       # pak řekni: \"Chci založit projekt\" → Watson tě provede";;
    cursor)      echo "    cursor .     # pak řekni: \"Chci založit projekt\" → Watson tě provede";;
    aider)       echo "    aider        # pak řekni: \"Chci založit projekt\" → Watson tě provede";;
  esac
done
