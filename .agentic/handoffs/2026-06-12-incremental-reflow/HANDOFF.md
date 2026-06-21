---
wave: 2026-06-12-incremental-reflow
from: orchestrator (Watson session)
to: next-session
type: design-plan
returns_to: null
timestamp: 2026-06-12T01:00:00+02:00
---

# Plán: scopovaný re-flow (incremental rebuild) — řeší E1-depth

## Problém (E1-depth, potvrzen naostro v E2E `2026-06-12-createdat`)

Blocking gate FAIL → re-flow zneplatní **celý forward-closure** cíle, i když oprava ten
downstream reálně netrefí. Sheldonův *dokumentační* nález (spec nedoléčila open-question, ale
chování OK, 25/25 testů) re-floutl **24 uzlů** — re-implementace + re-testy + re-audit kvůli
opravě jednoho řádku v dokumentu. Blocking re-flow je **depth-unscoped**.

## Fix: incremental rebuild (jako Make/Bazel) — jedno pravidlo

> **Uzel se přepočítá, jen když se mu reálně změnil vstup.**

Každý uzel při dokončení **deklaruje, co změnil** (`changed: [typy]`); engine těm typům stampne
verzi; downstream je stale (re-run) jen když jeho vstupní typ má **novější verzi** než jeho
poslední běh. Tranzitivní (ted po re-runu řekne, jestli se contract změnil → propaguje dál).

Příklad: Vision opraví jen doc-sekci spec → `changed: [spec]` (acceptance beze změny):
- `ted` (čte spec) → stale → re-run
- `joey` (čte jen acceptance) → vstup beze změny → **zůstává hotový**

## Mechanika

**Stav (nová pole v current-run.md):**
- `epoch: <int>` — monotonní čítač.
- `type_versions: {typ: epoch}` — kdy byl typ naposledy změněn.
- `node_versions: {node: epoch}` — kdy uzel naposledy doběhl.

**result.sh — completion (PASS):**
- `chg = env.get("changed")`; pokud chybí → **všechny output typy uzlu** (z grafu); `none`/`[]` → prázdné.
- `epoch += 1`; pro `T in chg`: `type_versions[T] = epoch`; `node_versions[node] = epoch`.

**Staleness rule (sdílená — next.sh frontier + validita):**
- Completed uzel `M` je **stale** ⟺ ∃ vstupní typ `T` uzlu `M`: `type_versions[T] > node_versions[M]`.
- Stale → ber jako not-completed (re-run).

**result.sh — FAIL+returns_to (blocking):**
- un-complete **jen cíl** (+ counter). Žádný eager forward-closure. Downstream řeší staleness
  až po re-runu cíle (lazy, tranzitivně).

## Co to NAHRAZUJE (proto je to vlna, ne patch)

1. `result.sh` forward_closure re-flow → un-complete jen cíl; downstream přes staleness.
2. `next.sh` **E2 valid-fixpoint** („producent musí být completed" = downward-closure) →
   **version-based staleness** (vstupní verze ≤ moje verze). POZOR: E2 order-independence se
   MUSÍ zachovat (verze jsou monotonní → order-independent; ověř/přepiš E2 test).

## Zpětná kompatibilita / záludnosti

- `changed` chybí → default = všechny outputy → reprodukuje plný downstream re-flow (koncový
  stav stejný), ale **lazily** (cascada po re-runech, ne najednou). → **F3 test se mění**
  (immediate set = jen cíl, ne celý downstream). Aktualizovat.
- **Chybějící verze** (staré seedy / live běhy): graceful fallback — chybí-li `node_versions[M]`
  nebo `type_versions[T]`, ber jako epoch 0 / fallback na „producent musí být completed" (E2
  chování). Ať staré stavy nespadnou.
- **Gaty** (gate-output, žádný konzumovaný artefakt) → re-run gatu nedělá nikoho stale. OK.
- **Joins / control uzly** — ověř, že staleness nezacyklí (epoch monotonní → bez cyklu).

## Fázová cesta (test-driven, selftest jako guard po každém kroku)

1. **Stav + stamping**: schema (epoch/type_versions/node_versions) + result.sh stampuje při
   completion (`changed` default all). Additivní, chování zatím beze změny.
2. **FAIL handler**: un-complete jen cíl (+ counter). Aktualizuj F3 test (lazy immediate set).
3. **Staleness v next.sh**: nahraď E2 valid-fixpoint version-staleness rulem. Ověř E2
   order-independence test (přepiš na verze). Fallback pro chybějící verze.
4. **Testy**: nový scoped-reflow scénář (vision `changed:[spec]` → ted stale, joey NE);
   default-all scénář (= plný re-flow); E2 order-indep; F3 lazy.
5. **Docs**: `flow.md §drive` + `frontier-scheduler.md §FAIL/return` (E1-depth → incremental).

## Acceptance

selftest zelený (aktualizovaný) + nový scoped-reflow test + E2 order-independence drží +
spec-doc scénář re-runne JEN spec-konzumenty (joey zůstane hotový). Empiricky: zopakuj E2E
`createdat` scénář se sheldon-blocking → re-flow jen spec-větve, ne celá pipeline.

## Kontext / odkud to vzešlo

E2E `2026-06-12-createdat` (STATE §Aktuální fokus, commit `5fd0fbb`). Souvisí s E1 severity
(`handoffs/2026-06-11-flow-determinism/HANDOFF.md`) a E2 self-heal (tamtéž). Vodítko: viz
paměť „flow-determinism north-star" — přepočítej deterministicky JEN to, co na změně závisí.

---

## HOTOVO (implementováno dle plánu)

Všech 5 fází zavezeno, plán dodržen 1:1:

1. **Stav + stamping** — `templates/current-run.md` + `result.sh`: `epoch`/`type_versions`/
   `node_versions`, `stamp_completion()` v obou completion větvích (success i advisory). `changed`
   default = node outputy z grafu; `none`/`[]` = jen node-verze. `node_versions[node]` se nastaví
   VŽDY (i `none`) → uzel s nezměněným outputem nezůstane navždy stale. Additivní, routing nečetl.
2. **FAIL handler** — `result.sh` FAIL+returns_to un-completne **jen cíl**; `forward_closure`
   funkce smazána. F3 selftest přepsán (lazy immediate set: cíl pryč, downstream zůstává).
3. **Staleness** — `next.sh`: E2 downward-closure nahrazena version-staleness
   (`type_ver(T) > node_versions[M]`, abstraktní typ rozbalen přes `artifacts.yaml subtypes`).
   Graceful fallback: uzel bez `node_versions[M]` → downward-closure (E2 chování) → staré seedy/live
   běhy nespadnou. Order-independence drží přes monotonní epoch (ne přes downward-closed cache).
4. **Testy** — selftest **45/45**. Fáze 4 verzovou cestou: (A) scoped `changed:[spec]` → ted/chandler
   stale, bob/joey zůstávají; (B) default-all → joey stale taky; (C) version order-indep (contract v8
   → chandler+bob tranzitivně, joey lazy). Existující testy (neverzované seedy) jedou fallbackem.
   Determinismus ověřen PYTHONHASHSEED stressem.
5. **Docs** — `flow.md §FAIL+return`, `frontier-scheduler.md §FAIL/return`, STATE §Aktuální fokus
   + Open Item uzavřen.

## Acceptance naostro — HOTOVÁ ✓ (2026-06-12)

E2E `createdat` (backend-only feature) protažen **reálným grafem** přes `run.sh drive` + `result.sh`
(ne syntetický selftest seed). Reproducer: `accept-createdat.py` (v této složce; `python3
accept-createdat.py`, čte repo graf přes `PIPELINE_GRAPH`).

**Scénář:** happy intake→vision→tony→ted→chandler→bob→joey→fan-out(optimus,sheldon,heimdall,vitek).
Audit-vrstva: **vitek advisory** (UserView 4× dup → bez re-flow, zůstává hotový) + **sheldon blocking**
(spec open-question 'created_at tz?' vs contract CLOSED) → return `vision`. Vision opraví jen doc-sekci
spec (`changed:[spec]`); ted re-runne, ale contract beze změny (`changed:none`) — realistické pro
doc-reconciliation k už CLOSED kontraktu.

**Výsledek:**
- re-flow dispatch = **{vision, tony-feasibility, ted, chandler, sheldon}** (5 = spec-spine + stěžující
  si auditor) — PŘESNĚ očekávaná množina.
- **bob, joey, optimus, heimdall, vitek** se NEre-dispatchnuly a zůstaly v `completed` (kód +
  code-auditoři nedotčeni). Dřív (forward-closure) totéž re-floutlo **24 uzlů**.
- `counters: {sheldon->vision: 1}` (žádný BLOCKER), `status: done`, terminal dosažen.

**Jádro důkazu:** `ted` JE stale (čte spec) a re-runne, ale jeho `changed:none` znamená, že
`type_versions[contract]` se nebumpne → `bob` (čte contract, ne spec) zůstane valid → kaskáda se
zastaví na spec-spine. To je Make/Bazel chování na reálném I/O wiringu, ne na seedu.

**Vedlejší poznatek (orchestrace, ne blocker):** non-blocking `l2-review` drive nabízí *souběžně* se
stale spec-spine re-runy (frontier-scheduler design: L2 gate neblokuje). Kdyby člověk ACKnul `l2-review`
předčasně, běh dojede do `done` s `ted`/`chandler` stále stale (nere-runnutými). Neškodné: produkt je
identický (contract/kód se nezměnily), a self-correcting — kdyby spec-fix VYŽADOVAL změnu contractu,
ted by deklaroval `changed:[contract]` → bob/joey/auditoři stale → audit-join se nenaplní → `l2-review`
není dosažitelný, dokud kaskáda nedoběhne. Disciplína (reflektnuto v reproduceru): human-gate odbav až
po vyprázdnění worker-frontieru.
