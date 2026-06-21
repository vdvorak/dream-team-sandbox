---
cache_key: pipeline-readme-v1.0
type: documentation
last_updated: 2026-06-10
status: F1 — graf autorovaný, runner ho zatím NEvykonává
---

# `pipeline/` — deklarativní stavový graf delivery flow

Strojová podoba flow. `delivery.yaml` zachycuje `flow.md §Tři transformace` +
`agents/INDEX.md §Dispatch matrix` jako uzly a hrany. Architektura a důvody:
`pipeline-architecture.md` (repo root).

> **Status (F1):** graf je autorovaný a 1:1 validovaný proti `flow.md`. **Žádný
> runner ho zatím nevykonává** — zdroj pravdy o flow zůstává `flow.md`. Tohle je
> jeho strojová podoba pro budoucí runner (F3) a node-editor app (F5). Bez změny
> chování dnešní orchestrace.

## Typy uzlů

| `type` | Význam | Výstup |
|---|---|---|
| `agent` | pracovní uzel = subagent invocation | handoff + artefakty |
| `gate` | L1 inter-agent kontrola | `PASS` \| `FAIL` |
| `human-gate` | blokuje běh, čeká na člověka (`level: L2` info \| `L3` souhlas) | rozhodnutí |
| `router` | větví dle predikátu; neprodukuje práci | volba hrany |
| `join` | slučovací bod; pokračuje jen když `requires` všichni `PASS` | — |
| `terminal` | konec běhu | — |

## Pole uzlu

- `agent` — short-id z `agents/INDEX.md` (definice role; uzel ji jen invokuje).
- `phase` — `T1` \| `T2` \| `T3` \| `T3-post`.
- `model` — výchozí **strop** tieru (`agents/INDEX.md §Model strategy`). Orchestrátor
  ho dle `flow.md §Model routing` smí snížit (XS→`haiku`) i zvýšit (záludná→`opus`).
- `inputs` / `outputs` — artefakty (= „minimální vstupní balíček" z `constitution §D3`).
  Ve F1 jsou to neformální názvy, ne striktní schéma; runner je zpřesní v F3.
- `when` — aktivace uzlu (podmíněná účast). Viz §Podmínky.
- `readonly: true` — auditorský uzel (nemá write scope, jen reportuje).
- `failure_limit` — override stropu pokusů (default 3; Optimus 5 — tuning iterativní).

## Pole hrany

- `from` / `to` — node id; `to` smí být **seznam** (fan-out / víc cílů return).
- `when` — predikát, kdy hrana platí (gate výsledek `PASS`/`FAIL`/`APPROVED`,
  nebo project predikát, nebo lidsky čitelná podmínka).
- `kind` — `normal` (default) \| `return` (zpětná hrana, finding/bug) \| `fork`
  (paralelní odbočka) \| `fan-out` (1→N paralelně).
- `counter` — jmenný prostor počítadla pro guarded loop. 3× identická failure
  signature ve stejném counteru = **BLOCKER** (`constitution §Kritická pravidla #2`),
  eskalace o rolí výš.

## Typované I/O — `artifacts.yaml`

`inputs`/`outputs` uzlů nejsou volné názvy, ale **typy** z registru
`pipeline/artifacts.yaml`. Účel: node editor spojí jen kompatibilní I/O (output
type == input type), `check.sh` ověří slovník (C8) a že každý konzumovaný typ někdo
produkuje (C9), a scaffold-passing předává scaffold jako typovaný artefakt.

Pole artefaktu: `kind` (source/spec/flag/design/contract/code/test/report/deploy/meta) ·
`desc` · `external: true` (vzniká mimo graf — tool/uživatel) · `abstract: true` +
`subtypes` (zástupný typ; input uspokojen, produkuje-li se ≥1 subtype — např. `code`
= server/web/mobile/desktop-code). Změna I/O v `delivery.yaml` ⇒ doplnit typ do registru.

## Přechody — node-result obálka („/done" v souboru)

Když uzel dokončí, vyprodukuje **node-result obálku** (`templates/node-result.md`):
outputs (typované) + outcome + gate + **cost + čas**. Zpracuje `scripts/pipeline/result.sh`:
ověří (uzel ∈ graf, outputs.type ∈ artifacts), připíše do `runs/<run>/ledger.yaml`
(append-only multi-doc) a posune `current-run.md` (completed / last_outcome / counters;
FAIL+returns_to → bump, 3× = BLOCKER). Routing dál dělá `next.sh`.

Loop (deterministický, bez ručního přepisování stavu LLM):
`uzel hotov → result.sh <envelope>  (= /done) → stav posunut → next.sh → další uzel`.
V budoucí aplikaci je `result.sh` přesně endpoint `/done`; `runs/<run>/ledger.yaml` je
zdroj pro live view a pro cost+čas účtování.

**Cost + čas per issue** — `scripts/pipeline/ledger.sh [<run>]` agreguje
`runs/<run>/ledger.yaml`: wall-clock + compute čas, kredity, tokeny, rozpad per
model/uzel, return loops; zapíše `runs/<run>/summary.md`. Kredity bere ze
zaznamenaných `cost.credits`; chybí-li, dopočítá odhad z tokenů přes volitelný
(indikativní) `pipeline/model-prices.yaml`. Tohle je odpověď na „jak dlouho to trvalo
a kolik to stálo" — strukturovaná, ze souborů, bez tool-paměti.

## Human-interaction — `interactions.yaml`

`human-gate` uzly blokují běh a čekají na člověka. Každá interakce je typovaně
definovaná v `pipeline/interactions.yaml` (uzel ji referencuje polem `interaction:`):
`prompt` · `kind` (choice / approval / ack / upload / text) · `options` · `produces`
(flag nebo outcome) · `level` (L2/L3) · `blocking`.

Účel: aplikace deterministicky vyrenderuje správný ovládací prvek (kind → UI),
odpověď je typovaná (jasný vstup → jasný výstup), a `current-run.awaiting_human`
+ registr řeknou live-view, na co přesně se čeká. `check.sh §C10` ověří, že každý
human-gate má platnou interakci se známým kind. Odpověď se zaznamená node-result
obálkou (`result.sh`) — člověk je v tu chvíli „uzel".

## Podmínky (`when`) — predikáty

`condition_language: machine` — predikáty `when:` **strojově vyhodnocuje runner**
(`predicate.py`: `PROJ_RE`/`CMP_RE` + flag-atomy) ve F3. Project flagy vychází z `project-config.md`:

| Flag | Zdroj |
|---|---|
| `project.has_server` | aktivní server target |
| `project.has_db` | DB v stacku |
| `project.has_ui` / `spec.has_ui` | UI klient / feature má UI |
| `project.has_deploy` | deploy platforma (ne library) |
| `project.targets.{web,mobile,desktop}` | aktivní klientské targety |

Vypnutý agent (`project-config §active_agents`) = jeho uzel se přeskočí, i když
`when` platí (target-gating, `INDEX.md §Activation profily`).

## Fan-out / join

Po `qa` PASS se rozbíhá 5 auditorů paralelně (`kind: fan-out`). `audit-join`
pokračuje na `l2-review` jen když **všichni z `requires`** vrátí PASS. Auditor
s findingem nejde do join — vrací se vlastníkovi zpětnou hranou (BLOCKER).
`design-audit` je v `requires` jen pro UI feature (jinak se přeskočí).

## Co v grafu NENÍ (vědomě)

- **Watson setup / session-resume a Eywa meta** — mimo standardní delivery flow
  (bootstrap a správa agent-systému, ne výroba feature).
- **Per-todo uzly** — dekompozice (agent z issue udělá plán + work items a deleguje)
  je **výstup uzlu** (artefakt: spec / `work-breakdown.md` / `backlog/`) + dispatch
  implementačních uzlů, ne nové uzly grafu. Todos žijí v `current-run.md`
  (`pending`/`completed`). Víc work items = fan-out (for-each), ne mutace grafu.
  (Viz `pipeline-architecture.md §Feasibility`.)

## Strict spec-driven invariant (vynuceno)

**Celé flow vždy produkuje na základě spec-driven developmentu** (`constitution.md §1`:
spec je source of truth, kód je artefakt). Strukturálně to graf garantuje:

- `product` (spec autorita) **dominuje** všem produkujícím uzlům — z `entry` (intake)
  se k žádnému uzlu produkujícímu kód/kontrakt (agent, phase `T2`/`T3-post`:
  architecture, db-schema, ui-system, backend, web, mobile, desktop, devops, production) **nelze dostat
  bez průchodu product**.
- `intake` proto routuje **feature i improvement** přes product; žádná zkratka do
  architecture/feasibility.
- bugfix s failure-signature vstupuje return mechanikou u vlastníka, ale fix musí
  splnit **existující acceptance** — taky spec-driven.

`scripts/pipeline/check.sh` to vynucuje kontrolou **C7** (odeber product → žádný
producent nesmí být z entry dosažitelný). Porušení = exit 1.

## Validace 1:1 proti flow.md

Graf je odvozenina, ne nová autorita. Integritu hlídá `scripts/pipeline/check.sh`
(C1–C16: parse, dangling refs, join.requires, neznámý agent, dead-end, orphan,
spec-driven invariant, typované I/O slovník + existence producenta, human-gate
interakce, dataflow, flow-blind agenti, řízené slovníky, a **C16 próza↔graf most**
— brány slíbené ve `flow.md §Stop body`/`§Lint gate` mají uzel v grafu, deklarované
v `meta.prose_gates`). Manuální kontrola sémantiky při změně `flow.md`:

- uzly = vlastníci v `flow.md §Tři transformace` + `INDEX.md §Cast`;
- hrany `normal` = sekvence v `INDEX.md §Dispatch matrix`;
- hrany `return` = `INDEX.md` „Return paths";
- gates = `flow.md §Stop body`;
- `model` = `INDEX.md §Model strategy`.

Sanity check (parse, refy, dead-end/orphan, agent roster, spec-driven invariant):

```sh
bash scripts/pipeline/check.sh        # exit 0 = OK, 1 = nálezy
```

## Další krok (mimo F1)

Graf je zatím v template, ale **nečte ho runner ani se nedistribuuje sync**. Wiring
(`agentic-sync.sh` allowlist, runner ve F3, čtení grafu orchestrátorem) je samostatné
rozhodnutí — viz `pipeline-architecture.md §Fázová cesta` a `STATE.md §Open Items`.
