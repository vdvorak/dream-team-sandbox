---
wave: 2026-06-12-engine-oo-refactor
from: implementace (session 2026-06-12, přerušeno — odchod od PC)
to: next-session (POKRAČOVAT od Fáze 3)
type: progress-handoff
returns_to: null
timestamp: 2026-06-12T16:30:00+02:00
---

# PROGRESS: OO refactor enginu — Fáze 1+2 HOTOVY, navázat na Fázi 3

Tohle je **pokračovací** handoff k `HANDOFF.md` (zadání) v téhle složce. Plán
(schválený) je `/home/vitek/.claude/plans/ancient-singing-pnueli.md` — **přečti ho první**,
obsahuje cílovou architekturu, rozhodnutí 5 otevřených otázek a kompletní paritní tabulku
sémantiky. Tenhle soubor říká, co je hotovo a kde přesně navázat.

## Stav: 2 ze 4 fází hotové a zacommitnuté

- **Fáze 1 (commit `611b0a5`)** — Predicate AST. `core/predicate.py` + `core/vocab.py`;
  `frontier.Ctx.atom/classify/flag_live` SMAZÁNY, `eval()` z enginu pryč. Frozen-oracle
  paritní test `parity-predicate.py` (19208 porovnání, 0 neshod).
- **Fáze 2 (commit `c388605`)** — `core/graph.py` (Node/Edge/Graph) + `core/runstate.py`
  (RunState). `frontier.compute_frontier/next` → `Frontier` třída nad objekty. `result.py`
  přepojen na Graph dotazy + Vocabulary + RunState mutátory. **If/elif outcome řetěz v
  result.py ZATÍM zůstává — to je první úkol Fáze 3.**

**Brána drží po obou fázích:** selftest **57/57**, check.sh C1–C15 OK, createdat OK,
parity 19208/0. Working tree po commitu c388605 = čistý.

## Mapa modulů (po Fázi 2)

```
core/predicate.py  485ř  Verdict + atomy + And/Or/Not + Malformed + parser + Predicate
                          (.of/.evaluate/.classify/.structural_live/.problems/.has_fault)
core/vocab.py       88ř  Vocabulary (flag_kind/enum_values/kategorie + fallbacky, missing-mode)
core/graph.py      224ř  Node(+6 podtříd)/Edge/Graph.load + dotazy + Node.is_active
core/runstate.py   185ř  RunState (read pohledy + mutátory; obal nad st dictem)
core/frontier.py   348ř  Ctx(EvalContext, drží .graph) + Frontier třída + CLI; už BEZ dictů
core/result.py     252ř  validace(Vocabulary) + auto-derive(Graph) + IF/ELIF řetěz(→Fáze 3)
core/run.py        248ř  drive() = stringový type žebřík (→Fáze 3 partition)
core/check.py      339ř  C1–C15 stále na syrových dictech (→Fáze 4)
core/status.py      89ř  (→Fáze 4 drobnost)
```

## NAVÁZAT TADY: Fáze 3 (result.py handlery + run.py drive)

### 3a — result.py: if/elif outcome řetěz → polymorfní handlery
Dnešní `result.py` (cca ř. 185–250) je řetěz `if outcome=="FAIL" and advisory / elif FAIL
and returns_to / elif FAIL / elif REJECTED / else`. Mutace UVNITŘ větví už volají RunState
metody (`state.mark_completed/set_outcome/stamp_completion/uncomplete/bump_counter/
add_finding/add_payload/clear_payload`) — extrakce do handlerů je proto **mechanická**:
- Malé objekty/třídy s `matches(outcome, severity, returns_to) -> bool` + `apply(state, env,
  node, stamp_completion) -> ctr_note`. Handlery: **AdvisoryFail · ReturnFail · BareFail ·
  Rejected · Completion** (PASS/APPROVED/ACK/DONE/BLOCKER).
- **Pořadí výběru = dnešní pořadí větví** (advisory → returns_to → bare FAIL → REJECTED →
  else). První `matches` vyhraje.
- `ctr_note` stringy + `st["status"]`/`st["note"]` zápisy MUSÍ zůstat **bajt-identické**
  (selftest grepuje „advisory finding", „return …=…", „REJECTED → halt", …).

### 3b — run.py drive(): stringový type žebřík → node.drive_category partition
Dnešní `drive()` (ř. ~95–192) dělá `by = lambda t: [r for r in ready if r.get("type")==t]`
a větví `if joins / if terminals / if g_block / if workers or g_free / if routers / judgment
/ inflight`. Refactor:
- Přidat `Node.drive_category` do graph.py: **JOIN · TERMINAL · BLOCKING_GATE · FREE_GATE ·
  WORKER · ROUTER**. Blocking se u human-gate resolvuje z interactions (už máš
  `HumanGateNode.blocking(interactions)`); `frontier` info dict NESE `blocking` u human-gate
  → partition může číst z ready-infa NEBO z grafu. **Pozor:** ready dict má `type` string a
  (u human-gate) `blocking` bool — partition může zůstat nad ready dictem, jen čitelněji
  (kategorie místo holého type stringu). Workers = type ∈ {agent, gate}.
- **Prioritní žebřík (joins → terminals → blocking-gate → workers+free-gate → routers →
  judgment → inflight → terminal_reached → BLOCKED) je POLICY EXECUTORU — zůstává explicitní**
  (není to vlastnost uzlu). Refaktoruj jen čitelnost a těla větví na RunState metody
  (`state.mark_completed/set_outcome`, `state.active_node=`, append do frontier/awaiting…).
- Všechny `print(...)` hlášky (FRONTIER/DONE/HALT/DECIDE/BLOCKED/INFLIGHT + DISPATCH řádky +
  „↻ re-flow finding") MUSÍ zůstat **bajt-identické** — selftest je grepuje a parsuje
  (`grep -oP '^\s*DISPATCH \K\S+'`, `grep -oE '^(FRONTIER|DONE|HALT|DECIDE|BLOCKED|INFLIGHT)'`).
- `drive()` dnes čte/zapisuje `st` dict napřímo + `ensure` klíče. Použij
  `RunState.ensure_drive_keys()` (už existuje, jiná sada než result!) a mutátory.

### Fáze 4 (po 3): check.py + status.py + docs
- `check.py` C1–C15 nad `Graph`/`Vocabulary`; **C14 = `predicate.problems(vocab, where)`**
  posbírané z `graph.all_predicates()` (uzly+hrany) — logika atomů už je v `Atom.problems()`
  (StructuralFlag/Target/Class/Comparison/Fault/FreeText ji mají hotovou, ověřeno paritou).
  C2/C5/C6/C7/C11/C12 přes Graph dotazy (`reachable`/`forward_producers`/`adjacency`).
  **Lenientní `Graph.load` je tu kritický** (selftest mutuje graf na rozbitý a čeká konkrétní
  C-nálezy — texty nálezů MUSÍ zůstat identické).
- `status.py` — validace node-ids přes `Graph.load` (drobnost).
- `core/README.md` (dopsat predicate/vocab/graph/runstate do architektury, počet testů zůstává
  57) + `STATE.md` (odškrtnout Open Item „OO refactor enginu — NAPLÁNOVAT", přidat řádek do
  hotových vln) + tenhle handoff zaktualizovat / smazat parity-progress.

## Brána (spusť po KAŽDÉ fázi — všechno musí být zelené)

```bash
bash scripts/pipeline/selftest.sh        # „== VŠE PROŠLO ==", 57× ✓
bash scripts/pipeline/check.sh           # „RESULT: OK"
python3 handoffs/2026-06-12-incremental-reflow/accept-createdat.py   # exit 0 (tiše)
python3 handoffs/2026-06-12-engine-oo-refactor/parity-predicate.py   # „PARITY OK"
grep -rn "eval(" scripts/pipeline/core/  # jen 2 komentáře v predicate.py, žádné volání
```

## Poučení / pasti (ušetří čas)

- **Staleness fixpoint pozor na tvar deps:** `Frontier._active_deps` vrací `(src, when)`
  TUPLY; když potřebuješ jen zdroje, extrahuj `[s for (s,_w) in ...]`. (Záměna = každý uzel
  „stale" → drive nekonečně re-derivuje → guard 200 → selftest visí. Stálo to jeden debug
  cyklus, viz commit c388605.)
- **Verdict NENÍ Kleene** — kombinace: any-JUDGMENT→JUDGMENT, jinak any-UNKNOWN→UNKNOWN, jinak
  bool. Free-text „FAIL…" atom je na ne-FAIL outcome FALSE (skip). Free-text judgment atomy
  jsou ZÁMĚRNÁ kategorie (`mockup needs missing component`, `FAIL: build/deploy/migration`).
- **Serializace current-run.md musí být bajt-identická** — RunState drží `st` dict jako
  úložiště a `ensure_result_keys`/`ensure_drive_keys` udržují pořadí klíčů. Nepřeskládat.
- Selftest je INTEGRAČNÍ guard přes .sh shimy → testuje i to, že CLI hlášky sedí na znak.
  Když měníš print, čekej selftest breakage; je to feature.

## Reference

- Plán (schválený, autoritativní): `/home/vitek/.claude/plans/ancient-singing-pnueli.md`
- Zadání: `handoffs/2026-06-12-engine-oo-refactor/HANDOFF.md`
- Commity: `611b0a5` (Fáze 1), `c388605` (Fáze 2). Předchozí baseline: `8317c31`.
- Registry: `pipeline/{delivery,artifacts,vocabulary,interactions}.yaml`.
