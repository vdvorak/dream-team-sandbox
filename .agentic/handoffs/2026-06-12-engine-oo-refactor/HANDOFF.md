---
wave: 2026-06-12-engine-oo-refactor
from: orchestrator (design session)
to: next-session (PLÁNOVÁNÍ)
type: design-handoff
returns_to: null
timestamp: 2026-06-12T13:00:00+02:00
---

# Handoff: OO refactor enginu — doménový model místo if/regex/eval slepence

**Účel:** zadání pro příští session, aby **naplánovala** (a pak provedla) refaktor pipeline
enginu z procedurálního string/if/`eval()` kódu do **doménového modelu** (Node/Edge/Graph/
Predicate třídy). Žádná změna chování — čistý refactor pod 57 zelenými testy.

---

## 1. Proč (problém)

Engine (po bash→python vlně) je funkčně hotový a stabilní, ale **vnitřně je to procedurální
slepenec**. Metriky (`scripts/pipeline/core/`):

| modul | ř. | `if` | `re.` | `eval()` |
|---|---|---|---|---|
| **frontier.py** | 443 | **91** | 13 | **2** | ← nejhorší
| check.py | 339 | 74 | 6 | 0 |
| result.py | 301 | 61 | 0 | 0 |
| run.py | 248 | 45 | 0 | 0 |

**Jádro problému = vyhodnocování `when` podmínek.** Stejná logika (rozsekej string na atomy
regexem → klasifikuj každý atom hromadou ifů → poskládej výraz zpátky → `eval()`) je v
`frontier.py` **TŘIKRÁT**: `Ctx.atom()`, `Ctx.classify()`, `Ctx.flag_live()`. Každá ~30 řádků
ifů + regex + `eval(expr, {"__builtins__":{}}, {})`. To je křehké, neunit-testovatelné a pro
budoucí node-editor app nepoužitelné (app by musela parsovat YAML stringy).

User verdikt: *„ifovací prasárna … nešla by nad tím udělat architektura aby to bylo fakt puzzle"*.

---

## 2. Aktuální stav enginu (orientace — CO REFAKTOR ZASTÁVÁ)

- **Engine = Python v `scripts/pipeline/core/`**, `.sh` jsou tenké shimy. `common.py` = sdílené.
- **Uzly grafu = ROLE** (`delivery.yaml`: product/architecture/db-schema/backend/ux-design/
  ui-system/web/mobile/desktop/qa/performance/spec-audit/security/code-quality/design-audit/
  devops/feasibility/design-intake), `agent:` = cast binding (persona). Hrany drátují role.
- **Registry (zdroj pravdy):** `pipeline/artifacts.yaml` (typy I/O), `pipeline/vocabulary.yaml`
  (flagy/enumy/node_types/edge_kinds/severities/faults/classes/targets/phases/model_tiers),
  `pipeline/interactions.yaml` (human-gaty).
- **Stav běhu:** `current-run.md` (```yaml blok: completed/outcomes/frontier/epoch/type_versions/
  node_versions/findings/return_payload/model_overrides/flags/counters/…).
- **Co engine umí (chování, které MUSÍ zůstat 1:1):** frontier dataflow ready-rule, incremental-
  rebuild staleness (verze), severity gating (blocking/advisory), E1 payload-carry, B2 touches_db,
  B3 model-override, F3 auto-derive, target-gating, design_source politika, active_roles, fail-closed
  vocabulary. Vše kryto `selftest.sh` (**57 scénářů**) + `check.sh` (C1–C15) + createdat reproducer
  (`handoffs/2026-06-12-incremental-reflow/accept-createdat.py`).

---

## 3. Navržená architektura (doménový model)

Nový soubor **`core/model.py`** (+ rozpad), engine moduly ho konzumují:

```
Vocabulary                      # z vocabulary.yaml; klasifikuje atom (flag? enum? outcome? …)
  .flag_kind(name) -> bool|enum|None
  .is_valid(category, value) -> bool

Predicate                       # `when` jako PARSOVANÝ STROM (ne string+eval) — KEYSTONE
  Predicate.parse(when:str, vocab) -> Predicate        # validuje při parsu (fail-closed)
  .evaluate(ctx) -> Verdict     # Eligible | Skip | Judgment | Unknown   (tri-state, JEDNO místo)
  atomy (uzly stromu):
    OutcomeAtom(PASS/FAIL/…)  FlagAtom(name)  FlagEqualsAtom(name,val)
    ClassAtom(val)  FaultAtom(val)  TargetAtom(x)  FreeTextAtom(text)   # judgment marker
  kompozitní: And(children)  Or(children)  Not(child)

Node (abstract)                 # props: id(role) · agent · phase · model · inputs · outputs · when:Predicate
  AgentNode · GateNode · HumanGateNode · RouterNode · JoinNode · TerminalNode
  .is_active(ctx) -> active|inactive|unknown          # role_status + when
  .drive_action(...)            # polymorfně místo `by("join")/by("terminal")` ifů v run.py

Edge                            # from · to:[ids] · kind:EdgeKind(enum normal/return/fork/fan-out)
  .when:Predicate · .counter · .is_forward()

Graph                           # nodes:{id:Node} · edges:[Edge] · meta(entry)
  Graph.load(path, vocab) -> Graph
  .forward_deps(node_id) -> [(src, Edge)]    # nahrazuje ruční deps dict
  .producers_of(node_id) · .returns_from(node_id) · .nodes_by_type(t)

RunState                        # obal current-run.md stavu
  .completed · .outcomes · .versions(epoch/type/node) · .flags · …
  .is_stale(node) -> bool       # incremental-rebuild staleness jako metoda
  .valid_completed() -> set     # downward-closure/version self-heal
  .stamp(node, changed)         # completion stamping
```

**Skládání (puzzle):**
- `Frontier(graph, state, ctx).compute()` — ready-rule jako iterace nad `Node`/`Edge` objekty
  (`node.is_active`, `edge.when.evaluate`, `state.is_stale`), ne nad dicty + nested ify.
- `result.py`: outcome větvení (advisory / FAIL+return / REJECTED / success / BLOCKER) → **polymorfní
  `Outcome` handlery** nebo `RunState.apply(envelope)` state-machine, místo if/elif řetězu.
- `run.py drive`: dispatch dle `node.type` polymorfně (`node.drive_action()`), ne `by("join")` ify.
- `check.py`: checky jako funkce nad `Graph`/`Vocabulary` (C8/C9/C14/C15 z registru padnou skoro zadarmo).

**Proč Predicate AST = největší výhra:**
1. Zmizí trojí regex+`eval()` duplikace (atom/classify/flag_live → jeden `.evaluate`).
2. **Validace slovníku vypadne ZADARMO** — parser narazí na neznámý flag → error (dnešní C14 grep
   se stane vedlejším produktem parsu).
3. Unit-testovatelné atom po atomu; **app-importovatelné** (editor čte/píše `Predicate`, ne stringy).
4. `eval()` (bezpečnostně i čitelnostně podezřelý) úplně zmizí.

---

## 4. Kde přesně je spaghetti (mapa pro refactor)

- `frontier.py`:
  - `Ctx.flag()` (~25 ř) — flag resolution + touches_db/design_source defaulty.
  - `Ctx.atom()` (~30 ř) — regex klasifikace atomu → Predicate atomy.
  - `Ctx.classify()` (~30 ř) — split+eval → `Predicate.evaluate`.
  - `Ctx.flag_live()` (~25 ř) — DUPLIKÁT classify pro strukturální flagy → `Predicate.evaluate(structural_only)`.
  - `compute_frontier()` (~70 ř) — ready-rule + staleness → `Frontier.compute` + `RunState`.
  - `compute_next()` (~25 ř) — single-node kandidáti → `Graph` dotaz.
- `result.py`:
  - velký `if outcome == FAIL+advisory / FAIL+returns_to / FAIL / REJECTED / else` blok (~80 ř) →
    polymorfní outcome handlery / `RunState.apply`.
  - `stamp_completion()` → `RunState.stamp`.
  - fault resolve + single-return auto-resolve → `Graph.returns_from` + `Edge`.
- `run.py drive`: frontier-dict processing (joins/terminals/gates/workers/routers) → `Node.drive_action`.
- `check.py`: C1–C15 jako sekvence — strukturně OK, ale může konzumovat `Graph`/`Vocabulary` objekty.

---

## 5. Fázová cesta (každá = samostatný commit, 57 testů jako brána)

1. **`model.py`: Vocabulary + Predicate AST** → přepojit `frontier.py` (atom/classify/flag_live
   ZMIZÍ, nahradí `Predicate.evaluate`). C14 logika se přesune do parsu. **Největší výhra, ohraničené.**
2. **Node/Edge/Graph objekty** → `Graph.load`; frontier/check/result konzumují objekty místo dictů.
   `RunState` obal nad current-run.md (staleness/valid/stamp jako metody).
3. **result.py outcome handlery** (polymorfně) + **run.py drive** (Node-polymorfní dispatch).
4. (volitelně) check.py přepojit na Graph/Vocabulary; ledger/status taky.

**Pořadí důležité:** Predicate (1) je nezávislé a největší úklid → dělat první. Node/Edge/Graph (2)
je nosná kostra pro zbytek. result/drive (3) navrch.

---

## 6. Acceptance / constraints

- **ČISTÝ REFACTOR — nula změny chování.** `selftest.sh` **57/57** zelený po KAŽDÉ fázi, `check.sh`
  C1–C15 OK, createdat reproducer drží. To je nepřekročitelná brána.
- Rozhraní (`run.sh drive`, `result.sh <env>`, `check.sh`) beze změny — shimy + CLI stejné.
- `core/*.py` zůstává importovatelné (app vrstva). Doménový model je PRÁVĚ to, co app konzumuje
  (VISION §Most node-editor) — `Node`/`Edge`/`Predicate`, ne YAML stringy.
- Žádná nová závislost (čistý Python + PyYAML). `model.py` je sourozenec ostatních core modulů.

---

## 7. Rizika / háčky

- **Free-text judgment atomy jsou ZÁMĚRNÁ kategorie**, ne typo. `FreeTextAtom` musí přežít
  (`"mockup needs missing component"`, `"FAIL: build/deploy/migration"`, `"FAIL → rollback"`).
  Parser: flag-shaped atom (bare/`X==Y`/target) → typovaný + validovaný; víceslovná fráze → FreeText
  → Judgment. (Pozor: `"FAIL: …"` má speciální chování — FAIL-prefix → skip na non-FAIL outcome.)
- **Tri-state je klíčové.** `evaluate` musí umět Eligible/Skip/Judgment/Unknown (None). Dnešní
  `classify` + `flag_live` mají JINOU sémantiku (flag_live = „strukturálně ne-falsifikované",
  ignoruje outcome/free atomy). V modelu: `Predicate.evaluate(ctx, structural_only=True)` pro deps.
- **Order-independence + staleness** (incremental rebuild) je subtilní — `RunState.is_stale`/
  `valid_completed` musí zachovat: version-staleness (verzované uzly) + downward-closure fallback
  (neverzované seedy). Empiricky ověřeno; přepiš pod testy Fáze 4 selftestu.
- **Backward-compat:** `active_roles` (nové) + `agents:` (staré) — `node.is_active` čte obojí.
- Dicty current-run.md zůstávají na disku (YAML); `RunState` je jen in-memory obal (serializace
  zpět beze změny formátu — `result.py` ho ukládá identicky).

---

## 8. Otevřené design otázky (k rozhodnutí při plánování)

1. **Granularita:** jeden `model.py`, nebo rozpad (`predicate.py`/`graph.py`/`state.py`)?
2. **Predicate parser:** ručně psaný recursive-descent nad atomy, nebo malý tokenizer + Pratt?
   (Gramatika je triviální: atomy + `&&`/`||`/`!`/`()`.)
3. **Node polymorfismus:** plné podtřídy (AgentNode…), nebo jeden Node + `type` enum + strategy?
4. **RunState:** mutovatelný obal, nebo immutable + apply→nový stav (čistší pro determinismus/test)?
5. **Rozsah:** jen frontier+predicate (Fáze 1–2), nebo i result/drive (Fáze 3)? Doporučení: udělat
   1–2 jako první vlnu (největší zisk), 3 jako druhou.

---

## Reference

- Session, co tohle připravila: commity `863d716`→`62a47aa` (bash→python, role-rename, design_source,
  flow-blind naplno, vocabulary). Předchozí handoff: `handoffs/2026-06-12-engine-python-roles/`.
- Doménová pravda dnes: `pipeline/{delivery,artifacts,vocabulary,interactions}.yaml`.
- Testy/brána: `scripts/pipeline/selftest.sh` (57), `scripts/pipeline/core/check.py` (C1–C15),
  createdat reproducer.
- Architektura agentů (flow-blind, role=node, persona=binding): `agents/ARCHITECTURE.md`, `INDEX.md §Cast`.
