---
wave: 2026-06-11-frontier-scheduler
from: orchestrator
to: next-session
type: milestone-handoff
returns_to: null
timestamp: 2026-06-11T14:30:00+02:00
---

# Handoff: frontier-scheduler HOTOVÁ (F2–F6 + REJECTED halt)

## Stav (jak chápu situaci)

Předchozí session uzavřela F1 (frontier computation, `next.sh --emit frontier`) a nechala
crisp blueprint pro F2. Tato session **dotáhla celý rewrite naostro**: F2 (drive),
F3 (result.sh) jako spřažený celek + F4 harness, F5 (check.sh) a F6 (doc). Navíc
přibalena drobnost **REJECTED halt** (z Open Items). Single-`active_node`+`pending`
model je pryč, nahrazený **dataflow frontierem**. selftest **17→26**, strom čistý.

## Plán (co session udělala)

1. **F2 `drive` rewrite** — frontier executor. Místo jedné direktivy vydá **celou ready
   množinu jako akce**: paralelní `DISPATCH` workerů, `HUMAN-GATE` non-blocking gatů
   (běh jede dál souběžně), `HALT` na blocking L3 (deploy-approve), `DECIDE` na judgment/
   intake, `DONE`/`BLOCKED`. join/router auto-advance (neprodukují práci). Nový
   `run.sh skip <node>` (judged-skip). `start` seeduje nový tvar stavu.
2. **F3 `result.sh`** — `outcomes` map, inflight (`frontier`) maintenance, `class` z intake.
   FAIL+return = **re-flow**: un-complete cíl + forward-downstream (kód se za vlastníkem
   mění → re-audit), counter++ (3× = BLOCKER). `pending` logika pryč.
3. **F4 harness** — `selftest.sh` drive_loop přepsán na frontier parsing (paralelní dispatch,
   HALT, DECIDE/skip). Nový **scénář C** (`has_ui=true` e2e: fork tony ∥ design-source,
   confluence peter čeká ted+leonard, edna 5. auditor → DONE) + FAIL-re-flow + skip testy.
4. **F5 `check.sh`** — C11 (dataflow-orphan: non-entry uzel musí mít forward producenta) +
   C12 (`join.requires` == množina forward producentů, odvoditelná aserce). +negativní test.
5. **F6 doc** — `flow.md §Deterministický dispatch` přepsán ze single-step na dataflow
   ready-rule; `pipeline-architecture.md` (fan-out řádek + current-run příklad).
6. **REJECTED halt** — `drive` na `status:blocked` (REJECTED / 3× counter / BLOCKER) čistě
   zastaví (`BLOCKED` + důvod v `note`), ne re-nabídka gate. deploy-approve `REJECTED` →
   production se NEspustí.

## Výsledek

- `scripts/pipeline/run.sh` — `drive` = frontier executor; `skip` subcommand; nový seed tvar
- `scripts/pipeline/result.sh` — outcomes/inflight/skip/class; FAIL-re-flow (`forward_closure`); REJECTED/BLOCKER note
- `scripts/pipeline/next.sh` — frontier emit respektuje `skipped` + `blocking` z interactions.yaml
- `scripts/pipeline/state.sh` — nový model (frontier/outcomes/skipped/awaiting-list/halt_gate/class)
- `scripts/pipeline/check.sh` — **C11/C12** dataflow kontroly
- `scripts/pipeline/selftest.sh` — frontier harness; **26/26** (scénář A/B/C, FAIL-re-flow, skip, REJECTED)
- `templates/current-run.md` — nový stavový tvar
- `flow.md`, `pipeline-architecture.md` — dataflow ready-rule dokumentovaný
- `STATE.md` — wave HOTOVÁ; Open Items reconcile
- 4 commity: `457576d` (F2+F3) → `821558a` (F5) → `d7774e6` (F6) → `4f6d4df` (REJECTED)

## Decided (rozhodnutí, která následný agent NEOPAKUJE)

- **intake (router) se dokončuje přes DECIDE+`done`** (ne obchází přes `active vision`).
  V dataflow má `vision` závislost na `intake`; `done intake` s `class:` → class persistuje
  do stavu, drive ho posílá `--class` každou smyčku. Klasifikace = úsudek (DECIDE).
- **judged-skip = `run.sh skip <node>`.** Judgment hrana (`denisa→leonard`), kterou orchestrátor
  vyhodnotí jako „netřeba" → uzel do `skipped`; frontier ho vyloučí z dep-edges (peter se
  odblokuje) i z ready. Ověřeno selftestem.
- **FAIL+return un-completuje cíl I jeho forward-downstream** (`forward_closure` přes non-return
  hrany). Kód se za vlastníkem mění → re-audit všeho za ním je správně (ne překvapení).
- **blocking vs non-blocking gate ze zdroje pravdy `interactions.yaml.blocking`** (ne odvozovat
  z levelu). L3 = HALT celého frontieru; L2 = souběh.
- **`status:blocked` = deliberate halt** (REJECTED / 3× / BLOCKER) — `drive` na něj čistě zastaví
  s důvodem v `note`, nepřepočítává frontier (jinak by re-nabízel gate/uzel).

## Slabé místo (POVINNÉ)

**Engine ověřen jen selftest stubem, ne reálnými agenty.** `drive`/`result`/`next` protáhnou
celý happy-path (i fork/confluence/release/REJECTED) deterministicky, ale node-result obálky
v selftestu jsou syntetické (`outputs: [{type: gate-output}]`, PASS na povel). Drift v **obsahu**
uzlů (reálný subagent vrací nevalidní envelope, nečekaný outcome, špatný returns_to) není
otestován — to je přesně **flow-finish #4**. Risk: runner je zelený proti vlastní simulaci,
ne proti realitě. Doporučení: první reálný běh dělat na **malé** feature v `dogfood/userflow/`,
sledovat (b) jestli `run.sh done` přijme reálné obálky bez ručního překladu (souvisí s
pipeline-loop-fix F3 = handoff→envelope most).

Druhé (menší): **FAIL bez `returns_to`** je degenerate soft-stav (uzel se nedokončí, outcome
FAIL zaznamenán, status in_progress). V dataflow by se gate re-nabídl jako ready donekonečna,
pokud orchestrátor nedoplní `returns_to`. Selftest to nepokrývá (FAIL vždy s returns_to).

## Normativní mezera (volitelné)

- **Co chybí**: `templates/node-result.md` nezná `class:` (intake) ani potvrzení `returns_to`
  jako povinné při FAIL. Doplnit, až flow-finish #4 ukáže reálný tvar obálek.
- **Kde**: `templates/node-result.md` + `result.sh` validace.
- **Kdo**: orchestrátor při flow-finish #4.

## NEXT (příští session)

**flow-finish #4** — re-run profilu B reálnými agenty na konkrétní feature (`dogfood/userflow/`):
celý drive vč. release s reálnými subagenty, ověřit (b) drift v obsahu uzlů. Engine (a) je
ověřen selftestem 26/26, teď jde o realitu. Potřebuje **konkrétní feature/issue** k protažení
(user dodá). Vedlejší: `node-result.md` schema (class, returns_to), FAIL-bez-returns_to robustnost.

## === GATE OUTPUT ===
```
agent: orchestrator
outcome: PASS
outputs:
  - frontier-scheduler F2+F3+F4 (HOTOVO, selftest 26/26)
  - frontier-scheduler F5 check C11/C12 (HOTOVO)
  - frontier-scheduler F6 doc (HOTOVO)
  - REJECTED halt (HOTOVO)
next: flow-finish #4 (re-run profil B reálnými agenty — potřebuje feature)
blockers: null
```
