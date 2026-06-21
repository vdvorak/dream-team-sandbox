<!--
Blueprint vlny `frontier-scheduler`. Návrh PŘED implementací (design-first).
Spec je česky, kód anglicky. Vstupní bod pro implementaci + acceptance.
Souvisí: pipeline-architecture.md (graf), flow.md §Deterministický dispatch (runner),
STATE.md §Aktuální fokus.
-->

# Frontier scheduler — flow jako dataflow DAG, ne jedna linka

## TL;DR — root cause v jedné větě

`drive` drží **jeden** `active_node` + jeden fan-out `pending` barrier, takže neumí
(a) skutečně paralelní nezávislé tracky (UI ∥ backend, security ∥ review) ani
(b) confluence, kde uzel čeká na víc producentů z různých větví (peter potřebuje
`contract` z ted **i** `ui-components` z leonard). Řešení = nahradit single-active_node
**frontier množinou** a routing odvodit jako **dataflow ready-rule z grafu**.

## Co to láme dnes (důkaz)

`has_ui=true`, drive z `vision` (PASS) vydá:

```
DISPATCH-ALL (fan-out, paralelně):
  - tony-feasibility (kind:normal)
  - design-source    (kind:fork)   ← human-gate smíchaný do paralelní práce
Po dokončení všech uzlů ... pokračuje join.   ← žádný společný join neexistuje
```

Fork (`vision→design-source`, samostatná UI linka) je smíchán do fan-out barriery
s main linkou (`vision→tony`), čeká se na neexistující join, a human-gate `design-source`
je traktován jako paralelní práce. To je nález **F5** z wave-pipeline.

## Princip — jedno pravidlo místo tří mechanismů

> **Uzel N je *ready*, když jsou hotoví všichni jeho aktivní producenti.**
> Frontier = všechny ready aktivní uzly. `drive` je dispatchne naráz (paralelně).

Tohle jedno pravidlo **pohltí fan-out i fork i join** — nejsou to tři direktivy:
- **fan-out** = víc uzlů se stane ready zároveň (mají hotového téhož producenta),
- **fork** = nezávislá linka je prostě další ready uzel (žádná speciální `kind: fork` logika),
- **join/confluence** = uzel s víc producenty se stane ready, až doběhnou **všichni**.

`kind: fork` / `kind: fan-out` v grafu zůstávají jako **lidská anotace záměru** (čitelnost,
doc), ale scheduler je nepotřebuje — routing počítá z dataflow závislostí.

## Definice (přesně)

**Dep-edges N** = příchozí hrany `M→N`, které:
- nejsou `kind: return` (return = zpětná vazba, ne závislost), a
- nejsou flag-falsifikované (jejich `when` neobsahuje strukturální atom, který je pro
  tento běh `false` — viz `has_db` přepínání `ted→bob` vs `chandler→bob`).

**fired(M→N)** ⟺ `M ∈ completed` ∧ `when` hrany platí při outcome(M) + flagách
(outcome-část podmínky — typicky `PASS` u gate hran; flag-část už ošetřena v dep-edges).

**READY(N)** ⟺ `active(N)` ∧ `N ∉ completed` ∧ `N ∉ frontier` ∧
   (`N == entry` ∨ (dep-edges(N) ≠ ∅ ∧ ∀ e ∈ dep-edges(N): fired(e))).

= **AND-join přes aktivní flag-live forward producenty.** Vzájemně výlučné flag-cesty
(např. `done` přes `l2-review` při `!has_deploy` vs přes `monitor` při `has_deploy`)
se vyřeší samy: flag-gating nechá živou právě jednu dep-edge → AND přes jednu = správně.

## Jak se skládá s target-gatingem (druhý uživatelův bod)

Flow se **nevolí per stack** (to by byl O(stacků) grafů + porušení axiomu „žádní
tech-specific agenti"). Je to **jeden graf, podmíněně aktivovaný**: `peter when: targets.web`,
`winny when: targets.desktop`, `bob when: has_server`, `denisa/leonard/edna when: has_ui` …
Watson zadrátuje `active_targets` při foundingu; každý drive prořezává sám.

V dataflow scheduleru to padá ven zadarmo: **vypnutý uzel se nikdy nestane ready a nikoho
neblokuje** (není aktivní producent → není dep-edge). `joey` nečeká na `mobile-code`, když
mobile není target. (Ověřeno dnes: mobile-only ⇒ `ted` nabídne jen `mob`; web-only ⇒ jen `peter`.)

## FAIL / return (control-flow vedle dataflow) — návratová strana (E1/E2, HOTOVO)

Graf má vedle dataflow závislostí i **outcome-routing** (PASS dál, FAIL zpět). Dataflow
ready-rule řeší happy-path (vše PASS → všechny forward hrany fired). Návratová strana byla
původně podspecifikovaná (nález flow-finish #4: drive umí *vydat* paralelní audit-set, ale
neměl deterministický příběh pro to, co se vrátí). Doplněno **deterministicky** — gate dodá
`(returns_to, severity, signature)`, engine přechod počítá bez úsudku orchestrátora:

- **severity** (E1): `blocking` (default) → return hrana un-completne **jen cíl**, counter++
  (3× = `BLOCKER`); downstream řeší incremental rebuild (níže). `advisory` → non-blocking nález:
  uzel je hotov (jde do join/dál), nález jen do `findings`, **žádný re-flow**. Tím se kosmetický
  nález oddělí od blokujícího jako VSTUP, ne jako úsudek drive. (Dřív: severity-blind — i
  kosmetický nález srazil celý downstream.)
- **payload-carry** (E1): `signature` (failure-signature) → `return_payload[cíl]`; `drive`
  ho při re-dispatchi vytiskne (`↻ re-flow finding:`). Re-běh dostane CO opravit ZE STAVU,
  ne z paměti orchestrátora. Po úspěšném re-běhu cíle se smaže; `findings` je append-only.
- **incremental rebuild (scoped re-flow) + order-independence** (nahrazuje E2 downward-closure):
  uzel se přepočítá, **jen když se mu reálně změnil vstup** (Make/Bazel). Každé `done` orazítkuje
  verzí (`epoch`) změněné output-typy (`type_versions`) + vlastní uzel (`node_versions`); uzel
  deklaruje `changed: [typy]` (default = všechny jeho output-typy → plný re-flow lazily). Uzel M je
  **stale** ⟺ ∃ vstupní typ M má novější verzi než `node_versions[M]` (abstraktní typ `code` se
  rozbalí na subtypes). Doc-only fix (`changed:[spec]`) tak re-runne JEN spec-konzumenty, ne celý
  forward-closure — **řeší E1-depth** (dřív 1 řádek dokumentu re-floutl 24 uzlů). Verze monotonní →
  **order-independent**: resurrected completion (zpracovaná PO reflow) se zneudrží, vstupní verze
  přebije node-verzi. Staré seedy bez verzí → graceful fallback na downward-closure (producent valid).
- na PASS jde gate do join/dál (fired).

Empiricky ověřeno: audit-batch `optimus PASS ∥ heimdall FAIL→ted` ve dvou pořadích → identický
ready set (`[ted]`) i payload (`ted←signature`), ač raw `completed` list se mezi pořadími liší.
Scoped re-flow: `changed:[spec]` re-runne ted/chandler (čtou spec), bob/joey zůstanou (selftest Fáze 4).

## Stav běhu — model change

`current-run.md`:
- `active_node: <one>` → **`frontier: [ready/in-flight uzly]`** (množina). `active_node`
  zůstane jako „poslední dotčený" pro kompat/inspekci, ne jako řidič.
- nový `outcomes: {node: OUTCOME}` — per-uzel outcome (potřebné pro `fired()`;
  dnes jen skalární `last_outcome`).
- `pending` (fan-out barrier) **zaniká** — nahrazen frontier + ready-rule.

## Fázová cesta

- **F1 — frontier computation** (`next.sh --frontier` nebo `frontier.sh`): z `current-run`
  + grafu vydá ready množinu (JSON). Čistá funkce, testovatelná izolovaně.
- **F2 — `drive` rewrite**: frontier místo single-step (detail níže §F2).
- **F3 — `result.sh` done**: completed += N, `outcomes[N]=outcome`, frontier recompute;
  FAIL+return → un-complete cíle (counter). `pending` logika pryč.
- **F4 — selftest**: frontier-harness; **nový scénář C** (`has_ui=true`): vision → paralelně
  {tony main, design-source UI}, confluence peter (čeká ted+leonard), edna 5. auditor → DONE.
  Plus scénář ověřující **skutečnou paralelitu** (≥2 ready uzly naráz mimo audit fan-out).
- **F5 — `check.sh`**: nová kontrola — každý non-entry, non-return-only uzel má aspoň jednu
  flag-live dep-edge (jinak je nedosažitelný / orphan v dataflow smyslu). `audit-join.requires`
  se stane odvoditelnou ascercí.
- **F6 — `flow.md` / `pipeline-architecture.md`**: dataflow ready-rule jako dokumentovaný
  mechanismus; `kind: fork/fan-out` = anotace záměru, ne direktiva.

## §F2 — `drive` jako frontier executor (detail, z F1 testování)

**Změna kontraktu:** dnes `drive` vydá **jednu** direktivu. Nově vydá **celý ready frontier
jako množinu akcí** — protože paralelní tracky znamenají víc současně dispatchovatelných uzlů.

```
FRONTIER (N ready):
  DISPATCH tony-feasibility (agent:tony-cto, gate)
  HUMAN-GATE design-source   (interaction:design-source, level:L2, blocking:false)
Po `done` každého uzlu → drive přepočítá frontier.
```

**Algoritmus drive:**
1. `next.sh --emit frontier` → `{ready, judgment, waiting, inflight, terminal_reached}`.
2. `terminal_reached` ∧ ready∪judgment∪inflight = ∅ → **`DONE`**.
3. ready rozděl: **human-gaty** vs **agent/gate uzly**.
   - agent/gate ready → **`DISPATCH`** každý (víc = paralelně; orchestrátor je vezme v lib. pořadí).
   - human-gate ready → **`HUMAN-GATE`** (s `interaction`/`level`/`blocking` z grafu+interactions.yaml).
   - terminal v ready → **`DONE`** (jako dnešní terminal pass-through).
4. ready = ∅ ∧ judgment ≠ ∅ → **`DECIDE`** (free-text/return úsudek orchestrátora; vč. intake klasifikace).
5. ready = ∅ ∧ judgment = ∅ ∧ inflight = ∅ ∧ ¬terminal → **`BLOCKED`** (return potřeba / graf drhne).

**Blocking vs non-blocking gate** (`interactions.yaml.blocking`):
- **non-blocking (L2, design-source/l2-review)** — uzel čeká na člověka, ale **frontier jede dál**:
  ostatní ready uzly se dispatchnou souběžně. Člověk odpoví „když se hodí" → `done` gate.
- **blocking (L3, deploy-approve)** — když je v ready, **halt celého běhu** na explicitní ano/ne
  (i kdyby teoreticky bylo co dělat paralelně — destruktivní krok, constitution §8).

**inflight tracking:** `frontier:` list v current-run = uzly dispatchnuté-ale-ne-hotové.
`drive` je tam zapíše při vydání, `result.sh done` uzel z `frontier` odebere + přidá do
`completed`. `next.sh --emit frontier` je už čte (`inflight`) a nevydá je znova.

**`awaiting_human`** (dnes skalár) → list (víc paralelních non-blocking gatů). Blocking gate
= zvláštní halt-flag.

## Acceptance (determinismus = kritérium)

1. `has_ui=false` (backend): chování identické se současností (regrese 14/14 drží).
2. `has_ui=true`: vision forkne dvě paralelní linky; `peter` se **nedispatchne**, dokud
   nejsou hotoví **ted i leonard**; edna se přidá jako 5. auditor; běh dojede do `DONE`.
3. Security ∥ review: ≥2 auditoři ready a dispatchnutí ve stejném `DISPATCH-ALL` (už dnes,
   ale nově jako obecný frontier, ne zvláštní fan-out větev).
4. mobile-only / web-only: confluence i join čekají jen na **aktivní** producenty.

## Riziko / pojistka

Core driver rewrite je high-risk. Pojistka = `selftest.sh` jako safety net (běží před/po
každém kroku) + F1 jako čistá izolovaná funkce (testovatelná bez rewriteu drive). Landovat
po fázích; `has_ui=false` regrese je tvrdý gate (nesmí se hnout).
