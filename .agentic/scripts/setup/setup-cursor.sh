#!/usr/bin/env bash
# setup-cursor.sh — Nastaví Cursor IDE integraci pro projekt s agentic flow.
#
# Co dělá:
#   1) Ověří přítomnost .agentic/
#   2) Vytvoří `.cursorrules` s references na .agentic/ soubory
#
# Usage:
#   cd <your-project-root>
#   bash .agentic/scripts/setup/setup-cursor.sh

set -euo pipefail

if [[ ! -d ".agentic" ]]; then
  echo "Adresář .agentic/ neexistuje. Naklonuj nejdřív dream-team." >&2
  exit 1
fi

if [[ -f .cursorrules ]]; then
  echo ".cursorrules už existuje, neprepisuji."
  echo "  Doporučení: do .cursorrules přidej tyto reference a Watson session-start ritual:"
  echo "    @.agentic/agents/INDEX.md"
  echo "    @project-config.md"
  echo "    @.agentic/constitution.md"
  echo "    @.agentic/flow.md"
  exit 0
fi

cat > .cursorrules <<'EOF'
# Agentic flow bootstrap — 19 agentů, tool-agnostic.
# Tyto soubory se načtou jako kontext při každé Cursor session.

@.agentic/agents/INDEX.md
@project-config.md
@.agentic/constitution.md
@.agentic/flow.md

# ── SESSION START — VŽDY jako první krok (před přijetím prvního úkolu) ──────
# Proveď Watson session-resume ritual:
# 1. Přečti STATE.md → §Aktuální fokus + §Open Items
# 2. Pokud existuje framework-sync-log.md → přečti poslední záznam;
#    pokud status = PENDING_REVIEW → prezentuj uživateli a nastav REVIEWED
# 3. Najdi poslední handoff: ls -t handoffs/**/*.md 2>/dev/null | head -3
# 4. Přečti poslední handoff (sekce Výsledek + frontmatter to:)
# 5. Prezentuj status report (1 stránka, žádné zbytečné rozvádění)
# 6. Navrhni next step a čekej na uživatele
# Celý ritual viz: .agentic/agents/watson-interviewer.md §Session resume

# ── Keyword triggery ────────────────────────────────────────────────────────
# "handoff" / "zapiš handoff" / "konec session"
#   → watson-interviewer §Handoff mode: zapiš STATE.md + handoffs/<wave>/<from>-to-<next>.md
# "zavolej Watson" / "Watson"
#   → watson-interviewer rituál (detekce stavu projektu)
# nový feature / bug
#   → dispatch vision-po dle .agentic/agents/vision-po.md
# "Eywa" / "přidej agenta"
#   → dispatch eywa-meta dle .agentic/agents/eywa-meta.md

# ── Orchestrátor pravidla ───────────────────────────────────────────────────
# - Nikdy nepřebírej identitu agenta sám
# - Každý agent = izolovaný kontext (agent file jako system prompt)
# - Gates L0–L3 viz .agentic/flow.md; L3 vždy blokuje na uživateli
# - Destruktivní operace vyžadují L3 lidský souhlas
# - Spec nejasnost = STOP; 3 pokusy = BLOCKER + return path
# - Žádné placeholder implementace (TODO: implement later)

# ── Cast (19 agentů) ────────────────────────────────────────────────────────
# Vision (PO), Tony (CTO), Ted (Architect), Chandler (DB), Bob (Backend),
# Peter (Web), Mob (Mobile), Winny (Desktop), Joey (QA), Optimus (Perf),
# Denisa (UX), Leonard (UI), Sheldon (Spec Audit), Heimdall (Security Audit),
# Vitek (Code Quality Audit), Edna (Design Audit), Alfred (DevOps),
# Eywa (Meta-agent), Watson (Setup + Handoff interviewer)
# Plné definice: .agentic/agents/<short>.md
EOF

echo "Vytvořen .cursorrules"
echo "Otevři projekt v Cursor — Watson session-resume ritual proběhne automaticky při první interakci."
