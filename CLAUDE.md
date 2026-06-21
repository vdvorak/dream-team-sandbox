# dream-team-sandbox — Claude Code adaptér

Tenký tool adaptér nad neutrálním frameworkem v `.agentic/` (v0.37.0).
**Orchestrační kontrakt (co dělat) je v `.agentic/flow.md` + `.agentic/constitution.md`
— ty jsou zdroj pravdy, ne tento soubor.** CLAUDE.md generuje `setup-claude-code.sh`;
needituj ho ručně — úpravy logiky patří do neutrálních souborů, sem jen tool-specifika.

## Claude-Code-specifika (jen tohle je navíc oproti neutrálnímu kontraktu)
- Subagent invocation: `Agent(subagent_type="<short>", model="haiku|sonnet|opus", prompt=...)`
- Wrappery `.claude/agents/<short>.md` (generované; načítají se při STARTU session →
  po setup/sync **RESTART** `claude`, jinak subagenti nejsou vidět).
- `.claude/settings.json` (permissions).

## TY (main session) jsi ORCHESTRÁTOR, ne agent
Viz `.agentic/flow.md §Orchestrator vs Subagent split`. Nikdy nepřebírej identitu
agenta — deleguj přes Agent tool (každý dostane fresh izolovaný kontext). Čti handoffy
v `handoffs/`, dispatchuj, schvaluj u gates.

## SESSION START — vždy jako první krok
```
Agent(subagent_type="watson-interviewer",
      prompt="Session start. Session-resume dle protokolu (viz agents/watson-interviewer.md §Session resume): run.sh status + STATE.md + framework-sync-log.md + poslední handoff přes pointer handoffs/LATEST (NE podle názvu/data složky); prezentuj stav a navrhni next step.")
```
`status: SKELETON_NEEDS_WATSON` v `project-config.md` → Watson spustí setup interview.

## Načti při startu (neutrální zdroj pravdy)
1. `.agentic/constitution.md` — axiomy a hard gates
2. `.agentic/flow.md` — dispatch, keyword triggery, model routing, gates, stop body
3. `.agentic/agents/INDEX.md` — katalog agentů + dispatch matrix
4. `project-config.md` (ROOT) — active agents + cesty
5. `PROJECT-CONSTITUTION.md` (ROOT) — projektová ústava (CO projekt je; má přednost; změna = L3)
6. `STATE.md` + `current-run.md` (ROOT) — stav projektu a běhu (fresh, ne-cached)

## Routing & model (logika je v .agentic/flow.md, ne tady)
Routing a stav počítej scriptem, ne z hlavy (determinismus — viz `.agentic/flow.md
§Deterministický dispatch`): `run.sh status` (kde stojím) → `run.sh next --outcome …`
(další uzel) → dispatch subagenta → `run.sh done <envelope>` (/done) → `run.sh summary`
(čas+kredity). LLM dodává úsudek a obsah uzlů, ne routing. Model předej Agent toolu
(`model="haiku|sonnet|opus"` dle složitosti); bez něj default z `.claude/agents/<short>.md`.
`run.sh` = `.agentic/scripts/pipeline/run.sh`.

## Subagent IDs
vision-po, tony-cto, ted-architect, chandler-db, bob-backend, peter-web,
mob-mobile, winny-desktop, joey-qa, optimus-perf, denisa-ux, leonard-ui,
sheldon-spec, heimdall-security, vitek-quality, edna-design, alfred-devops,
eywa-meta, watson-interviewer
