---
wave: 2026-06-12-provider-agnostic-executor
from: research (claude session, odysseus repo)
to: next-session
type: research-handoff
returns_to: null
---

# Handoff: provider-agnostic code executor (extrakce z Odyssea)

## Cíl

Dát dream-teamu **možnost** spouštět coding agenty proti **jakémukoliv modelu/providerovi**,
ne být závislý na Claude Code jako jediném harnessu. Jde o variabilitu (vlastnost), ne
o závazek používat levné modely. Vzor: jak to má Odysseus.

Stav: **jen výzkum, nic nepostaveno.** Žádné rozhodnutí stavět zatím nepadlo.

## Klíčové zjištění (architektura)

**dream-team = orchestrace + spec vrstva.** `scripts/pipeline/run.sh drive` jen řekne
„DISPATCH node X, agent Bob, model sonnet" — sám **žádné LLM nevolá a kód needituje**.
Řídí pořadí/stav/ledger/handoffy. Reálnou exekuci (dát modelu file/shell tooly + běh smyčky)
dnes deleguje na **externí harness**: Claude Code / Cursor / Aider
(viz `scripts/setup/setup-claude-code.sh`, `setup-cursor.sh`, `setup-aider.sh`).

→ Chybějící díl = **„executor"**: `run_agent(persona_prompt, repo_path, model) → {changes, final_text, tokens}`.
Přesně tohle je Odysseův agent_loop + coding tooly.

**Provider-nezávislost v Odysseu sídlí prakticky v jednom souboru: `src/llm_core.py`.**
- `_detect_provider(url)` (řádek ~426) — podle hostname pozná providera (anthropic, ollama,
  openrouter, groq, copilot, chatgpt-subscription…); **neznámé → OpenAI-compatible default**.
- `llm_call_async(url, model, messages, …)` (řádek ~1334) — podle providera postaví správný
  payload/headers/URL (Anthropic Messages API / Ollama native / OpenAI shape), zavolá,
  a **odpověď znormalizuje zpátky na string**. Volající providera neřeší.
- Má i retry/backoff, dead-host cooldown, fallback dispatch (`llm_call_async_with_fallback`
  ~1317, `stream_llm_with_fallback` ~2098).

Odysseus repo: `/home/vitek/Apps/odysseus`

## Co extrahovat z Odyssea

**A) Provider-nezávislost (jádro vlastnosti):**
- `src/llm_core.py` — adaptér napříč providery (TO je ta vlastnost)
- `src/model_context.py` — context-okna modelů (llm_core na něm visí)
- tenké úložiště endpointů `{base_url, api_key, model}` — Odysseus má DB tabulku
  `ModelEndpoint` (`core/database.py:333`); dream-teamu stačí YAML/dict.

**B) Coding executor (smyčka + tooly):**
- `src/agent_loop.py` — agentní smyčka (tool-call → výsledek → další krok)
- coding tooly: `read_file`, `write_file`, `edit_file` (string-replace + diff),
  `grep`, `glob`, `bash`, `python` (registr v `src/tool_index.py`, popisy ~ř. 70–82)

**C) Volitelné (model optimalizace, není nutné pro provider-nezávislost):**
- `src/context_budget.py` (adaptivní token budget, čistá funkce) + `src/context_compactor.py` (trim)
- `src/endpoint_resolver.py` — role→endpoint + fallback chainy (pokud chceš role jako Odysseus)
- teacher eskalace `src/teacher_escalation.py` — levný→drahý při detekovaném selhání (regex zdarma)

**Co NEbrat:** paměť (ChromaDB), web UI, sessions, email/kalendář.
**RAG tool selection (`tool_index.py`) taky vynech** — pro coding je toolset malý a fixní
(~7 toolů), RAG je overkill; prostě injectni všechny.

## Styčné body k výměně při extrakci (coupling)

Modelová vrstva je čistá. `endpoint_resolver.py` visí na 3 věcech, co vyměníš:
1. `ModelEndpoint` (DB) → tvoje úložiště endpointů
2. `get_setting()` → tvůj config rolí + fallback chainů
3. `owner`/`auth_helpers` → vypustit (single-user) nebo tvoje auth

`llm_core.py` + `model_context.py` + `context_budget.py` jsou skoro standalone
(llm_core má pár `owner`/DB větví, dají se stubnout).

## Plán napojení do dream-teamu

Postavit **4. adaptér** vedle claude-code/cursor/aider:
```
run_agent(persona_prompt, repo_path, model) → {changes, final_text, tokens}
```
- `run.sh drive` místo „otevři Claude Code" zavolá tenhle executor.
- per-node tier z `pipeline/delivery.yaml` (sonnet/opus) → namapovat na role/endpointy.
- token/cost už Odysseus počítá (`agent_loop.py:~1488`) → napojit na `scripts/pipeline/ledger.sh`
  / `status/model-routing-log.md` (formát viz `scripts/model-usage.sh`).
- **subagent izolace zdarma:** každý dispatch = čerstvý agent_loop s prázdnými messages.

## Háček (upřímně)

Kvalita kódu = kvalita modelu. Se slabým/lokálním modelem `edit_file` (přesný string match)
častěji selže a smyčka udělá víc chyb než Claude Code se silným modelem. Executor postavíš
provider-agnostic, ale „programuje dobře s jakýmkoliv modelem" platí jen do té míry, do jaké
ten konkrétní model umí programovat. Vlastnost = volba, ne záruka kvality.

## Otevřené rozhodnutí pro další session

1. Postavit POC executoru (`llm_core` + endpoint store + tenký `run_agent()`), ano/ne?
2. Single-user, nebo zachovat owner/multi-user?
3. Stack executoru: Python (jako Odysseus, přímá kopie) nebo přepis do jiného?
4. Role/tier mapování: převzít Odysseův `endpoint_resolver` (default/utility/task/teacher),
   nebo jednodušší mapa tier→endpoint z `delivery.yaml`?
