#!/usr/bin/env bash
# setup-claude-code.sh — Claude Code integrace pro projekt s agentic flow.
#
# Princip (v0.5.0+): .agentic/ je POUZE FRAMEWORK (synced z dream-team).
# Vše projekt-specifické žije v ROOTU projektu:
#   - PROJECT-CONSTITUTION.md  (projektová ústava)
#   - project-config.md        (mapování cest, active agents, framework_version)
#   - specs/ contracts/ rules/ stack/ backlog/ acceptance/ design/
#     improvements/ status/ handoffs/ audit/   (project content + runtime)
#
# Co skript dělá (idempotent):
#   1) .claude/settings.json (pokud chybí)
#   2) .claude/agents/<short>.md wrappery z .agentic/agents/*.md (VŽDY regen)
#   3) Root project dirs + runtime dirs (pokud chybí)
#   4) Root PROJECT-CONSTITUTION.md skeleton z templatu (pokud chybí)
#   5) Root project-config.md skeleton (pokud chybí)
#   6) Root CLAUDE.md tenký adaptér z neutrálního kontraktu (pokud chybí; <Project> auto-fill)
#   7) Session restart reminder
#
# Usage: cd <project-root> && bash .agentic/scripts/setup/setup-claude-code.sh

set -euo pipefail

if [[ ! -d ".agentic" ]]; then
  echo "Adresář .agentic/ neexistuje. Naklonuj nejdřív dream-team:" >&2
  echo "  git clone <repo> .agentic && bash .agentic/scripts/setup/detach-template.sh" >&2
  exit 1
fi
if [[ ! -d ".agentic/agents" ]]; then
  echo "Adresář .agentic/agents/ neexistuje — chybný klon." >&2
  exit 2
fi

PROJECT_NAME=$(basename "$(pwd)")
FRAMEWORK_VERSION=$(cat .agentic/VERSION 2>/dev/null || echo "unknown")
TODAY=$(date +%Y-%m-%d)

mkdir -p .claude .claude/agents

# --- 1) settings.json ---
if [[ -f .claude/settings.json ]]; then
  echo "✓ .claude/settings.json existuje, nepřepisuji."
else
  cat > .claude/settings.json <<'JSON'
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run *)",
      "Bash(pytest *)",
      "Bash(bash .agentic/scripts/*)",
      "Bash(bash .agentic/scripts/**)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)"
    ]
  }
}
JSON
  echo "✓ Vytvořen .claude/settings.json"
fi

# --- 2) .claude/agents/ wrappery (VŽDY regen z .agentic/agents/) ---
echo "→ Generuji Claude Code subagent wrappery..."
python3 - <<'PYEOF'
import os, glob, re
DESCRIPTIONS = {
    "vision-po": "Use when user needs new feature, refinement of acceptance criteria, scope decision, or backlog prioritization. Vision writes specs and acceptance.",
    "tony-cto": "Use for tech-feasibility check of a spec, stack technology choice, cross-target coordination, IMPLEMENTATION priorita.",
    "ted-architect": "Use for API contract design, error code registry, rules/ patterns, reuse decision pass, breaking change migration plan.",
    "chandler-db": "Use for DB schema design, migrations, indexes, query optimization at DB layer.",
    "bob-backend": "Use for backend code implementation (Router/Service/Repository) plus unit testy. Receives spec + Ted decision pass + Chandler migration.",
    "peter-web": "Use for frontend page komponenty, routing, API binding, form handling, plus unit testy. WEB platform.",
    "mob-mobile": "Use for mobile screens (iOS + Android), navigation, lifecycle, deep linking, offline handling, plus unit testy. MOBILE platform.",
    "winny-desktop": "Use for desktop windows, native menu bar, system tray, file system access, IPC, multi-window, plus unit testy. DESKTOP platform.",
    "joey-qa": "Use for integration tests, e2e tests, system tests, regression test plan. Runs after Bob/Peter implementation.",
    "optimus-perf": "Use for performance tests, perf metrics on critical paths, capacity planning. Runs after Joey PASS.",
    "denisa-ux": "Use for UX flow + statický HTML mockup (design-source: author nebo intake). Vyvolán když feature má UI.",
    "leonard-ui": "Use for design manuál (rendered styleguide + tokens) + shared UI komponenty. Vyvolán po Denisa mockupu.",
    "sheldon-spec": "Read-only auditor. Spec consistency, format, brevity (200/400 line limity), spec-contract mapping. Auto-trigger po specs/contracts změně.",
    "heimdall-security": "Read-only auditor. Security audit (F1-F8): secrets leak, crypto, random source, forbidden keys, parametrized queries.",
    "vitek-quality": "Read-only auditor. Code quality: typing, comments WHY, single responsibility, swallowed exceptions, placeholder kód, duplikáty.",
    "edna-design": "Read-only design auditor. Design conformance: implementace vs mockup.html + design/manual/, token usage, vizuální breaky přes screenshot. Jen UI feature.",
    "alfred-devops": "Use for CI/CD pipelines, build, deploy (staging+production), release management, rollback. Runs po T3 gates PASS.",
    "eywa-meta": "Meta-agent. Agent system management: add/modify agent, audit role overlap, write scope conflicts, dispatch graph.",
    "watson-interviewer": "One-time bootstrap. Project setup interview: greenfield nebo transition. Seeduje PROJECT-CONSTITUTION.md + project-config.md. Trigger: chybí project-config.md.",
}
READONLY = {"sheldon-spec", "heimdall-security", "vitek-quality", "edna-design"}
DEFAULT_TOOLS = "Read, Write, Edit, Glob, Grep, Bash"
READONLY_TOOLS = "Read, Glob, Grep, Bash"
n = 0
for f in sorted(glob.glob(".agentic/agents/*.md")):
    base = os.path.basename(f)
    if base == "INDEX.md": continue
    short = base[:-3]
    with open(f, encoding="utf-8") as fh: content = fh.read()
    desc = DESCRIPTIONS.get(short, f"Agent {short}. Viz .agentic/agents/{base}.")
    tools = READONLY_TOOLS if short in READONLY else DEFAULT_TOOLS
    # default model tier z frontmatteru agenta (.agentic/agents/<short>.md §model);
    # chybí-li, řádek vynech (Claude Code použije default). Override per-task řeší
    # orchestrátor dle rubriky složitosti (flow.md §Model routing).
    mm = re.search(r'^model:\s*(\S+)', content, re.M)
    model_line = f"model: {mm.group(1)}\n" if mm else ""
    with open(f".claude/agents/{short}.md", "w", encoding="utf-8") as fh:
        fh.write(f"---\nname: {short}\ndescription: {desc}\ntools: {tools}\n{model_line}---\n\n{content}\n")
    n += 1
    print(f"  ✓ .claude/agents/{short}.md")
print(f"→ Vygenerováno {n} subagent wrapperů.")
PYEOF

# --- 3a) PROJECT.md → STATE.md rename (pokud STATE.md chybí) ---
if [[ -f PROJECT.md && ! -f STATE.md ]]; then
  mv PROJECT.md STATE.md
  echo "✓ PROJECT.md → STATE.md (přejmenováno automaticky)"
elif [[ -f PROJECT.md && -f STATE.md ]]; then
  echo "⚠ Existují oba PROJECT.md i STATE.md. PROJECT.md je redundantní — smaž ručně po ověření obsahu."
fi

# --- 3) Root project dirs + runtime (pokud chybí) ---
created_dirs=""
for d in specs contracts/api contracts/db rules stack backlog acceptance design improvements status handoffs audit runs; do
  if [[ ! -d "$d" ]]; then
    mkdir -p "$d"
    created_dirs="$created_dirs $d"
  fi
done
[[ -n "$created_dirs" ]] && echo "✓ Vytvořené root dirs:$created_dirs" || echo "✓ Root project dirs existují."

# --- 3b) idle current-run.md (engine stav; aby „hej Watsone" + state.sh fungovaly hned) ---
if [[ ! -f current-run.md && -f .agentic/templates/current-run.md ]]; then
  cp .agentic/templates/current-run.md current-run.md
  echo "✓ Seedován current-run.md (idle) z templatu"
fi

# --- 4) Root PROJECT-CONSTITUTION.md (pokud chybí) ---
if [[ -f PROJECT-CONSTITUTION.md ]]; then
  echo "✓ PROJECT-CONSTITUTION.md existuje, nepřepisuji."
elif [[ -f CONSTITUTION.md ]]; then
  echo "⚠ Existuje root CONSTITUTION.md (pravděpodobně stará projektová ústava)."
  echo "  → Watson (transition mód) ji zmigruje do PROJECT-CONSTITUTION.md. Nech to na něm (L3)."
else
  cat > PROJECT-CONSTITUTION.md <<MD
# ${PROJECT_NAME} — Project Constitution

> Projektová ústava (CO projekt je). Doplňuje universal \`.agentic/constitution.md\`
> (JAK agenti fungují). Skeleton — Watson vyplní v interview. Změna = L3.

## Vize a mise
TODO (Watson fáze 1 / Vision)

## Hodnoty
TODO

## Cílová skupina
TODO

## Co projekt JE / NENÍ
TODO

## Nefunkční požadavky (NFR)
TODO (Watson fáze 4 / Tony + Ted)

## Doménová security pravidla
TODO

## Delivery topologie
TODO (Watson fáze 2 / Tony + Ted)
MD
  echo "✓ Vytvořen PROJECT-CONSTITUTION.md skeleton"
fi

# --- 5) Root project-config.md (pokud chybí) ---
if [[ -f project-config.md ]]; then
  echo "✓ project-config.md existuje, nepřepisuji."
else
  cat > project-config.md <<MD
---
cache_key: project-config-${PROJECT_NAME,,}-v1.0
framework_version: "$FRAMEWORK_VERSION"
last_updated: $TODAY
spec_language: cs
code_language: en
status: SKELETON_NEEDS_WATSON
---

# Project Config — $PROJECT_NAME

> Auto-generated skeleton. Spusť Watson pro vyplnění:
> \`Agent(subagent_type="watson-interviewer", prompt="Refinovat project-config interview módem.")\`

## Projekt
\`\`\`yaml
project_name: $PROJECT_NAME
project_type: TODO     # greenfield | transition
vision: TODO
stage: TODO
\`\`\`

## Targets
\`\`\`yaml
active_targets: {}     # TODO: Watson vyplní dle detekovaného stacku
\`\`\`

## Active agents
\`\`\`yaml
# Watson doporučí profil dle složitosti (viz .agentic/agents/INDEX.md
# §Activation profily). Profil = startovní set; vypnutý agent NENÍ smazaný,
# zapne se až ho projekt potřebuje. Default skeleton = standard.
profile: standard            # solo | standard | full
agents:
  vision-po: active
  ted-architect: active
  bob-backend: active
  peter-web: active          # jen pokud web target
  joey-qa: active
  heimdall-security: active
  vitek-quality: active
  sheldon-spec: active
  tony-cto: active
  chandler-db: active        # jen pokud DB
  leonard-ui: active
  alfred-devops: active      # jen pokud deploy
  watson-interviewer: pending
  # off by default ve standard (zapni když projekt potřebuje):
  optimus-perf: inactive
  denisa-ux: inactive
  edna-design: inactive
  eywa-meta: inactive
  mob-mobile: inactive       # jen pokud mobile target
  winny-desktop: inactive    # jen pokud desktop target
\`\`\`

## Fyzické cesty (logical → physical)
\`\`\`yaml
# Default: vše v rootu projektu (NE v .agentic — to je jen framework).
project_constitution: PROJECT-CONSTITUTION.md
specs: specs/
contracts: contracts/
rules: rules/
stack: stack/
backlog: backlog/
acceptance: acceptance/
design: design/
improvements: improvements/
status: status/
handoffs: handoffs/
audit: audit/
project_state: STATE.md
# Watson upraví dle reálné struktury.
\`\`\`
MD
  echo "✓ Vytvořen project-config.md skeleton (root)"
fi

# --- 6) Root CLAUDE.md (pokud chybí; <Project> auto-fill) ---
if [[ -f CLAUDE.md ]]; then
  if grep -q "<Project>" CLAUDE.md 2>/dev/null; then
    sed -i.bak "s/<Project>/$PROJECT_NAME/g" CLAUDE.md && rm -f CLAUDE.md.bak
    echo "✓ CLAUDE.md: <Project> → $PROJECT_NAME"
  else
    echo "✓ CLAUDE.md existuje, nepřepisuji."
  fi
else
  cat > CLAUDE.md <<MD
# ${PROJECT_NAME} — Claude Code adaptér

Tenký tool adaptér nad neutrálním frameworkem v \`.agentic/\` (v$FRAMEWORK_VERSION).
**Orchestrační kontrakt (co dělat) je v \`.agentic/flow.md\` + \`.agentic/constitution.md\`
— ty jsou zdroj pravdy, ne tento soubor.** CLAUDE.md generuje \`setup-claude-code.sh\`;
needituj ho ručně — úpravy logiky patří do neutrálních souborů, sem jen tool-specifika.

## Claude-Code-specifika (jen tohle je navíc oproti neutrálnímu kontraktu)
- Subagent invocation: \`Agent(subagent_type="<short>", model="haiku|sonnet|opus", prompt=...)\`
- Wrappery \`.claude/agents/<short>.md\` (generované; načítají se při STARTU session →
  po setup/sync **RESTART** \`claude\`, jinak subagenti nejsou vidět).
- \`.claude/settings.json\` (permissions).

## TY (main session) jsi ORCHESTRÁTOR, ne agent
Viz \`.agentic/flow.md §Orchestrator vs Subagent split\`. Nikdy nepřebírej identitu
agenta — deleguj přes Agent tool (každý dostane fresh izolovaný kontext). Čti handoffy
v \`handoffs/\`, dispatchuj, schvaluj u gates.

## SESSION START — vždy jako první krok
\`\`\`
Agent(subagent_type="watson-interviewer",
      prompt="Session start. Session-resume dle protokolu (viz agents/watson-interviewer.md §Session resume): run.sh status + STATE.md + framework-sync-log.md + poslední handoff přes pointer handoffs/LATEST (NE podle názvu/data složky); prezentuj stav a navrhni next step.")
\`\`\`
\`status: SKELETON_NEEDS_WATSON\` v \`project-config.md\` → Watson spustí setup interview.

## Načti při startu (neutrální zdroj pravdy)
1. \`.agentic/constitution.md\` — axiomy a hard gates
2. \`.agentic/flow.md\` — dispatch, keyword triggery, model routing, gates, stop body
3. \`.agentic/agents/INDEX.md\` — katalog agentů + dispatch matrix
4. \`project-config.md\` (ROOT) — active agents + cesty
5. \`PROJECT-CONSTITUTION.md\` (ROOT) — projektová ústava (CO projekt je; má přednost; změna = L3)
6. \`STATE.md\` + \`current-run.md\` (ROOT) — stav projektu a běhu (fresh, ne-cached)

## Routing & model (logika je v .agentic/flow.md, ne tady)
Routing a stav počítej scriptem, ne z hlavy (determinismus — viz \`.agentic/flow.md
§Deterministický dispatch\`): \`run.sh status\` (kde stojím) → \`run.sh next --outcome …\`
(další uzel) → dispatch subagenta → \`run.sh done <envelope>\` (/done) → \`run.sh summary\`
(čas+kredity). LLM dodává úsudek a obsah uzlů, ne routing. Model předej Agent toolu
(\`model="haiku|sonnet|opus"\` dle složitosti); bez něj default z \`.claude/agents/<short>.md\`.
\`run.sh\` = \`.agentic/scripts/pipeline/run.sh\`.

## Subagent IDs
vision-po, tony-cto, ted-architect, chandler-db, bob-backend, peter-web,
mob-mobile, winny-desktop, joey-qa, optimus-perf, denisa-ux, leonard-ui,
sheldon-spec, heimdall-security, vitek-quality, edna-design, alfred-devops,
eywa-meta, watson-interviewer
MD
  echo "✓ Vytvořen CLAUDE.md (tenký adaptér) pro '$PROJECT_NAME'"
fi

# --- 7) Restart reminder ---
echo
echo "================================================================"
echo "✅ Setup: $PROJECT_NAME (framework v$FRAMEWORK_VERSION)"
echo "   .agentic/ = framework | root = projekt (PROJECT-CONSTITUTION, project-config, specs/...)"
echo "================================================================"
echo "⚠️  RESTART SESSION: .claude/agents/ se načítá při startu — pokud máš"
echo "    claude otevřené, ZAVŘI a spusť znovu, jinak subagenty nebudou dostupné."
echo
if grep -q "SKELETON_NEEDS_WATSON" project-config.md 2>/dev/null; then
  echo "Další krok: claude → \"Zavolej Watson — dokončit setup\""
fi
