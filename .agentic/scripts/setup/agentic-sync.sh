#!/usr/bin/env bash
# agentic-sync.sh — Selektivní sync frameworku ze zdroje pravdy do projektu s agentic flow.
#
# ZDROJ PRAVDY (2026-06-14, „Forma B" absorpce): framework žije v `dream-team-app/.agentic/`
# (NE už v samostatném `../dream-team` — ten je archivován). Layout `.agentic/` je 1:1 s tím,
# co tento skript od zdroje čeká (constitution.md, agents/, rules/, scripts/, pipeline/), takže
# `--dream-team-path <…>/dream-team-app/.agentic` funguje beze změny. Konzumenti (projekty
# používající engine terminálově) syncují odsud.
#
# Co dělá:
#   1) Compare framework_version (lokál vs dream-team) — pokud match, nic
#   2) Per soubor (template-owned) ukáže diff a zeptá se yes/no
#   3) Aplikuje schválené úpravy
#   4) Po dokončení aktualizuje framework_version v project-config.md
#
# Co NIKDY nepřepíše (per-project content, žije v ROOTU, ne v .agentic/):
#   - project-config.md, PROJECT-CONSTITUTION.md (per-project)
#   Pozn.: .agentic/ je v0.5.0+ POUZE framework → celé syncovatelné bez rizika.
#   - CLAUDE.md (per-project bootstrap)
#   - .agentic/stack/, specs/, contracts/, backlog/, improvements/, status/,
#     handoffs/, audit/, acceptance/, design/ (project content)
#   - framework-sync-log.md (per-projekt log, generuje tento script)
#
# Usage:
#   cd <your-project-root>
#   bash .agentic/scripts/setup/agentic-sync.sh [--yes] [--dream-team-path PATH]
#
# Options:
#   --yes              Auto-accept všechny změny (batch mode, riskuje override)
#   --dream-team-path  Path ke zdroji frameworku (default auto-detekce:
#                      ~/dev/AI/dream-team-app/.agentic, pak legacy ~/dev/dream-team)

set -euo pipefail

# Parse args
AUTO_YES=0
DREAM_TEAM_PATH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) AUTO_YES=1; shift ;;
    --dream-team-path) DREAM_TEAM_PATH="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Detect framework source (Forma B: dream-team-app/.agentic je zdroj pravdy;
# legacy ~/dev/dream-team ponecháno jako fallback pro nesmigrované checkouty).
if [[ -z "$DREAM_TEAM_PATH" ]]; then
  for cand in "$HOME/dev/AI/dream-team-app/.agentic" "$HOME/dev/dream-team-app/.agentic" \
              "$HOME/dev/dream-team" "$HOME/dev/AI/dream-team" "../dream-team"; do
    if [[ -d "$cand" ]] && [[ -f "$cand/constitution.md" ]]; then
      DREAM_TEAM_PATH="$cand"
      break
    fi
  done
fi

if [[ -z "$DREAM_TEAM_PATH" ]] || [[ ! -f "$DREAM_TEAM_PATH/constitution.md" ]]; then
  echo "Zdroj frameworku nenalezen." >&2
  echo "Použij: --dream-team-path <…>/dream-team-app/.agentic" >&2
  exit 1
fi

if [[ ! -d ".agentic" ]]; then
  echo "Tento adresář nemá .agentic/ — nic k synchronizaci." >&2
  exit 1
fi

# Pojistka proti self-syncu: pokud je zdroj uvnitř TOHOTO projektu (= jsem repo zdroje pravdy),
# nemám kam syncovat. Framework se tu edituje in-place, ne přes sync.
SRC_ABS="$(cd "$DREAM_TEAM_PATH" 2>/dev/null && pwd -P || echo "")"
HERE_ABS="$(pwd -P)"
if [[ -n "$SRC_ABS" ]] && [[ "$SRC_ABS" == "$HERE_ABS"/* || "$SRC_ABS" == "$HERE_ABS" ]]; then
  echo "Tento repo JE zdroj pravdy frameworku ($DREAM_TEAM_PATH je uvnitř $HERE_ABS)." >&2
  echo "Framework se zde edituje přímo v .agentic/, nesyncuje se do sebe. Nic k udělání." >&2
  exit 0
fi

# Optional: pull latest ve zdroji, pokud je v git repu (zdroj může být podsložka .agentic/ —
# git -C najde enclosing repo, takže testujeme rev-parse, ne přítomnost .git přímo ve zdroji).
if git -C "$DREAM_TEAM_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "→ Zdroj je v git repu, pulluju latest..."
  git -C "$DREAM_TEAM_PATH" pull --rebase 2>&1 | tail -3 || echo "  (pull skipped — možná lokální changes)"
fi

# Version check
# project-config.md je v ROOTU (v0.5.0+). Fallback na .agentic/ (legacy pre-0.5).
if [[ -f project-config.md ]]; then
  PCONFIG="project-config.md"
elif [[ -f .agentic/project-config.md ]]; then
  PCONFIG=".agentic/project-config.md"
  echo "⚠️  project-config.md je v .agentic/ (legacy). Doporučeno přesunout do rootu (v0.5.0)."
else
  PCONFIG="project-config.md"  # neexistuje — setup ho vytvoří
fi
LOCAL_VER=$(grep -E "^framework_version:" "$PCONFIG" 2>/dev/null | sed -E 's/^framework_version:[^0-9]*([0-9][0-9.]*).*/\1/' || echo "unknown")
TEMPLATE_VER=$(cat "$DREAM_TEAM_PATH/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "unknown")

echo
echo "================================================================"
echo "Agentic sync — $PWD"
echo "  Local framework version:    $LOCAL_VER"
echo "  Dream-team current version: $TEMPLATE_VER"
echo "  Dream-team path:            $DREAM_TEAM_PATH"
echo "================================================================"
echo

if [[ "$LOCAL_VER" == "$TEMPLATE_VER" ]] && [[ "$LOCAL_VER" != "unknown" ]]; then
  echo "✓ Verze se shoduje. Spouštím sync přesto (pro případ že template změnil bez bump verze)."
  echo
fi

# Template-owned files (kandidáti na sync)
declare -a TEMPLATE_FILES=(
  "constitution.md:.agentic/constitution.md"
  "flow.md:.agentic/flow.md"
  "USAGE.md:.agentic/USAGE.md"
  "VERSION:.agentic/VERSION"
  "agents/INDEX.md:.agentic/agents/INDEX.md"
  "scripts/README.md:.agentic/scripts/README.md"
)

# Add all agent files dynamically
for src_agent in "$DREAM_TEAM_PATH"/agents/*.md; do
  name=$(basename "$src_agent")
  [[ "$name" == "INDEX.md" ]] && continue
  TEMPLATE_FILES+=("agents/$name:.agentic/agents/$name")
done

# Add universal rules (v0.16.0+, synced to .agentic/rules/)
for src_rule in "$DREAM_TEAM_PATH"/rules/*.md; do
  [[ -e "$src_rule" ]] || continue
  name=$(basename "$src_rule")
  TEMPLATE_FILES+=("rules/$name:.agentic/rules/$name")
done

# Add all templates dynamically (top-level + subdirectories)
for src_tmpl in "$DREAM_TEAM_PATH"/templates/*.md; do
  [[ -e "$src_tmpl" ]] || continue
  name=$(basename "$src_tmpl")
  TEMPLATE_FILES+=("templates/$name:.agentic/templates/$name")
done
# templates subdirectories (rules/, stacks/, constitution-overlays/, …)
while IFS= read -r -d '' src_tmpl_sub; do
  rel="${src_tmpl_sub#$DREAM_TEAM_PATH/}"
  TEMPLATE_FILES+=("$rel:.agentic/$rel")
done < <(find "$DREAM_TEAM_PATH/templates" -mindepth 2 -name "*.md" -print0 2>/dev/null)

# Add all scripts dynamically
for src_script in "$DREAM_TEAM_PATH"/scripts/*.sh; do
  name=$(basename "$src_script")
  TEMPLATE_FILES+=("scripts/$name:.agentic/scripts/$name")
done

for src_script in "$DREAM_TEAM_PATH"/scripts/setup/*.sh; do
  name=$(basename "$src_script")
  TEMPLATE_FILES+=("scripts/setup/$name:.agentic/scripts/setup/$name")
done

# Pipeline scripts (v0.19.0+ — state/next/check runner). Shimy (.sh) + core/ python balíček
# (logika; .sh jsou jen tenké shimy na core/*.py — bez core/ by v projektu nefungovaly).
for src_script in "$DREAM_TEAM_PATH"/scripts/pipeline/*.sh; do
  [[ -e "$src_script" ]] || continue
  name=$(basename "$src_script")
  TEMPLATE_FILES+=("scripts/pipeline/$name:.agentic/scripts/pipeline/$name")
done
for src_py in "$DREAM_TEAM_PATH"/scripts/pipeline/core/*.py; do
  [[ -e "$src_py" ]] || continue
  name=$(basename "$src_py")
  TEMPLATE_FILES+=("scripts/pipeline/core/$name:.agentic/scripts/pipeline/core/$name")
done

# Pipeline graf (v0.19.0+ — delivery.yaml + README; framework-owned, synced)
for src_pl in "$DREAM_TEAM_PATH"/pipeline/*; do
  [[ -f "$src_pl" ]] || continue
  name=$(basename "$src_pl")
  TEMPLATE_FILES+=("pipeline/$name:.agentic/pipeline/$name")
done

# Scaffold manifest (v0.23.0+ — strojový index scaffoldů; .yaml mimo *.md glob)
for src_mf in "$DREAM_TEAM_PATH"/templates/scaffolds/*.yaml; do
  [[ -e "$src_mf" ]] || continue
  name=$(basename "$src_mf")
  TEMPLATE_FILES+=("templates/scaffolds/$name:.agentic/templates/scaffolds/$name")
done

# Stack .yaml registry (v0.30.0+ — recommended-libs; .yaml mimo *.md glob)
for src_sy in "$DREAM_TEAM_PATH"/templates/stacks/*.yaml; do
  [[ -e "$src_sy" ]] || continue
  name=$(basename "$src_sy")
  TEMPLATE_FILES+=("templates/stacks/$name:.agentic/templates/stacks/$name")
done

# Atomický zápis src→dst. mv (rename) nepřepisuje inode běžícího skriptu → opravuje
# --yes self-replacement crash (skript přepsal sám sebe za běhu; bash pak četl z nového
# offsetu → syntax error). Běžící proces drží fd na starém inode, nové bajty jdou jinam.
apply_file() {
  local src="$1" dst="$2" tmp
  mkdir -p "$(dirname "$dst")"
  tmp="$(dirname "$dst")/.$(basename "$dst").synctmp.$$"
  cp "$src" "$tmp"
  [[ "$src" == *.sh ]] && chmod +x "$tmp"
  mv -f "$tmp" "$dst"
}

# Counter
TOTAL=${#TEMPLATE_FILES[@]}
CHANGED=0
SKIPPED=0
NEW=0
declare -a CHANGED_FILES=()

for pair in "${TEMPLATE_FILES[@]}"; do
  src_rel="${pair%%:*}"
  dst_rel="${pair##*:}"
  src="$DREAM_TEAM_PATH/$src_rel"
  dst="$dst_rel"

  if [[ ! -f "$src" ]]; then
    continue
  fi

  if [[ ! -f "$dst" ]]; then
    # New file from template
    if (( AUTO_YES )); then
      apply_file "$src" "$dst"
      echo "✓ NEW $dst (kopírováno)"
      NEW=$((NEW+1))
    else
      echo
      echo "📁 NEW soubor v template: $dst"
      read -p "   Zkopírovat? [Y/n] " -n 1 -r
      echo
      if [[ -z "$REPLY" ]] || [[ "$REPLY" =~ ^[Yy]$ ]]; then
        apply_file "$src" "$dst"
        echo "   ✓ kopírováno"
        NEW=$((NEW+1))
      else
        echo "   ⊘ skipped"
        SKIPPED=$((SKIPPED+1))
      fi
    fi
    continue
  fi

  if cmp -s "$src" "$dst"; then
    # Identical, skip silently
    continue
  fi

  # Diff exists
  if (( AUTO_YES )); then
    apply_file "$src" "$dst"
    echo "✓ UPDATED $dst"
    CHANGED=$((CHANGED+1))
    CHANGED_FILES+=("$src_rel")
  else
    echo
    echo "📝 ZMĚNA v $dst"
    echo "   --- (lokální) | +++ (dream-team)"
    diff -u "$dst" "$src" | head -30
    read -p "   Aplikovat? [Y/n/q] " -n 1 -r
    echo
    if [[ "$REPLY" == "q" ]] || [[ "$REPLY" == "Q" ]]; then
      echo "   Quit"
      break
    fi
    if [[ -z "$REPLY" ]] || [[ "$REPLY" =~ ^[Yy]$ ]]; then
      apply_file "$src" "$dst"
      echo "   ✓ aplikováno"
      CHANGED=$((CHANGED+1))
      CHANGED_FILES+=("$src_rel")
    else
      echo "   ⊘ skipped"
      SKIPPED=$((SKIPPED+1))
    fi
  fi
done

# Update framework_version v project-config.md (root, fallback legacy .agentic/)
if [[ -f "$PCONFIG" ]] && [[ "$TEMPLATE_VER" != "unknown" ]]; then
  if grep -q "^framework_version:" "$PCONFIG"; then
    sed -i.bak -E "s/^framework_version:.*/framework_version: \"$TEMPLATE_VER\"/" "$PCONFIG"
    rm -f "$PCONFIG.bak"
    echo
    echo "✓ Aktualizován framework_version v $PCONFIG na $TEMPLATE_VER"
  elif grep -q "^cache_key:" "$PCONFIG"; then
    sed -i.bak "/^cache_key:/a framework_version: \"$TEMPLATE_VER\"" "$PCONFIG"
    rm -f "$PCONFIG.bak"
    echo
    echo "✓ Přidán framework_version: $TEMPLATE_VER do $PCONFIG (po cache_key)"
  else
    echo
    echo "⚠️  $PCONFIG nemá cache_key ani framework_version — přidej ručně."
  fi
fi

echo
echo "================================================================"
echo "Sync hotov: $NEW nových, $CHANGED upravených, $SKIPPED skipped"
echo "================================================================"
echo
echo "Doporučené další kroky:"
echo "  1. bash .agentic/scripts/setup/setup-claude-code.sh"
echo "     (regeneruje .claude/agents/ wrappery z aktualizovaných agent definic)"
echo "  2. Pokud máš otevřenou Claude Code session, RESTART (claude)"
echo "  3. Watson při příštím session startu prezentuje framework-sync-log.md"

# ── Framework sync log (per-projekt, root, není synced) ─────────────────────
# Zapíše záznam pokud se cokoliv změnilo — Watson čte při session-resume.
SYNC_LOG="framework-sync-log.md"
if (( CHANGED > 0 || NEW > 0 )); then
  if [[ ! -f "$SYNC_LOG" ]]; then
    cat > "$SYNC_LOG" <<'LOGEOF'
# Framework Sync Log

Automaticky generováno `agentic-sync.sh`. Watson čte při session-resume
a prezentuje záznamy se stavem `PENDING_REVIEW`. Po prezentaci Watson
nastaví stav na `REVIEWED`.

Formát záznamu:
  date | from_version→to_version | changed:N new:M | files: ... | PENDING_REVIEW

---
LOGEOF
    echo "✓ Vytvořen framework-sync-log.md"
  fi
  SYNC_DATE="$(date +%Y-%m-%d)"
  FILES_STR="${CHANGED_FILES[*]:-}"
  echo "${SYNC_DATE} | ${LOCAL_VER}→${TEMPLATE_VER} | changed:${CHANGED} new:${NEW} | files: ${FILES_STR} | PENDING_REVIEW" >> "$SYNC_LOG"
  echo "✓ Záznam přidán do framework-sync-log.md (Watson prezentuje při příštím session startu)"
fi
