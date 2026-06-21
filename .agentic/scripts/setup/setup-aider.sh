#!/usr/bin/env bash
# setup-aider.sh — Nastaví Aider integraci pro projekt s agentic flow.
#
# Co dělá:
#   1) Ověří přítomnost .agentic/
#   2) Vytvoří `.aider.conf.yml` s read-only références na .agentic/
#
# Aider nemá auto-trigger pro session start — Watson se volá manuálně
# (viz níže). Dispatch agentů probíhá přes --read + --message.
#
# Usage:
#   cd <your-project-root>
#   bash .agentic/scripts/setup/setup-aider.sh

set -euo pipefail

if [[ ! -d ".agentic" ]]; then
  echo "Adresář .agentic/ neexistuje. Naklonuj nejdřív dream-team." >&2
  exit 1
fi

if [[ -f .aider.conf.yml ]]; then
  echo ".aider.conf.yml už existuje, neprepisuji."
  echo "  Doporučení: přidej do 'read' sekce reference na .agentic/:"
  echo "    - .agentic/agents/INDEX.md"
  echo "    - project-config.md"
  echo "    - .agentic/constitution.md"
  echo "    - .agentic/flow.md"
  exit 0
fi

cat > .aider.conf.yml <<'EOF'
# Aider config pro projekt s agentic flow (19 agentů, tool-agnostic).
# Tyto soubory se načtou jako read-only kontext při každé session.

read:
  - .agentic/agents/INDEX.md
  - project-config.md
  - .agentic/constitution.md
  - .agentic/flow.md

# ── SESSION START — spusť jako první krok ────────────────────────────────────
# Aider nemá auto-trigger → Watson session-resume spusť ručně:
#
#   aider --read .agentic/agents/watson-interviewer.md \
#         --message "Session start. Proveď session-resume: přečti STATE.md + framework-sync-log.md (pokud existuje) + poslední handoff. Prezentuj stav projektu a navrhni next step."
#
# ── Handoff (konec session) ───────────────────────────────────────────────────
#   aider --read .agentic/agents/watson-interviewer.md \
#         --message "Handoff mode: zachyť stav session, zapiš STATE.md + handoff dokument."
#
# ── Dispatch agentů ──────────────────────────────────────────────────────────
# Nový feature / spec:
#   aider --read .agentic/agents/vision-po.md --message "Vision: napiš spec pro X"
#
# Backend implementace:
#   aider --read .agentic/agents/bob-backend.md \
#         --message "Bob: implementuj dle spec X + decision pass od Teda"
#
# Obecně: aider --read .agentic/agents/<short>.md --message "<agent>: <task>"
#
# Cast (19 agentů):
# vision-po, tony-cto, ted-architect, chandler-db, bob-backend, peter-web,
# mob-mobile, winny-desktop, joey-qa, optimus-perf, denisa-ux, leonard-ui,
# sheldon-spec, heimdall-security, vitek-quality, edna-design, alfred-devops,
# eywa-meta, watson-interviewer
EOF

echo "Vytvořen .aider.conf.yml"
echo
echo "Session start (Watson orientation — manuálně):"
echo "  aider --read .agentic/agents/watson-interviewer.md \\"
echo "        --message \"Session start. Proveď session-resume.\""
