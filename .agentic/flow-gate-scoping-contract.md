# flow-gate-scoping — implementační kontrakt (HOW)

**Wave:** 2026-06-15-flow-gate-scoping
**Autor uzlu:** architecture (Eywa — doménově flow-mašinérie)
**Zdroj pravdy CO/PROČ:** `specs/flow-gate-scoping.md` + `acceptance/flow-gate-scoping.md` (AC-1..AC-7)
**Feasibility:** Tony PASS, tier M, stack-impact NONE.

Tento dokument fixuje implementační mechaniku 4 fixů. Spec mlčí o mechanice (env, hrany,
git refs) — to určuje tento kontrakt. Implementace se řídí TÍMTO dokumentem, ne diagnózou.

---

## Ground truth (ověřeno v kódu, ne z hlavy)

- Skenery (`spec-agnostic-scan.sh`, `format-check.sh`, `file-size.sh`) **NEmají** delta mechanismus.
  Mají jen `--root DIR`. Agregátor `preflight.sh --mode spec|code` je jediný vstup raných bran.
  `grep -rn WAVE_BASE` v `.agentic/` → 0 výskytů (mechanika neexistuje, stavíme ji od nuly).
- Predikáty `when:` **jsou strojově vyhodnocované** pro strukturální flag-atomy a `==`/`!=`
  porovnání (`predicate.py` `PROJ_RE`, `CMP_RE`; `frontier.Ctx.flag()`). `condition_language:
  human-readable` v `delivery.yaml:19` je konzervativní legacy framing — realita F2 už predikáty
  nad flagy/class vyhodnocuje. `frontier.py:303-306` plní Ctx z `current-run.md` (`flags`, `class`).
  → **FIX #2 má reálný mechanický hook, není to próza.**
- `run.py:52` `"counters": st.get("counters", {}) if st else {}` — `start` **dědí** countery.
  `runstate.py:36` `fresh_result` má korektně `"counters": {}`. Reálný `current-run.md` nese
  carry-over (`spec-gate->product: 2`), který musel orchestrátor ručně nulovat. → FIX #4 potvrzen.
- Constitution `§Spec je stack-, agent- a impl-agnostická` (řádek 272+) mluví o „spec", ale řádek
  303 míchá „akceptační kritérium" do zákazů → zdroj AC-5 zmatku. Skener `acceptance/` necílí
  (`P_MDREF` + `ALLOW_MD_TOKEN`), ale normativní text není explicitní. → FIX #3 potvrzen.
- `commit-on-done`: vlna commituje až na konci → **během vlny jsou změny necommitnuté** (working
  tree). To je load-bearing pro FIX #1 (viz níže).

---

## FIX #1 — Delta-scope mechanických bran

### Rozhodnutí 1.1 — Báze vlny: kde, kdy, pod jakým klíčem

**Báze = git ref zachycený při `run.py start`, zapsaný do `current-run.md` pod klíčem `wave_base`.**

- `run.py` mode `start` (funkce `mutate_state`, blok `if mode == "start"`) navíc spočítá
  `git rev-parse HEAD` a uloží do seed dictu jako nový skalár `"wave_base": <sha|None>`.
- Pořadí klíčů: vlož `wave_base` hned za `run` (před `graph`), aby serializace zůstala čitelná
  a stabilní. Stejný klíč přidej do `runstate.fresh_result` (sjednocení — viz FIX #4).
- Pokud `git rev-parse HEAD` selže (mimo git / no commits) → `wave_base = None` (degraduje na
  full-scan, viz Rozhodnutí 1.3). `start` NIKDY nefailuje kvůli gitu.

> Báze je commit při startu vlny. Vše, co vlna od té doby změnila (commitnuté i necommitnuté),
> je delta vlny.

### Rozhodnutí 1.2 — Uncommitted soubory (KRITICKÉ)

**Delta set = `git diff --name-only $wave_base` + `git diff --name-only --cached` +
`git ls-files --others --exclude-standard` (untracked).** NE `$wave_base..HEAD`.

Důvod: commit-on-done znamená, že během vlny jsou změny v working tree NEcommitnuté. `$wave_base..HEAD`
by je neviděl (HEAD == wave_base po většinu vlny) → delta scope by byl prázdný a brána by
falešně prošla / nic neskenovala. Proto bereme **working tree + index + untracked vůči bázi**:

```
git diff --name-only "$WAVE_BASE"            # tracked změny working tree vs báze (committed i ne)
git diff --name-only --cached "$WAVE_BASE"   # staged změny vs báze
git ls-files --others --exclude-standard     # nové netrackované soubory (nové specs, kód)
```

Tři výstupy `sort -u`. To je „vše, co vlna dosud změnila nebo přidala", bez ohledu na commit fázi.

### Rozhodnutí 1.3 — Zpětný default (opt-out)

- **Delta = default, KDYŽ je báze dostupná** (`WAVE_BASE` neprázdný a git OK).
- **Full-scan = fallback**, když báze chybí (`WAVE_BASE` prázdný / `None` / ne-git) NEBO explicitní
  `--full-scan`. Full-scan je dnešní chování (zpětně kompatibilní).
- Prázdný delta set (vlna zatím nezměnila žádný relevantní soubor) → brána **PASS** s hláškou
  „delta scope prázdný — nic ke skenu" (AC-1: vlna, co nemění nic, neselže na cizím dluhu).

### Rozhodnutí 1.4 — Mechanika předání delta listu (kde se mění)

**Vlastníkem delta-resolve je `preflight.sh`** (jediný vstupní bod bran). Skenery dostanou
seznam souborů, NE samy nečtou git (single source of delta logiky).

1. **`preflight.sh`** — nový kód:
   - Čte `WAVE_BASE` z env. Pokud prázdné, zkusí přečíst `wave_base` z `current-run.md`
     (přes `run.sh`/`state.sh` helper nebo grep skalár — viz pozn. níže). Pokud ani tak → full-scan.
   - Nové flagy: `--delta` (vynutí), `--full-scan` (vynutí full), `--wave-base SHA` (override).
   - Spočítá delta set (Rozhodnutí 1.2), zapíše do dočasného souboru, předá skenerům přes `--files`.
   - Default rozhodnutí delta vs full dle Rozhodnutí 1.3.
2. **Každý skener** (`spec-agnostic-scan.sh`, `format-check.sh`, `file-size.sh`) — nový flag
   **`--files FILE`** (cesta k souboru se seznamem, jeden path na řádek). Když `--files` předán:
   sken se omezí na průnik (delta ∩ vlastní doména skeneru: spec-agnostic jen `specs/**`,
   format-check jen soubory dle stacku, file-size jen zdrojáky). Když `--files` chybí: dnešní
   full-scan chování (`--root`). **Žádná změna logiky co skener posuzuje** — jen scope vstupu (Out dle specu).
   - Implementace v každém skeneru: pokud `--files`, nahraď `find`/`grep -r` za iteraci nad
     filtrovaným seznamem (`grep -F -f <(domain-filter)` nebo `xargs`), aby pre-existing dluh
     mimo delta nepadl do nálezů.
3. **`delivery.yaml`** — beze změny logiky uzlů. `desc` u `spec-gate`/`code-lint` doplnit větou
   „skenuje delta vlny (soubory od `wave_base`), full-scan jen bez báze" — dokumentační, ne mechanická.

> Pozn. čtení `wave_base` z `current-run.md` v bashi: preferuj nový pomocný subcommand
> `run.sh status --field wave_base` (čistý, deterministický) NEBO ať orchestrátor exportuje
> `WAVE_BASE` do env před voláním brány. Implementace zvolí env-first (orchestrátor exportuje),
> s fallback grep skaláru z `current-run.md`. Skener git NEčte — jen `preflight.sh`.

### AC pokrytí #1
- AC-1: delta = working-tree+index+untracked vůči bázi → vlna vidí jen své soubory.
- AC-2: pre-existing dluh není v delta setu → neblokuje; full-repo scan (mimo pipeline) ho stále najde.

---

## FIX #2 — Lehká dráha (skip feasibility + architecture)

### Rozhodnutí 2.1 — Jak se podmínka REÁLNĚ vyhodnotí (KRITICKÉ)

**Vyhodnotí ji frontier deterministicky přes `when:` predikát nad run-state flagy** — protože
`predicate.py` `==` porovnání a bool flagy JSOU strojově vyhodnocené (ground truth výše). Žádný
nový mini-uzel, žádné AI rozhodnutí mid-wave.

Zavádíme jeden run-state flag:

- **`lightweight: true|false`** v `current-run.md flags:` (default: nepřítomen = false/UNKNOWN → uzly běží).

Podmínka lehké dráhy je konjunkce tří už existujících / nově zaváděných signálů:

```
lightweight == true   ⟺   class == improvement  ∧  stack_impact == none  ∧  no_new_contract
```

Místo skládání tří atomů v každé hraně (křehké) **kondenzujeme do jednoho odvozeného flagu
`lightweight`**, který autorizovaně nastaví intake/feasibility (viz 2.2). Hrany v grafu pak
testují jediný deterministický atom `flags.lightweight`.

### Rozhodnutí 2.2 — Kdo autorizovaně zapíše podmínku, a KDY (před feasibility)

Tři vstupy podmínky, každý má jasného autora a okamžik:

1. **`class == improvement`** — zapisuje **intake** (router) přes `done` envelope (`class: improvement`).
   Už dnes existuje. Okamžik: první uzel.
2. **`stack_impact == none`** — **PROBLÉM:** dnes to hlásí feasibility (Tony) AŽ ve svém běhu;
   ale lehká dráha má feasibility PŘESKOČIT. Nemůže to tedy autorizovat feasibility.
   **Rozhodnutí:** `stack_impact` posoudí **intake klasifikace** jako součást triage — intake
   už dnes klasifikuje class; rozšíříme jeho envelope o `flags: { stack_impact: none|some }`.
   Intake je tech-aware bod (Watson/orchestrátor), který u XS improvement (JSON edit, doc, rules)
   bezpečně řekne „NONE". Při nejistotě → `some` (konzervativní: uzly běží). Tím je podmínka
   určena **při zahájení vlny** (AC-4), ne ad-hoc uprostřed.
3. **`no_new_contract`** — deterministický test nad delta setem (z FIX #1!):
   `git diff --name-only $WAVE_BASE | grep -q '^contracts/'` → pokud nic, no_new_contract=true.
   Vyhodnotí ho **intake** ve stejném envelope (nebo orchestrátor při startu), zapíše
   `flags: { new_contract: false }`. Při startu vlny je delta typicky prázdný → spoléháme na
   intake úsudek „tato vlna nezavádí kontrakt"; konzervativní default `new_contract: true` (uzly běží).

**Zápis `lightweight`:** intake v `done` envelope emituje rovnou odvozený flag
`flags: { lightweight: true }`, KDYŽ platí všechny tři (intake je jediné místo, kde se to skládá).
Orchestrátor flag nezapisuje ručně — vychází z intake envelope (autorizovaný zdroj).
Alternativně (čistší pro audit): intake emituje tři dílčí flagy (`class`, `stack_impact:none`,
`new_contract:false`) a graf testuje konjunkci. **Volba kontraktu: jeden odvozený flag `lightweight`**
— menší povrch v grafu, jeden atom k testu, méně míst k driftu. Dílčí signály zůstanou v envelope
jako audit stopa (note), ale routing čte `lightweight`.

### Rozhodnutí 2.3 — Mechanika skipu v grafu (kde se mění)

`delivery.yaml` — feasibility a architecture se na lehké dráze obejdou hranou, ne mazáním uzlu
(Out dle specu: žádné trvalé vypnutí). Vzor existující judged-skip (`run.py skip`) + podmíněná hrana:

- Přidej hranu z `spec-gate` (PASS) přímo na cíl po architecture, KDYŽ `flags.lightweight`:
  ```
  - { from: spec-gate, to: feasibility, when: "PASS && !flags.lightweight" }
  - { from: spec-gate, to: <arch-downstream>, when: "PASS && flags.lightweight", kind: ... }
  ```
  POZOR: architecture má víc downstream cílů (db-schema/backend/klienti dle flagů). Přeskočit
  architecture nelze prostým přemostěním na jeden uzel. **Proto preferuj judged-skip variantu:**
- **Zvolený mechanismus:** frontier označí `feasibility` a `architecture` jako **auto-skip**, když
  `flags.lightweight == true`. Implementace: rozšíř `frontier.py` partition tak, aby uzel s
  `skip_if: flags.lightweight` v definici dostal outcome PASS automaticky (analogie `judged-skip`,
  ale podmíněná predikátem, ne ručním `run.py skip`). Architektura jako producent `contract`:
  na lehké dráze NEVZNIKÁ kontrakt (podmínka no_new_contract to garantuje), takže downstream uzly,
  co `contract` konzumují, buď neběží (improvement bez kódu) nebo dostanou contract=absent —
  což u XS improvement (JSON/doc/rules edit) odpovídá realitě.
  - Nové pole uzlu v `delivery.yaml`: `skip_if: "flags.lightweight"` na `feasibility` a `architecture`.
  - `frontier.py`: při evaluaci uzlu, jehož `skip_if` predikát == TRUE → uzel se chová jako
    auto-PASS (přidej do completed+outcomes PASS, ne do ready/inflight). Tím AC-3 „automaticky
    označeny jako splněné".
  - C-checks (`check.py`): nové pole `skip_if` přidat do schématu uzlu (jinak C-validace spadne).

### Rozhodnutí 2.4 — Pojistka proti nesprávnému skipu

- Pokud kterýkoli ze tří signálů není splněn (default konzervativní), `lightweight` je false/unknown
  → `skip_if` predikát NENÍ TRUE → uzly běží standardně (AC-4: vlna s novým kontraktem / stack-impact
  projde feasibility+architecture normálně).
- `UNKNOWN` verdikt (`predicate.py`) u `skip_if` se chová jako **NEskipuj** (fail-safe: chybí-li
  flag, uzel běží). To je správný default — raději zbytečně spustit než nesprávně přeskočit.

### AC pokrytí #2
- AC-3: `flags.lightweight==true` → feasibility+architecture auto-PASS, graf jde na spec-gate dráhu. ✔
- AC-4: podmínka určena intake (zahájení vlny); chybějící/false signál → uzly běží. ✔

---

## FIX #3 — Kodifikace rozsahu agnostického pravidla

### Rozhodnutí 3.1 — Kam (přesně)

Dvě místa, dvě úrovně:

1. **`.agentic/constitution.md §Spec je stack-, agent- a impl-agnostická`** (řádek ~272-304) —
   **normativní zdroj.** Oprav řádek 303, který mixuje „akceptační kritérium" do spec-zákazů.
2. **`.agentic/agents/sheldon-spec.md`** — per-uzel rozsah (spec-gate vs spec-audit), aby persona
   nereflektovala rozpor. Sekce (A)/(B) už existují; zostřit rozsah.

PROJECT-CONSTITUTION.md **NEměnit** — agnostické pravidlo specu je framework-level (constitution),
ne projektová ústava (ta řeší CO projekt je). Grep potvrdil, že PROJECT-CONSTITUTION o spec-agnostice
nemluví. Držet to v `.agentic/constitution.md` (jeden zdroj).

### Rozhodnutí 3.2 — Znění (návrh, L-úroveň níže)

**Constitution — přidat explicitní rozsahovou větu** do `§Spec je stack-…agnostická`, hned za
nadpis (před výčet zákazů):

> **Rozsah pravidla:** Agnostické pravidlo se vztahuje výhradně na soubory specifikace (`specs/**`).
> **NEvztahuje se na akceptační kritéria (`acceptance/**`)** — ta smí a mají obsahovat konkrétní
> testovatelné termíny (názvy namespace, ověřovací příkazy, identifikátory), protože slouží
> testovatelnosti, ne čtení netechnickým PO. Mechanicky to vynucuje `spec-agnostic-scan.sh`,
> který skenuje jen spec adresáře a `acceptance/<feature>.md` strukturálně promíjí.

**Oprava řádku 303** (zdroj zmatku) — `„Nejde-li akceptační kritérium napsat bez…"` přeformulovat
na spec-rovinu:

> Nejde-li **chování ve specu** popsat bez některého z výše uvedeného, je formulované příliš nízko
> → přeformuluj na pozorovatelné chování. (Akceptační kritérium naopak BÝT konkrétní smí — testuje se.)

**sheldon-spec.md** — zostřit (A)/(B):

- (A) spec-gate `§Čistota check`: doplnit „**Rozsah: pouze `specs/**`.** Agnostiku v `acceptance/**`
  NEzdvihám — akceptační kritéria smí být technicky konkrétní (testovatelnost). To je úmysl, ne nález."
- (B) spec-audit: doplnit „**NEopakuji agnostiku** (tu řeší spec-gate na `specs/**`). spec-audit
  řeší výhradně **contract-mapping** (acceptance ↔ kontrakt, error kódy v registru). Vrácení na
  spec kvůli agnostice z tohoto uzlu = chyba rozsahu." (AC-6)

### AC pokrytí #3
- AC-5: constitution + skener jednoznačně: acceptance/ je mimo agnostiku. ✔
- AC-6: sheldon-spec (B) explicitně NEopakuje agnostiku → návrat na spec-gate jen kvůli mappingu. ✔

---

## FIX #4 — Reset loop-counterů při startu

### Rozhodnutí 4.1 — Přesná změna

`run.py` `mutate_state`, blok `if mode == "start"` (řádek 49-53):

```python
# PŘED (bug — dědí countery z předchozí vlny):
"counters": st.get("counters", {}) if st else {},

# PO (fresh start nuluje countery):
"counters": {},
```

Tím se `start` seed sladí s `runstate.fresh_result` (řádek 36: `"counters": {}`), který už je
korektní. Sjednocení = jeden zdroj defaultu.

### Rozhodnutí 4.2 — Sjednocení s fresh_result (anti-drift)

Seed dict v `run.py mode=="start"` je ručně duplikovaný literál `fresh_result`. Aby nedošlo
k dalšímu driftu (jako u counters), **`start` má volat `RunState.fresh_result(val)`** jako základ
a jen přepsat to, co `start` legitimně přebírá z předchozího stavu (dnes: NIC — counters byl jediný
carry-over a ten byl bug). Konkrétně:

```python
if mode == "start":
    st = RunState.fresh_result(val)          # jediný zdroj defaultu (vč. counters={})
    st["active_node"] = entry                # start seedne entry uzel
    # + nově: st["wave_base"] = git_rev_parse_head()   (FIX #1)
```

POZOR — `fresh_result` má `active_node: None`; `start` ho přepíše na `entry`. `wave_base` přidej
do `fresh_result` (nový klíč, default None) i sem. Tím má `start` i `fresh_result` identické schéma
+ pořadí klíčů (serializace stabilní).

### Rozhodnutí 4.3 — Ověření selftestem (AC-7)

Přidat do `selftest.sh` dva testy (vzor existujících `printf` scénářů):

- **AC-7(a) — nová vlna nuluje:** seedni `current-run.md` s `counters: {spec-gate->product: 9}`
  (nad limitem), spusť `run.sh start newrid`, ověř `grep -q "counters: {}" current-run.md`
  (nebo absence carry-over klíče). → countery vynulovány.
- **AC-7(b) — guard uvnitř vlny stále funguje:** existující F3 test (řádek ~212-220,
  `security->backend 3× = BLOCKER`) MUSÍ dál procházet — nezměněn. Ověřuje, že reset NEohrozil
  in-wave pojistku. Pokud chybí samostatné pokrytí, přidej: v rámci jedné vlny (bez `start`)
  bumpni counter 3× → BLOCKED.

### AC pokrytí #4
- AC-7(a): `start` → `counters={}`. ✔
- AC-7(b): bump-counter logika (`runstate.bump_counter`) nezměněna → in-wave guard drží. ✔

---

## Implementační pořadí (PO priorita + závislosti)

1. **FIX #4** — nejmenší, izolovaný (`run.py` 1 řádek + sjednocení + 1 selftest). Lze hned, paralelně s #3.
2. **FIX #3** — text-only (constitution + sheldon-spec), bez kódu. Paralelně s #4.
3. **FIX #1** — báze (`run.py start` + `wave_base`) → `preflight.sh` delta-resolve → `--files` ve 3 skenerech.
   PO chce první z funkčních; technicky závisí na FIX #4 sjednocení `fresh_result` (sdílí `wave_base` klíč),
   proto FIX #4 udělej před/spolu s #1.
4. **FIX #2** — až po #1 (sdílí `WAVE_BASE`/delta pro `no_new_contract` test + `git diff contracts/`).
   `delivery.yaml skip_if` + `frontier.py` auto-skip + intake envelope `lightweight` + `check.py` schéma.

Pozn.: FIX #1 a #4 sdílejí `wave_base`/`fresh_result` → udělat #4 sjednocení jako základ #1.

---

## Co se mění (soubor → fix)

| Soubor | Fix | Změna |
|---|---|---|
| `core/run.py` (`mutate_state` start blok) | #4, #1 | `counters={}`, volat `fresh_result`, přidat `wave_base=rev-parse HEAD` |
| `core/runstate.py` (`fresh_result`) | #4, #1 | přidat `wave_base: None` klíč (schéma parita) |
| `scripts/preflight.sh` | #1 | delta-resolve (WAVE_BASE env / current-run / fallback), `--delta`/`--full-scan`/`--wave-base`, předá `--files` |
| `scripts/spec-agnostic-scan.sh` | #1 | nový `--files FILE` (sken ∩ specs/), jinak full-scan |
| `scripts/format-check.sh` | #1 | nový `--files FILE` (sken ∩ stack soubory) |
| `scripts/file-size.sh` | #1 | nový `--files FILE` (sken ∩ zdrojáky) |
| `pipeline/delivery.yaml` | #2 | `skip_if: "flags.lightweight"` na feasibility+architecture; `desc` doplňky |
| `core/frontier.py` | #2 | auto-skip uzlu s pravdivým `skip_if` predikátem (PASS, mimo ready) |
| `core/check.py` | #2 | `skip_if` do schématu uzlu (C-validace) |
| intake mechanika (orchestrátor/Watson envelope) | #2 | intake emituje `flags: {lightweight, stack_impact, new_contract}` |
| `constitution.md §Spec…agnostická` | #3 | rozsahová věta (specs/ ano, acceptance/ ne) + oprava ř.303 |
| `agents/sheldon-spec.md` (A)/(B) | #3 | per-uzel rozsah, (B) neopakuje agnostiku |
| `scripts/pipeline/selftest.sh` | #4 | AC-7(a) reset test + ověř AC-7(b) in-wave guard |

---

## Otevřené body předané implementaci (rozhodnuto, ale pozor při kódu)

- **#1 čtení `wave_base` v bashi:** env-first (orchestrátor exportuje `WAVE_BASE`), fallback grep
  skaláru z `current-run.md`. Skener git NEčte — jen `preflight.sh`. Pokud implementace zvolí
  `run.sh status --field`, je to OK alternativa (čistší), ale není povinná.
- **#2 `condition_language: human-readable` v delivery.yaml meta:** ponech — `skip_if` flag-atom
  je v deterministicky vyhodnocené třídě predikátů (`PROJ_RE`/`CMP_RE`), takže běží i pod tímto
  framingem. Nepřepisuj meta na strojové (mimo scope této vlny).
- **#2 architecture jako producent `contract`:** lehká dráha garantuje no_new_contract, takže skip
  architecture nezpůsobí osiřelý downstream — XS improvement (JSON/doc/rules) `contract` nekonzumuje.
  Implementace ověř na vlně typu `i18n-cs-cleanup` (AC-3 ověření).
