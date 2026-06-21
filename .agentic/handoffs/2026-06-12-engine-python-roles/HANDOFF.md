---
wave: 2026-06-12-engine-python-roles
from: orchestrator (Watson handoff mode)
to: next-session
type: session-handoff
returns_to: null
timestamp: 2026-06-12T12:00:00+02:00
---

# Handoff: engine → Python (core/) + role-typed graf + determinismus dotažen

Velká session. Začalo to dotažením determinismu engine, skončilo to přepsáním enginu
do importovatelného Pythonu a přejmenováním uzlů grafu z osob na role (základ pro
vizuální node-editor z VISION §Most). **Vše zelené, vše pushnuté na `origin/main`.**

## Co session zavezla (commity, chronologicky)

1. **`f9459f4` — incremental-reflow acceptance naostro.** Scoped re-flow ověřen na REÁLNÉM
   grafu (E2E `createdat`): doc-only spec fix re-floutne JEN spec-spine (5 uzlů), kód +
   code-auditoři zůstanou hotoví (dřív forward-closure: 24 uzlů). Reproducer:
   `handoffs/2026-06-12-incremental-reflow/accept-createdat.py`.
2. **`3ba801d` — B2 (`touches_db`).** Feature-level DB flag od `architecture` (Ted): read-only
   feature → `db-schema` uzel (chandler) odpadne, `backend` jde přímo. Zrcadlí B3 (runtime úsudek
   role přebíjí statický graf). Default = `has_db` (fail-safe).
3. **`0dcea63` — F3 (most handoff→envelope).** `result.py` auto-derivuje output typy/agent/phase
   z grafu → orchestrátor je nemapuje ručně (divergence-zdroj). Minimal envelope = `{run,node,outcome}`.
   `time` volitelné (→ seconds=0). Konec posledního resolve-vs-apply švu.
4. **`a9c108d` — create-project.sh.** Bootstrap nového projektu jedním příkazem
   (`create-project NÁZEV --claude`): klon dream-team jako `.agentic/` + detach + IDE adaptér +
   initial commit. Pak `cd && claude` + „Chci založit projekt" (Watson init).
5. **`863d716`+`e689a9a`+`e448179` — bash→python refactor.** Engine logika (~85 % byla Python
   uvězněný v bash-heredocích, s duplikací) vytažena do **`scripts/pipeline/core/*.py`** (13 modulů
   + `common.py` = sdílené jádro). `.sh` = 3-řádkové shimy (dokumentované rozhraní beze změny).
   `run.py drive` importuje `frontier` přímo (konec subprocess+JSON). `agentic-sync.sh` rozesílá
   `core/*.py`. Arch: `scripts/pipeline/core/README.md`.
6. **`d8bb945` — design_source politika.** `design-source` gate se ptal „kdo dodá mockup?" u KAŽDÉ
   UI featury a odpověď nic neroutovala (anti-pattern). Nově projektový value-flag
   (`author|intake|derive`, default author), Watson nastaví 1× při initu. Engine routuje:
   author→ux-design, intake→gate(upload)→ux-design, derive→ui-system (UI ze specu). `frontier.py`
   atom/flag_live umí `<flag> == <value>`.
7. **`d08fa2f`+`5c701a8`+`73196cf` — role-typed graf.** Uzly `delivery.yaml` přejmenovány z OSOB
   na ROLE; `agent:` = cast binding. Hrany drátují role → graf modifikovatelný vizuálním editorem.
8. **Eywa (továrna na agenty) aktualizována.** Když uživatel příště požádá o nového agenta, Eywa
   ví, že **uzel = ROLE** (ptá se nejdřív „jakou ROLI/schopnost plní?" → název uzlu, pak „kterou
   personou obsadit?" = cast binding), staví ho jako slepý I/O kontrakt a zapojí roli do grafu
   zvlášť. C7 reference opravena na roli `product`. (`agents/eywa-meta.md`.)

## Orientace pro příští session (CO SE ZMĚNILO STRUKTURÁLNĚ)

- **Engine = Python v `scripts/pipeline/core/`.** `.sh` jsou jen shimy. Logiku uprav v `core/*.py`,
  ne v heredocích (ty už nejsou). `common.py` = sdílené (graf/stav/flagy/outcomes). Importovatelné
  (app vrstva).
- **Uzly grafu = ROLE, ne osoby.** `delivery.yaml`: `product`/`architecture`/`db-schema`/`backend`/
  `ux-design`/`ui-system`/`web`/`mobile`/`desktop`/`qa`/`performance`/`spec-audit`/`security`/
  `code-quality`/`design-audit`/`devops`/`feasibility`/`design-intake`. `agent:` = která persona roli
  plní. Mapování role↔persona: `agents/INDEX.md §Cast`. Persony zůstávají (Vision/Ted/Bob = agenti).
- **design_source = projektová politika** (project-config flag), ne per-feature otázka.
- **Persony v lidských docs** (WORKFLOW.md, OVERVIEW diagram) jsou OK — orientační noty odkazují na
  role-mapping. Stroj/topologie (delivery.yaml, INDEX dispatch) = role.

## Stav

selftest **52/52**, check **C1–C13** OK, createdat reproducer drží. `origin/main` = `73196cf`.
Repo je engine-only (dogfood smazán dřív v session). Determinismus engine: B1/B2/B3/E1/E2/
incremental-reflow/F3 — **kompletní**.

## Otevřené (pro příště)

- **pytest unit-vrstva nad `core/`** — selftest.sh (bash) drží 52 E2E přes shimy; přidat granulární
  pytest přímo na funkce v `core/` (rychlejší, jednotkové). Zapsáno v Open Items.
- **Auth na get-user** (D1) — produktové rozhodnutí (ne engine): `GET /users/{id}` vrací email+role
  bez tokenu. Bearer vs vědomě public. Čeká na člověka.
- **Provider-agnostic executor** — research-only thread (`handoffs/2026-06-12-provider-agnostic-executor/`),
  nesouvisí s tímhle. 4. adaptér vedle claude-code/cursor/aider, 4 otevřená rozhodnutí.
- **Node-editor app** — role-typed graf je teď připravený substrát. Reálná app vrstva (VISION §Most)
  = další velká věc; engine je importovatelný a graf editovatelný.

## Slabé místo

Role-rename selftestu jel přes `sed \b…\b` — ohlídáno proti substringům (`ted`/`bob`/`mob`/`vitek`)
i korupci agent-shortů (`bob-backend`→`backend-backend` chyceno a opraveno), ale je to mechanická
transformace; kdyby něco proklouzlo, projeví se to jako selhání selftestu (drží 52/52, takže OK).
WORKFLOW.md/OVERVIEW persona-diagramy nejsou převedené na role záměrně (lidské explainery) — kdyby
příště vznikl nesoulad mezi personou a rolí v těchto docs, zdroj pravdy je `INDEX.md §Cast` mapping.
