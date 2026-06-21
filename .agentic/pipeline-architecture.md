---
cache_key: pipeline-architecture-v1.0
type: design
last_updated: 2026-06-10
status: FORWARD-LOOKING — design only, nic z toho není implementované
---

# Pipeline Architecture — agentic flow jako deklarativní stavový graf

> ⚠️ **Design, ne aktivní mechanika.** Dnes orchestraci řídí LLM main session
> čtením prózy ve `flow.md`. Tento dokument navrhuje, jak flow převést na
> **strojově čitelný graf** (uzly = agenti, hrany = handoffy), aby běžel
> deterministicky, tool-agnosticky, a šel jednou vizualizovat/editovat jako
> node-editor app. Nic z fází F1–F5 se zatím nestaví — tady je jen architektura
> a cesta.

## Problém

Framework dnes funguje, ale orchestrace má tři slabiny:

1. **Routing je próza v hlavě LLM.** `flow.md` popisuje „kdo je další" textem;
   main session to čte a *rozhoduje*. Dva běhy stejného issue se můžou rozejít.
   Nedeterministické a netestovatelné.
2. **Tool-agnosticismus je jen na papíře.** README slibuje agnosticismus, ale
   kus orchestrace žije inline v `CLAUDE.md` (`Agent(subagent_type=…)`, session-start
   ritual, keyword triggery). Cursor/Aider mají jen kostru. Mozek flow není
   v žádném neutrálním artefaktu — je rozmazaný v per-tool configu.
3. **Chybí „issue → výsledek" jako jeden definovaný tok.** Planning a dekompozice
   na todos nejsou first-class; `current-wave.md` je ve `flow.md` zmíněn, ale nemá
   ani template. Stav běhu se nedá strojově přečíst.

Cena: nekonzistentní výstupy, flow nejde vizualizovat ani migrovat mezi nástroji
bez duplikace logiky.

## Cíl a princip

**Agentic flow = deklarativní stavový graf.** Jeden uzel = jedna agent invocation
s typovanými vstupy a výstupy. Jedna hrana = handoff. Stav běhu se persistuje do
MD (žádná tool-paměť).

Klíčový princip — **graf je sdílený substrát, executory jsou vyměnitelné**:

```
                       ┌─ LLM orchestrátor (dnes — čte graf místo prózy)
pipeline/delivery.yaml ┼─ runner script        (F3 — počítá další uzel ze stavu)
   + stav v MD         └─ node-editor app       (F5 — renderuje a edituje graf)
```

Co se **nemění**: axiomy v `constitution.md`, orchestrator-vs-subagent split
(`flow.md`), handoff formát, write-scope disciplína, gates L0–L3. Tenhle návrh
jen dělá *mechaniku* `flow.md` strojově čitelnou — nedotýká se *principů*.

## Feasibility — může to vůbec fungovat?

**Ano, a je to osvědčený model.** Agentic flow jako propojené uzly s I/O je přesně
to, co dělají LangGraph (state graph s uzly/hranami a *podmíněnými* a *cyklickými*
hranami), n8n, ComfyUI, Flowise, Dify. Uzlový instinkt je správný.

**Jedna korekce:** musí to být **stavový graf**, ne čistý DAG (jednosměrný strom
„šipky zleva doprava"). Náš flow má cykly, brány a větvení, které naivní DAG
nepojme. Tady jsou tvrdé části a jak je graf řeší:

| Design constraint | Proč to máme | Řešení v grafu |
|---|---|---|
| **Cykly / návratové cesty** | Joey→Bob→Joey; failure-signature; strop 3 pokusy | podmíněná zpětná hrana (`kind: return`) + `counter` ve stavu; 3× = BLOCKER |
| **Human-in-the-loop (L3)** | design-source volba, breaking change, deploy souhlas | uzel typu `human-gate` — blokuje běh, čeká na externí vstup |
| **Paralelní fan-out / fan-in** | auditoři (Sheldon/Heimdall/Vitek/Optimus/Edna) po Joey | **dataflow ready-rule**: N uzlů se stane ready zároveň (týž producent) → paralelně; `join` je ready až doběhnou **všichni** producenti. `kind: fan-out`/`fork` = anotace záměru, ne direktiva — routing počítá scheduler z hran |
| **Dekompozice → plán → todos → delegace** | agent z issue udělá spec + plán + work items, pak deleguje práci | normální **výstup uzlu** (artefakt: spec / `work-breakdown.md` / backlog), pak dispatch implementačních uzlů; víc work items = fan-out (for-each) nad runtime seznamem |
| **Podmíněné větve** | no DB → skip Chandler; no UI → skip Edna/Leonard/Denisa | `router` uzel čte flagy z `project-config`/spec |
| **Stav bez tool-paměti** | „hej Watsone" po nové session | běh grafu se serializuje do MD; executor ho načte a pokračuje |

**Dekompozice je normální provoz, ne otevřený problém.** „Z issue se udělá plán
a todos, pak se deleguje práce" = přesně tok grafem: Vision udělá spec (WHAT),
Ted/Tony plán + work items (HOW), orchestrátor deleguje na implementační uzly. Plán
i todos jsou **výstupní artefakty uzlu** (spec, `work-breakdown.md`, `backlog/`) a
stav todos žije v `current-run.md` (`frontier`/`completed`) — **ne nové uzly grafu**.
Graf definuje role a pořadí (stage); todos jsou payload. Víc work items = stejný uzel
opakovaně nebo fan-out (for-each), což graf umí. Jediná modelovací volba (ne riziko):
granularita běhu — 1 run = 1 feature; příliš velká feature → Vision ji rozdělí na
sub-features (`constitution.md`: spec >400 ř. = split), každá vlastní run. Žádná
mutace grafu za běhu.

Závěr: node-editor app **dává smysl** a graf je **no-regret** — i kdyby app nikdy
nevznikla, deklarativní graf zlepší determinismus a agnosticismus už pro dnešní
LLM orchestraci.

## Schéma uzlu (návrh, ilustrativní)

Není to finální formát — ukazuje *tvar*. Vstupy/výstupy uzlu jsou přesně dnešní
„minimální vstupní balíček" (constitution D3) + handoff výstup; model už takhle
de facto funguje, jen to není zapsané jako data.

```yaml
# pipeline/delivery.yaml  (ilustrativní výřez)
nodes:
  vision:
    type: agent
    agent: vision-po
    phase: T1
    inputs:  [backlog-item]              # co konzumuje
    outputs: [spec, acceptance]          # co produkuje (artefakty)
    model_default: sonnet                # strop; orchestrátor smí snížit/zvýšit
  tony-feasibility:
    type: gate                           # L1 inter-agent gate
    agent: tony-cto
    inputs:  [spec]
    outputs: [gate-output]               # PASS | FAIL
  ted:
    type: agent
    agent: ted-architect
    phase: T2
    inputs:  [spec, acceptance]
    outputs: [contract, reuse-decision]
  audit-join:
    type: join                           # pokračuj jen když všichni PASS
    requires: [sheldon, heimdall, vitek, optimus, edna]
  deploy-approve:
    type: human-gate                     # L3 — blokuje na člověka
    level: L3

edges:
  - { from: vision,           to: tony-feasibility }
  - { from: tony-feasibility, to: ted,    when: PASS }
  - { from: tony-feasibility, to: vision, when: FAIL, kind: return }
  - { from: joey,             to: bob,    when: FAIL, kind: return, counter: failure-signature }
  - { from: ted,              to: chandler, when: "project.has_db" }   # router podmínka
```

## Mapování dnešního flow na graf

Důkaz, že graf zachytí dnešní chování 1:1 (`flow.md §Tři transformace`,
`agents/INDEX.md §Dispatch matrix`). Žádný uzel ani hrana navíc.

**T1 — Idea → Spec**
```
backlog-item → vision → tony-feasibility(gate)
                  └─(paralelně, když má UI)→ denisa
tony PASS → ted ;  tony FAIL → return: vision
```

**T2 — Spec → Code**
```
ted → chandler (router: has_db) → bob (server)
ted → leonard (router: has_ui) → peter | mob | winny   (paralelně, dle aktivních targetů)
bob & klienti: unit testy zelené → joey
```

**T3 — Code → Ověření**
```
joey(gate funkční) → fan-out: sheldon, heimdall, vitek, optimus, edna(router: has_ui)
   → audit-join (všichni PASS) → L2 user view
```

**T3-post — Release & Deploy**
```
audit-join PASS → alfred → staging(L2) → deploy-approve(human-gate L3)
   → production → monitor ;  monitor FAIL → return: viník (rollback)
```

**Return paths jako podmíněné zpětné hrany** (`kind: return`):

| Z uzlu | Do uzlu | Podmínka |
|---|---|---|
| joey | bob / peter / mob / winny | bug v kódu |
| joey | ted | bug v API contractu |
| joey | vision | bug v acceptance |
| sheldon | vision / ted | spec/contract nekonzistence |
| heimdall / vitek / optimus | bob / peter / mob / winny | finding v kódu |
| edna | peter/mob/winny / denisa / leonard | design conformance / mockup / manuál |
| alfred | bob/peter/mob/winny / tony / chandler / joey | build/deploy/migration fail |

## Stav běhu v MD (tool-memory-independent)

Běh grafu se serializuje do MD, aby ho po nové session načetl kterýkoli executor
(„hej Watsone" čte tohle). Kandidát: formalizovaný `current-wave.md` / `current-run.md`:

```yaml
run: 2026-06-10-export-pdf
graph: delivery
status: in_progress
class: feature
active_node: joey                               # poslední dotčený (inspekce); NEřídí routing
frontier: [optimus, sheldon, heimdall, vitek]   # inflight: dispatchnuté-ale-ne-hotové
completed: [intake, vision, tony-feasibility, ted, chandler, bob, peter, joey]
outcomes: { joey: PASS }                         # node -> OUTCOME (ready-rule čte fired())
skipped: []                                      # judged-skip uzly (run.sh skip)
counters: { joey->bob: 1 }                       # failure-signature loop (3× = BLOCKER)
awaiting_human: []                               # non-blocking gaty (L2) čekající
halt_gate: null                                  # blocking gate (L3) držící běh
```

Napojení na stávající mechaniku: `STATE.md` = lidský přehled (fokus + open items);
`handoffs/<run>/` = obsahové artefakty mezi uzly (beze změny formátu);
`current-run.md` = strojový stav grafu (nový, malý, deterministický).

## Tool-agnostický execution kontrakt

| Sdílené (neutrální, jeden zdroj pravdy) | Per-tool (tenký adaptér) |
|---|---|
| `pipeline/*.yaml` — graf (uzly, hrany, gates) | jak nástroj vyvolá uzel (CC: `Agent(subagent_type)`; Cursor: mód; Aider: invocation; app: vlastní runtime) |
| `current-run.md` — stav běhu | — |
| handoff formát (`templates/handoff.md`) | — |
| `agents/<short>.md` — definice uzlu (role) | wrapper generovaný `setup-*.sh` |

Cíl F4: vytáhnout orchestrační logiku z `CLAUDE.md` (dnes Claude-Code specifická)
do neutrálního grafu + kontraktu. `setup-*.sh` pak generuje jen **tenký adaptér**,
který umí „spustit uzel X se vstupem Y" — nic víc.

## Vztah k principům uživatele

| Princip | Jak ho graf naplňuje |
|---|---|
| Tool-agnostic | graf + MD stav jsou plain soubory; nástroj je jen executor |
| Specs čisté a čitelné | graf je nemění — uzel `vision` na ně odkazuje jako artefakt |
| Script-first | runner (F3) a state-reader (F2) jsou scripty; LLM jen práce *uvnitř* uzlu |
| Standardizovaná struktura + scaffoldy | graf předpokládá kanonické cesty; konzistence stejného stacku = stejný graf + stejné scaffoldy + stejný I/O kontrakt uzlů |
| Člověk dělá zásadní rozhodnutí | `human-gate` uzly (L3) jsou v grafu explicitní, ne skryté v próze |

## Fázová cesta (forward-looking, nestaví se teď)

- **F0 (toto kolo):** tento design doc.
- **F1:** napsat `pipeline/delivery.yaml` zachycující dnešní flow 1:1 + schema doc;
  validovat proti `flow.md`. Bez změny chování — LLM jen čte graf místo prózy.
- **F2:** state model (`current-run.md`) + `scripts/pipeline/state.sh` reader +
  standardizace todo-trackingu. Vedlejší zisk: robustnější „hej Watsone".
- **F3:** `scripts/pipeline/next.sh` runner — „graf + stav → další uzel + sestavený
  vstupní balíček". LLM přestane rozhodovat routing.
- **F4:** tenké per-tool adaptéry z `setup-*.sh`; orchestrace pryč z `CLAUDE.md`.
- **F5 (budoucí, volitelné):** node-editor app renderující `pipeline/*.yaml` +
  vizualizující `current-run.md`. Graf je už ten formát, který by app četla/psala.
- **SCRUM:** explicitně odloženo. Graf je na něm nezávislý; sprint = pozdější
  seskupení backlog položek *nad* grafem, ne změna grafu.

## Invarianty a otevřené otázky

- **Strict spec-driven (vynuceno):** `vision` (spec autorita) dominuje všem uzlům,
  které produkují kód/kontrakt — z entry se k žádnému producentovi (agent, phase
  `T2`/`T3-post`) nelze dostat bez průchodu Vision. Celé flow tak vždy produkuje na
  základě spec (`constitution.md §1`). Vynucuje `scripts/pipeline/check.sh §C7`;
  intake proto routuje feature i improvement přes Vision (žádná zkratka do ted/tony).
- Žádný executor neobchází constitution axiomy, gates ani write-scope — graf je
  *koordinace*, ne nová autorita.
- **Dekompozice (plán → todos → delegace) je normální provoz** — výstupní artefakty
  uzlu + dispatch, ne mutace grafu (viz §Feasibility). Jediná modelovací volba:
  granularita běhu (1 run = 1 feature; velká feature → split na sub-features).
- **Drobný runtime bod (ne riziko):** počet paralelních work items (fan-out) není
  znám předem — runner ho řeší jako for-each nad runtime seznamem, ne novými uzly.
- **Vztah k `value-streams.md`:** jeden value-stream = jeden graf. Víc proudů
  (delivery, marketing) = víc grafů nad stejným substrátem. Router na vrcholu vybírá
  graf dle typu requestu. Tenhle doc řeší *delivery* graf; marketing se nestaví.
