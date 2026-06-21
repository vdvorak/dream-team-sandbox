---
cache_key: agentic-flow-v1.4
type: normative-root
last_updated: 2026-06-18
---

# Agentic Flow — Mechanika

Tento dokument popisuje **jak** agenti spolu interagují. Principy jsou v
`constitution.md`. Definice jednotlivých rolí v `agents/`.

> **Strojová podoba:** `pipeline/delivery.yaml` zachycuje tento flow jako deklarativní
> stavový graf. **Uzly = ROLE** (`product`/`architecture`/`backend`/…, ne osoby); pole
> `agent:` je **cast binding** — persona (short), která roli plní. Hrany drátují role →
> graf je modifikovatelný vizuálním editorem a výměna agenta na roli je změna bindingu, ne
> grafu. Próza zde zůstává **lidský zdroj pravdy** (validovaná 1:1 přes `run.sh check`); graf
> je její strojový executor (běží reálně přes runner). Mechanika: §Deterministický dispatch níže.
>
> **Pozn. ke jménům:** próza níže používá **persony** (Vision, Ted, Bob, Joey…) pedagogicky —
> jsou zapamatovatelné. Mapování persona ↔ role (uzel grafu) je v `agents/INDEX.md §Cast`.
> Když text říká „Vision", myslí roli `product`; routing vždy žije v grafu, ne v personě.

## Tři transformace

Práce vždy prochází těmito třemi fázemi v pořadí. Přechod mezi nimi je
explicitní (handoff dokument).

### T1: Idea → Spec
**Cíl:** převést user request na testovatelnou specifikaci a contractuální
rámec.

**Vlastníci:**
- **Vision** (PO) — feature spec, acceptance criteria, scope rozhodnutí
- **Tony** (CTO) — tech-feasibility schválení
- **Denisa** (UX) — user flow + **statický HTML mockup** `design/<feature>/mockup.html`
  (pokud feature má UI); mockup používá komponenty z `design/manual/` (Leonard)

**Výstup T1:** spec v `specs/<feature>.md`, acceptance v `acceptance/<feature>.md`,
volitelně mockup v `design/<feature>/mockup.html`. Vše schválené Tonym.

### T2: Spec → Code
**Cíl:** implementovat spec do kódu + unit testů + contractů.

**Vlastníci v sekvenci:**
- **Ted** (Architect) — API contract design, error codes, reuse decision pass
- **Chandler** (DB) — DB schema, migrace (paralelně s Ted, pokud DB hraje roli)
- **Leonard** (UI) — shared UI komponenty (po Denisa wireframes)
- **Bob** (Backend Dev) — server kód + unit testy
- **Peter** (Web Dev) — frontend page kód + unit testy

**Výstup T2:** kód v `server/`, `clients/<target>/`; unit testy zelené;
contracts aktualizované.

### T3: Code → Ověření
**Cíl:** nezávisle ověřit, že kód odpovídá spec + nepřinesl regresi +
splňuje NFR.

**Vlastníci:**
- **Joey** (QA) — integration / system testy proti acceptance criteria (funkční)
- **Optimus** (Performance) — perf testy kritických cest
- **Sheldon** (Spec Auditor) — konzistence specs/contracts
- **Heimdall** (Security Auditor) — F1–F8 kontroly (dle `constitution.md §Bezpečnostní checklist`)
- **Vitek** (Code Quality Auditor) — code hygiene kontroly
- **Edna** (Design Auditor) — design conformance vůči mockupu + manuálu
  (jen pokud feature má UI)

**Výstup T3:** všechny gates PASS; feature DONE; STATE.md aktualizovaný.

---

## Orchestrator vs Subagent split (KRITICKÉ)

**Main session (kterou user vidí) je ORCHESTRÁTOR, ne agent.** Žádný
agent se nikdy nespouští „v hlavní konverzaci" — všichni jsou vyvolaní
jako **izolovaný subagent** s vlastním čerstvým kontextem.

### Proč
- Bez izolace by **každý agent dědil veškerou předchozí konverzaci**
  (Watson otázky, Vision spec, Ted contract, …). Kontext se kumuluje,
  cost roste, kvalita rozhodování klesá.
- Princip „minimální vstupní kontrakt" (D3 z constitution) by byl porušen
- Hand-off dokumenty by ztratily smysl — agent by viděl víc než handoff říká

### Jak (per tool)

| Nástroj | Mechanismus izolace |
|---|---|
| **Claude Code** | `Agent` tool s `subagent_type=<short>`; každý agent má wrapper v `.claude/agents/<short>.md` generovaný z `.agentic/agents/<short>.md` (viz `scripts/setup/setup-claude-code.sh`). Subagent dostane vlastní fresh context, vrátí jediný structured výsledek. |
| **Cursor** | Per-mode rules v `.cursor/rules/<short>.mdc` — každý mód má vlastní system prompt; uživatel přepíná módy. |
| **Aider** | Každý `aider --read .agentic/agents/<short>.md --message "..."` je samostatná invocation s čistým kontextem. |
| **Claude API** | Každý agent call = nový messages thread; system prompt = `.agentic/agents/<short>.md` content. |

**Per-tool bootstrap je generovaný tenký adaptér.** `CLAUDE.md`, `.cursorrules`,
`.aider.conf.yml` vznikají ze `scripts/setup/setup-*.sh` nad neutrálním kontraktem
(`constitution.md` + tento `flow.md` + `agents/INDEX.md`). Orchestrační logika
(kdo je další, keyword triggery, model routing, gates) žije **zde**, ne v adaptéru —
adaptér nese jen tool-specific invocation (jak vyvolat subagenta) a needituje se ručně.
Tím je „mozek" flow v neutrálních souborech a nástroj je vyměnitelný (cíl
`pipeline-architecture.md §Tool-agnostický kontrakt`).

### Co main session DĚLÁ
- Čte handoff dokumenty v `handoffs/<wave-id>/`
- Klasifikuje user request (nová feature / bugfix / improvement)
- Dispatchuje konkrétního subagenta s konkrétním vstupem
- Schvaluje L2 nálezy (ukáže user shrnutí)
- Eskaluje L3 (vyžádá AskUserQuestion nebo zastaví)
- **Nepřebírá identitu agenta** sama

### Co main session NEDĚLÁ
- Nepíše spec sama (to je Vision subagent)
- Nepíše kód sama (to je Bob/Peter subagent)
- Nepíše testy sama (Joey)
- Nepřebírá Watson interview sama (viz výjimka níže)

### Konverzační meta-agenti — embody vs dispatch

**Watson** (interview) a **Monk** (meditace/ideace) jsou konverzační meta-agenti: jejich
hodnota je v **vícekolovém dialogu** se živým uživatelem. Subagent přes Agent tool je
one-shot izolovaný kontext — uživatel promluví, agent odpoví, kontext zmizí. Pro iterativní
interview nebo meditaci je to nemotorné.

Pravidlo: **embody pro interaktivní dialog, dispatch pro one-shot.**

| Situace | Mechanismus |
|---|---|
| **Watson setup interview** — iterativní sběr požadavků, otázka–odpověď | Orchestrátor **vtělí Watson** přímo do hlavní session (přečte jeho agent definici, chová se jako Watson po dobu dialogu) |
| **Monk ideace / meditace** — vícekolový brainstorming s uživatelem | Orchestrátor **vtělí Monk** přímo do hlavní session |
| **Watson session-resume** — jednorázový status report (přečti STATE.md, shrň stav) | Standardní **dispatch jako subagent** (`Agent(subagent_type="watson-interviewer", …)`) |
| **Všichni dodávkoví agenti** (Vision, Ted, Bob, Peter, Joey, …) | Vždy **dispatch jako subagent** — fresh izolovaný kontext je žádoucí |

Důvod carve-outu: bez izolace dodávkových agentů by dědili veškerý kontext (cost + kvalita).
U konverzačních meta-agentů je právě sdílený kontext s uživatelem ta hodnota — přerušení
po každé odpovědi by dialog rozbilo.

**Wrappery `.claude/agents/watson-interviewer.md` a `.claude/agents/monk-ideation.md` se
NERUŠÍ** — Watson se i nadále volá jako subagent pro session-resume; mění se jen to, *kdy*
embody vs dispatch.

### Vyvolání subagenta — minimální vstupní balíček

Při invokaci subagenta orchestrátor předává:
1. **Task description** — co konkrétně udělat (1-3 věty)
2. **Reference na handoff** — předchozí handoff dokument (cesta), pokud existuje
3. **Relevantní řezy** — sekce specs/contracts/rules (ne celé soubory)
4. **Decided list** — rozhodnutí výše ve flow, která subagent NEopakuje

Tj. ne „přečti celý projekt a dělej spec" — ale „čti `specs/X.md`, použij
rules §Y, vytvoř Z".

---

## Auto-dispatch (kdo je další)

Orchestrátor (main session) čte handoff dokumenty s polem `returns_to:`
nebo `to:` a vyvolá dalšího agenta jako subagent. Uživatel není
orchestrátor — je zadavatel a schvalovatel u gates.

**Dispatch logika:**
1. User submit request → orchestrátor klasifikuje (nový feature? bugfix? improvement?)
2. **Nový feature** → vyvolat **Vision** subagent
3. **Bugfix s failure signature** → return path, vyvolat vlastníka artefaktu
4. **Bugfix bez signature** → vyvolat Vision (potřebujeme spec pro bugfix)
5. **Improvement** → Tony nebo Ted subagent podle scope
6. Po vrácení výstupu subagenta → orchestrátor přečte jeho handoff, zjistí
   `to: <next-agent>`, vyvolá dalšího subagenta

**User-as-agent override:**
Před každým subagent invoke orchestrátor zkontroluje, jestli user dodal
manuální vstup pro danou roli (např. „architektura: X" v původním requestu).
Ano → použít user input místo subagent invoke. Ne → invokovat subagent.

## Deterministický dispatch (runner)

> **Pracovní adresář (cwd) — VŽDY kořen repa.** `run.sh` (→ `core/run.py`) řeší `current-run.md`
> i `runs/<run-id>/ledger.yaml` jako **cwd-relativní** cesty (žádný project-root marker). Kanonické
> úložiště je **kořen repa** (adresář s `project-config.md`) — tam žijí všechny vlny (`runs/`) i runtime
> `current-run.md`. Spuštění byť jediného `run.sh done`/`start` z jiného cwd (typicky `.agentic/`)
> **tiše rozštěpí stav** do druhé kopie (`.agentic/current-run.md` + `.agentic/runs/`) → projeví se jako
> `class: null` / `completed: []` / „zmizelý" ledger záznam. Každý `run.sh` call invokuj z kořene repa
> (cwd persistuje mezi shell voláními — jediný dřívější `cd .agentic` to zlomí). Pozn.: `pytest` runneru je
> NAOPAK z `.agentic/` (cwd-citlivé structure-check) — nezaměnit.

Routing a stav **nedělej z hlavy** — počítej je scriptem (determinismus, žádný vibe).
Próza výše je lidská spec téhož; runner ji vykonává nad `pipeline/delivery.yaml` +
`current-run.md`. Routing je **dataflow**, ne jedna linka:

> **Ready-rule:** uzel je *ready*, když doběhli všichni jeho **aktivní producenti**
> (příchozí forward hrany, flag-live, ne `return`). Frontier = množina všech ready uzlů.

Jedno pravidlo pohltí fan-out (víc uzlů ready zároveň), fork (nezávislá linka = další
ready uzel) i join/confluence (uzel s víc producenty je ready, až doběhnou **všichni**).
`kind: fork`/`fan-out` v grafu jsou **lidská anotace záměru**, ne direktiva pro scheduler.
Vypnutý uzel (target/flag-gating) se nikdy nestane ready a nikoho neblokuje. Orchestrátor
(LLM teď, app potom) drží tuhle smyčku:

1. **Drive** — `scripts/pipeline/run.sh drive` ze stavu spočítá frontier a vydá **celou
   ready množinu jako akce** (paralelní tracky = víc současně dispatchovatelných uzlů):
   - `DISPATCH <node>` — agent/gate uzel; **víc naráz = paralelně** (zapíše do `frontier`
     jako inflight, ať se nedispatchne dvakrát). **Model** = `model_overrides[node]` (Tony
     triage, hvězdička `*`) ∨ statický grafový default — deterministicky ze stavu, ne ruční
     honorování orchestrátorem (B3).
   - `HUMAN-GATE <node>` — non-blocking (L2): čeká na člověka, ale **frontier jede dál**
     (ostatní ready uzly se dispatchnou souběžně).
   - `HALT <node>` — blocking (L3, deploy-approve): **zastaví celý běh** na explicitní
     ano/ne (destruktivní krok, constitution §8), i kdyby teoreticky bylo co dělat paralelně.
     `APPROVED` → běh pokračuje; `REJECTED` → běh zastaven (`status: blocked`, žádný deploy).
   - `DECIDE` — ready prázdné a čeká úsudek: free-text/judgment hrana (vyber dle reálného
     nálezu) nebo klasifikace intake. Orchestrátor buď uzel dispatchne, nebo `run.sh skip
     <node>` (judged-skip: uzel netřeba → frontier ho přestane počítat jako producenta).
   - `DONE` — dosažen terminal, běh u konce (`drive` projde i join/router bez práce).
   - `BLOCKED` — frontier prázdný, nic ready/inflight/judgment a není terminal → graf drhne
     (potřeba return/oprava).
2. **Dispatch** — vyvolej subagenta uzlu (per-tool: Claude Code `Agent(subagent_type=…)`).
   **`subagent_type` = uzlův `agent:` short z `drive` výstupu** (cast binding role→persona, který
   engine už vyřešil a vytiskl jako `→ agent:<short>`) — **NIKDY node-id / název role**. Role≠persona
   se běžně liší (uzel `design-audit` → agent `edna-design`, `ui-system` → `leonard-ui`, `ux-design`
   → `denisa-ux`); předání node-id selže („agent type not found"). Engine binding vybral za tebe;
   orchestrátor jen opíše `agent:` pole, nehádá personu. Mapování i v `agents/INDEX.md §Cast`.
   Se scaffoldem: `run.sh scaffold …` → předá kostru jako typovaný vstup.
3. **Dokončení uzlu** — subagent vrátí node-result obálku → `run.sh done <envelope>`
   (= „/done"): ověří typy, zapíše do `runs/<run>/ledger.yaml`, posune stav (uzel pryč
   z `frontier`/inflight, `completed += node`, `outcomes[node]`) → zpět na krok 1.
   - **Most handoff→envelope (deterministický, F3):** orchestrátor NEmapuje výstupy na typy
     z hlavy (divergence-zdroj). `result.sh` **auto-derivuje z grafu** — output typy uzlu,
     `agent`, `phase` (graf = zdroj pravdy). Orchestrátor dodá jen **judgment**: minimal
     envelope = `{run, node, outcome}`, plus dle role `changed`/`flags`/`severity`/`fault`/`models`.
     Explicitní `outputs` s `path` přebijí auto-derive → B1 path-check drží. `time` volitelné
     (chybí → `seconds=0`, honest „neměřeno", ne fabrikace). Schéma: `templates/node-result.md`.
   - **HUMAN-GATE continuation:** lidská odpověď = node-result přes `run.sh done` (gate uzel;
     outcome věrně z interakce — `ACK` L2 / `APPROVED`|`REJECTED` L3; bez typovaného outputu).
     Tím se gate uvolní (z `awaiting_human` / `halt_gate`) a `drive` routuje dál.
   - **FAIL+return** (gate FAIL → vlastník): gate dodá `(returns_to, severity, signature)`,
     engine přechod počítá deterministicky (žádný úsudek orchestrátora):
     - **Auditor vrací úplný nález naráz** (ne po dávkách) — viz `constitution.md §Auditor vrací
       úplný nález`. Read-only gate (spec-čistota, bezpečnost, kvalita, design, výkon) v jednom
       FAILu vyjmenuje **všechny** výskyty svého druhu nálezu přes celý scope vlny. Opakovaný return
       téhož druhu nálezu z téhož auditora vyčerpává return-counter (3× = BLOCKER) na něčem, co měl
       jeden úplný výpis vyřešit napoprvé → je to vada auditu, ne legitimní iterace.
     - `severity: blocking` (default) → re-flow: un-complete **jen cíl** (counter++, 3× = BLOCKER).
       Downstream se NEinvaliduje eagerně — přepočítá se **lazily přes incremental rebuild** (viz
       níže), aby doc-only fix nere-floutl celý forward-closure. `signature` (failure-signature) jde
       do `return_payload[cíl]` → `drive` ho vytiskne při re-dispatchi (`↻ re-flow finding:`),
       takže re-běh dostane CO opravit **ze stavu, ne z paměti orchestrátora**. Po úspěšném
       re-běhu cíle se payload smaže; `findings` (append-only ledger) si nález nechá pro l2-review.
     - `severity: advisory` → non-blocking nález: uzel je **hotov** (join pokračuje), nález jen
       zaznamenán do `findings`. **Žádný re-flow.** Odděluje kosmetický nález (spec-čistota) od
       blokujícího (security) — rozhodnutí je VSTUP gate, ne úsudek drive.
     - **Incremental rebuild (scoped re-flow) + order-independence:** uzel se přepočítá, **jen
       když se mu reálně změnil vstup** (model Make/Bazel). Každé `done` orazítkuje verzí (`epoch`)
       změněné output-typy (`type_versions`) a vlastní uzel (`node_versions`); default (chybí
       `changed`) = všechny output-typy uzlu → plný downstream re-flow, ale lazily. Uzel M je
       **stale** ⟺ ∃ jeho vstupní typ má novější verzi než M (`node_versions[M]`). Tím doc-only fix
       (`changed:[spec]`) re-runne JEN spec-konzumenty, ne celý forward-closure (řeší E1-depth: dřív
       1 řádek dokumentu re-floutl 24 uzlů). Verze monotonní → **order-independent**: pozdě
       zpracovaná completion neresurektne stale uzel (vstupní verze přebije jeho node-verzi). Staré
       seedy bez verzí → graceful fallback na „producent musí být completed" (downward-closure).
     - **Re-flow staleness je tranzitivní (verifikační uzly znovu proběhnou):** vrátí-li audit/gate
       FAIL re-flow na **implementační** uzel (libovolná produkující role: server, web, klient,
       UI-systém, schéma…) a ten změní implementaci, **musí zestárnout celý downstream řetěz, který
       z té implementace vychází — včetně ověřovacích uzlů** (funkční testy, mechanický lint). Ty se
       po opravě **znovu spustí PŘED uzávěrem vlny**; jinak proklouzne regrese (oprava shodí testy,
       co už byly „hotové"). Invariant: completed uzel je stale nejen když má vstup novější verzi, ale
       i **když kterýkoli jeho aktivní producent přestal být platný** (downward-closure platí i pro
       verzovaný uzel) — protože pouhé un-completnutí producenta jeho výstupní typ nepřeverzuje,
       dokud reálně neproběhne. Tím se staleness šíří řetězem produkce→ověření, ne jen o krok.
4. **Konec runu** — `run.sh summary` → čas + kredity (`runs/<run>/summary.md`).

(`run.sh status`/`next` zůstávají pro ruční inspekci; `drive` je sjednocuje do smyčky.)

Integritu grafu hlídá `run.sh check` (C1–C12, vč. strict-SDD a dataflow-reachability —
každý uzel má forward producenta, `join.requires` je odvoditelný z hran). LLM tedy dodává
**úsudek a obsah uzlů**, ne routing/stav — ty jsou deterministické a v souborech
(proto session kdykoli naváže: `status` řekne, kde to je).

> **Řídí přes rozhraní, ne přes vnitřek** (operační projekce axiomu §Filozofie #8).
> Při feature/bugfix/improvement orchestrátor řídí flow **výhradně přes povely runneru** (drive →
> dispatch → done) a **kontraktní vrstvu** (axiomy, tento flow, katalog rolí, šablony výstupů). Tvar,
> který runner potřebuje — typy výstupů uzlu, obálka výsledku, model uzlu — **derivuje runner sám**
> a vrací ho jako odpověď povelu; orchestrátor ho čte odtud, **ne ze čtení vnitřní stavby nástroje**.
> Když rozhraní potřebné nedá (povel to neumí, kontrakt mlčí), je to `BLOCKED`/STOP → **vytáhni to
> jako mezeru v enginu**, nedohaduj ji reverse-engineeringem implementace. Vnitřek nástroje se čte a
> upravuje jen tehdy, je-li předmětem práce **sám engine nebo flow** — ne dodávka aplikace.

## Keyword triggery (orchestrátor reaguje na tato slova)

Tato tabulka platí pro všechny nástroje. Mechanismus invokace se liší
(Claude Code: `Agent(subagent_type=...)`, Cursor: inline ritual, Aider:
manuální krok) — co se invokuje je vždy stejné.

| Uživatel řekne | Orchestrátor vyvolá | Poznámka |
|---|---|---|
| `handoff` / `zapiš handoff` / `konec session` | `watson-interviewer` (handoff mode) | Watson zachytí stav session a zapíše `STATE.md` + handoff dokument |
| `zavolej Watson` / `Watson` | `watson-interviewer` (detect mode) | Watson detekuje stav projektu a zvolí mód (setup / session-resume) |
| nový feature request | `vision-po` | Vision napíše spec |
| `přidej agenta` / `audit agentů` / `Eywa` | `eywa-meta` | Eywa spravuje agent systém |

**Session start** (každá nová session, před přijetím prvního úkolu):
→ orchestrátor automaticky invokuje `watson-interviewer` pro orientaci.
Watson v COMPLETE projektu: rychlý status report (STATE.md + poslední handoff).
Watson v novém projektu (SKELETON_NEEDS_WATSON): spustí setup interview.

---

## Schvalovací úrovně (L0 / L1 / L2 / L3)

| Úroveň | Kdo schvaluje | Co | Kdy |
|---|---|---|---|
| **L0 — Auto** | žádný (handoff jde sám) | implementační kroky uvnitř scope, technické detaily | default |
| **L1 — Inter-agent gate** | druhý AI agent | spec dokončen (Tony validuje), contract dokončen (Architect), kód hotov (Joey), perf zelený (Optimus) | po každé transformaci |
| **L2 — Informativní (user vidí)** | user (jen view, nezdržuje) | velký commit, dokončený feature před finálním audit, finální handoff vlny | default + opt-out per session |
| **L3 — Lidský souhlas (blokuje)** | user (musí říct ano) | destruktivní operace, breaking contract changes, kontroverzní rozhodnutí, BLOCKER který agent nemůže rozseknout | vždy, žádný opt-out |

### Příklady gate aktivací

```
Vision píše spec → L1 (Tony tech-feasibility) → OK → pokračování T1
Ted navrhne breaking contract change → L3 (user schválí migrační plán)
Chandler chce DROP COLUMN → L3 (user schválí — destruktivní)
Bob/Peter implementace hotová → L1 (Joey integration test) → fail →
  Joey vrací TEDOVI (diagnostik) s failure signature → Ted určí vlastníka opravy
  (Bob/Chandler/…) nebo eskaluje na Vision; Joey naslepo sám nediagnostikuje
Joey OK → L1 (paralelně Optimus, Heimdall, Vitek) → OK →
  L2 (user vidí finální handoff) → merge
```

---

## Handoff dokument — formát

Zapisuje se do `handoffs/<wave-id>/<from>-to-<to>.md` na konci
každého kroku. Watson navíc přepíše pointer `handoffs/LATEST` (jednořádková
relativní cesta k právě zapsanému handoffu) — to je strojový zdroj pravdy
pro „poslední handoff" při session-resume (nahrazuje hádání podle mtime/názvu,
které přepisuje agentic-sync/git/kopie).

Šablona v `templates/handoff.md`. Povinné sekce:

```yaml
---
wave: <wave-id>
from: <agent-short>
to: <agent-short>
type: spec-completed | contract-completed | impl-completed | tests-completed | ...
returns_to: null  # nebo agent-short pokud BLOCKER vrácení
---

# Handoff: <From> → <To>

## Stav (jak chápu situaci)
...

## Plán (co dělám / udělal)
...

## Výsledek
- soubor (vytvořen|upraven)
- check (OK|FAIL)
- ...

## Decided (rozhodnutí, která následný agent neopakuje)
- ...

## Slabé místo
... (povinné; pokud žádné, napsat „bez slabin" — to je signál k pozornosti)

## === GATE OUTPUT ===
agent: <agent-short>
phase: <T1|T2|T3>
<base-row-1>: OK|FAIL|...
<base-row-2>: ...
write-scope: RESPECTED|VIOLATED
returns-to: <agent-short>
weak-spot: <one-line nebo none>
<per-agent-row-1>: ...
==================
```

### Failure signature (return packet)

Zvláštní typ handoffu při vrácení mezi agenty (např. QA bug → Dev).
Šablona v `templates/failure-signature.md`.

Inkrementuje counter v `wave-id` namespace. 3× identická failure signature
= BLOCKER eskalace na vyšší agent (z Dev → Architect; z QA → PO).

---

## GATE OUTPUT — base block

```
=== GATE OUTPUT ===
agent: <short>
phase: <T1|T2|T3|gate>
<main-check>: OK | FAIL — <důvod>
write-scope: RESPECTED | VIOLATED
returns-to: <next-agent-short>
weak-spot: <one-line>
[per-agent specific rows]
==================
```

Každý agent má v `agents/<role>.md` sekci „Formát výstupu", která
specifikuje per-agent specifické řádky. GATE OUTPUT bez všech povinných
řádků = checkpoint nesplněn.

---

## Pravidla pro design

### Setup projektu — design manuál

Pokud má projekt UI, součástí setupu je základní design manuál. Postup dle znalostí uživatele:

- **Uživatel ví, co chce** (dodá mockup/brief) → Watson zachytí `design_source: intake`; Denisa ověří
  a zaregistruje podklad; Leonard zhmotní manuál do `design/manual/`.
- **Uživatel neví / nechá na nás** → Watson zapíše `design_source: author`; Denisa iniciuje
  **mockup-konzultaci** (navrhne vizuální směr → zapracuje připomínky) → po **schválení uživatelem (L3)**
  předá podklad Leonardovi → Leonard sestaví `design/manual/` (tokeny + komponenty + `index.html`).

Výsledek je závazný základ pro všechny následující features.

### Trigger: nová komponenta → manuál před T2

Každá nová komponenta v mockupu (Denisa) **musí být zdokumentována v `design/manual/`
(Leonard) PŘED vstupem do T2** (Spec→Code). Mockup s neregistrovanou komponentou =
nález `mockup-uses-manual-components: MISSING` → BLOCKER. T2 nesmí začít, dokud Leonard
komponentu nezapíše.

### Edna audituje obousměrně

Edna kontroluje konformitu v obou směrech:

1. **Implementace vs manuál + mockup** — standardní conformance audit (T3).
2. **Manuál vs realita** — flaguje „manuál zaostal za realitou": komponenta se používá v
   implementaci nebo mockupu, ale v manuálu chybí nebo je zastaralá → nález
   `manual-conformance: STALE — <komponenta>` (advisory, není blocker pro aktuální feature,
   ale Leonard ji musí dohnat před další T2).

---

## Stop body (povinné gates)

Auto-dispatch se nesmí přes tyto body posunout bez gate PASS. Brány níže mají **uzel
v grafu** (`pipeline/delivery.yaml`); soulad próza↔graf hlídá `run.sh check` C16 přes
`meta.prose_gates` (drift „slíbená brána bez uzlu" už neprojde tiše):

1. **Po zápisu do `specs/`** → **raná spec brána** (uzel `spec-gate`): mechanika
   (`preflight --mode spec`: agnostika / line-refs / i18n) + Sheldon **intrinsic** kontrola
   (čistota / struktura / brevity); FAIL → return na `product`. Pak tech-feasibility (Tony).
   Tato brána NEřeší contract-mapping — to je až T3 `spec-audit` (viz níže).
2. **Po zápisu do `contracts/`** → spec ↔ contract mapping (T3 `spec-audit`, Sheldon)
   + breaking change check (Tony L3 pokud breaking)
3. **Po zápisu do `rules/` nebo `stack/`** → spec-konzistence (raná spec brána `spec-gate`)
4. **Po zápisu kódu, PŘED audity** → **lint gate** (uzel `code-lint`, mechanická brána, viz §Lint gate)
5. **Před T2 (Spec→Code), pokud feature má UI** → **design gate**: každá nová komponenta z mockupu
   musí být v `design/manual/` (Leonard); viz §Pravidla pro design
6. **Před deploymentem** → funkční gate (Joey PASS) + audit gate (Sheldon + Heimdall +
   Vitek + Optimus) všichni PASS; Edna PASS pokud feature má UI
7. **Před destruktivní operací** → L3 lidský souhlas

## Lint gate (stroj před úsudkem)

Lintery jsou **tvrdá mechanická brána**, ne úsudek auditora. Po zápisu kódu a **před** vstupem
do T3 auditů běží uzel `code-lint` (`scripts/preflight.sh --mode code` = agregátor: `format-check`
+ `file-size`). Musí projít zeleně (exit 0). FAIL = re-flow na vlastníka kódu (Bob/Peter) s
`--fix`; qa ani T3 audity se nespustí, dokud lint nesvítí. „Linter to chytí, ne oko."

Symetricky rané spec brány (`spec-gate`) volají `scripts/preflight.sh --mode spec` (agregátor
spec linterů: `spec-agnostic-scan` + `find-line-refs` + `i18n-scan`) — týž princip „stroj před
úsudkem" pro spec před tím, než ji Sheldon čte intrinsic.

| Stack | Nástroj | Chytá (mimo jiné) |
|---|---|---|
| Python | `ruff` (check + format) | F401 unused import, F841 unused var, dead code, řazení, formát |
| Web (TS/TSX) | `prettier` + `eslint` | nepoužité vars/importy, style, formát |

**Nepoužité proměnné / importy = BLOCKER** — rozhoduje exit-code linteru, ne posouzení agenta.
Konfigy (`ruff`/`eslint`/`prettier`) jsou součást stack scaffoldu; tento gate je jen vynucuje.
Vitek bere výsledek linteru jako **vstup** (nedubluje ho okem) — viz `agents/vitek-quality.md §2`.

---

## Cost policy

- Default sekvenční dispatch (jeden agent po druhém)
- Paralela jen při **explicitně nezávislém scope**:
  - Bob (server) || Peter (web) — write scope nepřekrývá
  - Sheldon || Heimdall || Vitek (auditoři) — všichni read-only
- Stejné soubory nečíst paralelně ve více agentech
- Minimální vstupní kontrakt: každý agent má v definici „Vstupy" s
  rozsahem (řez/celý). Default: < 200 ř = celý, jinak řez.
- **Right-sized model**: model dle složitosti úkolu (viz §Model routing) — levný na banální práci, drahý jen na úsudek, komplexní úkol rozložit pro levnější modely.

---

## Model routing (rubrika složitosti)

Druhá osa dispatchu vedle activation profilů: profil (`agents/INDEX.md
§Activation profily`) určuje, *kteří* agenti jsou aktivní; rubrika níže určuje,
na *jakém modelu* konkrétní úkol běží. Cíl jako Cursor „auto" mód: levný model
na banální práci, drahý jen tam, kde rozhoduje úsudek.

**Signály složitosti** (levně vyhodnotitelné před delegací): počet dotčených
souborů, odhad LOC, počet vrstev/concernů, jednoznačnost specu, blast radius
(contract / shared / security / data / migrace), novost (následuje existující
rule vs. nový pattern).

**Tier prior se NEHÁDÁ od nuly — odvozuje ho skript.** Před dispatchem (resp. při Tony triage)
zavolej `scripts/complexity-estimate.sh [soubory…]` (bez argumentů vezme `git diff`): files/loc/
sensitive → deterministický prior **XS/S/M/L**. Je to **standardní krok**, ne ad-hoc: orchestrátor
ho bere jako VSTUP a pak jen **koriguje úsudkem** signály, které skript nevidí (jednoznačnost specu,
blast radius, novost patternu, sensitive nuance) — nepočítá tier od základu. Skript je explicitně
„prior, ne verdikt" (sensitive flag = „nepodstřelovat"). Pro intake jsou priory zabalené v
`scripts/intake-signals.sh` (tier_prior + deterministický `has_signature`).

| Tier | Model | Kdy |
|---|---|---|
| **XS** triviální | `haiku` | 1 soubor, < ~30 LOC, nulová nejednoznačnost, žádný contract/security/data dopad, čistě následuje existující pattern (rename, oprava textu/komentáře, config/doc tweak, deterministický refactor krytý testy) |
| **S** malý | `sonnet` | 1–2 soubory, jasný spec, jedna vrstva, drží se rules, žádný breaking/contract/security |
| **M** standardní | `sonnet` | multi-file v rámci jedné komponenty, běžná implementace dle blueprintu, drobná rozhodnutí uvnitř funkce/modulu (výchozí pracovní tier) |
| **L** komplexní | `opus` **nebo dekompozice** | cross-cutting, nejednoznačné, dotýká se contractů/security/dat/migrací, nový pattern, velký blast radius nebo objem |

**Pravidlo dekompozice (jádro úspory):** když úkol vyjde **L**, orchestrátor
(resp. Tony při triage) **nejdřív zkusí rozložit** na S/M podúkoly, které utáhne
levnější model; `opus` se rezervuje jen na neredukovatelné jádro úsudku
(architektonické / security rozhodnutí). Navazuje na T1/T2/T3, waves a Vision
spec >400 ř. = split (`constitution.md §Brevity`).

**Default vs override.** Každý agent má výchozí tier ve frontmatteru (`agents/<short>.md §model`; přehled v `agents/INDEX.md §Model strategy`) = výchozí strop. Orchestrátor ho dle rubriky smí **snížit** (triviální instance → `haiku`) nebo **zvýšit** (záludná → `opus`).

Per-nástroj mechanismus override (přebije default z frontmatteru):
- **Claude Code (≥2.0):** Task/Agent tool má parametr `model` — orchestrátor ho předá při dispatchu: `Agent(subagent_type="bob-backend", model="haiku", prompt=...)`. Default ve wrapperu `.claude/agents/<short>.md` (generuje `setup-claude-code.sh` z pole `model:`) je fallback/strop. Pozn.: oficiální docs override per-volání zatím neuvádí, ale Task tool ho má.
- **Cursor:** model per mód — override = volba módu.
- **Aider / Claude API:** `--model` resp. `model` parametr per invokaci.

Když nástroj override neumí, projeví se snížení volbou agenta + dekompozicí (L → S/M podúkoly na levnějších modelech).

**Eskalace při selhání (bezpečný downgrade).** Snižovat tier je bezpečné jen s pojistkou: když agent na levnějším modelu narazí na opakovaný fail, orchestrátor **jednou zvýší model o stupeň** (`haiku`→`sonnet`→`opus`) a teprve pak BLOCKER (viz `constitution.md §Kritická pravidla #2`). Fail levného modelu = upgrade, ne rovnou eskalace na člověka.

**Haiku — konkrétní use-cases.** Věci nehodné sonnetu, ale neskriptovatelné: draft commit message / CHANGELOG entry, rename napříč soubory dle jasného vzoru, shrnutí handoffu, doc/komentář tweak, mechanická úprava textu specu. Orchestrátor je dispatchne s `model="haiku"`.

**Měření.** Routing se **NEpíše ručně** — derivuje se z ledgeru (`runs/<run>/ledger.yaml`, jediný zdroj pravdy, který engine plní z každého `done`). Wave/agent/model/cost jsou deterministická data, co engine zná v okamžiku dispatchu/done; jediný úsudkový kousek je `tier` (XS/S/M/L) — ten orchestrátor dodá jako pole envelope (`tier:` v `node-result`), zbytek se odvodí. Skladbu modelů + tier rozpad + odhad úspory dá `scripts/model-usage.sh` (čte ledger; bez argumentu vezme `run` z `current-run.md`). Levný prior tieru z diffu `scripts/complexity-estimate.sh`; dekompozici L šablona `templates/work-breakdown.md`. (Měřená telemetrie — tokeny/čas — se propisuje do envelope z `<usage>` bloku Agent toolu, viz `templates/node-result.md`; nikdy z hlavy.)

---

## Wave (iterace)

Wave = jedna ucelená change set. Žádné časové ohraničení (kanban-style).
Wave končí, když:
- Acceptance criteria splněna (Joey OK)
- Auditoři PASS (Sheldon + Heimdall + Vitek)
- STATE.md aktualizovaný
- Wave handoff uložen

Wave ID: `<YYYY-MM-DD>-<feature-slug>` (např. `2026-05-27-export-pdf`).
Adresář handoffů: `handoffs/2026-05-27-export-pdf/`.

Při paralelně běžících waves (vzácné, viz Cost policy): různé wave-id.

---

## STATE.md — průběžný stav projektu

Vlastní orchestrátor (nástroj/Claude Code session) + Tony (CTO schvaluje
větší změny).

**Dvě vrstvy — fakta vs příběh:**
- **Strojová fakta o uzavřených vlnách** — blok `<!-- ENGINE:STATE START -->` …
  `<!-- ENGINE:STATE END -->` hned pod H1. Píše ho **engine sám na terminálu `done`**
  (`run.py drive()` → `statewrite.py`), člověk ho NEEDITUJE. Mapa `closed_waves`
  (UPSERT + FIFO posledních 10): wave-id, `closed_at`, terminal `status`, `wave_base`,
  `class`, `touches_*`/`has_ui`, počet uzlů, `last_outcome`, `return_loops` a odkazy na
  `runs/<wave>/summary.md` + `ledger.yaml`. **Nezastarává** — je odvozeno deterministicky
  ze stavu běhu (axiom #7: stavová fakta = engine, ne ruční věta). Plná historie zůstává
  v `runs/` + gitu.
- **Lidský narativ** (pod markerem) — píše Watson/orchestrátor:
  - **Aktuální fokus** — co se zrovna dělá, **proč**, příběh wave
  - **Open Items** — co je rozpracované, deferred
  - **Cross-wave blockery** — co stojí v cestě
  - **Operační stav** — co provozovatel čeká

Engine **NIKDY nesáhne mimo svůj blok**; člověk nikdy needituje machine blok.
Lidská část se aktualizuje po každé wave nebo při významném STATE shiftu; machine
blok se plní automaticky. **Fakt „je hotovo" čti z machine bloku, ne z prózy.**

> **Fail-soft:** chybí-li STATE.md / marker / nastane I/O chyba, engine jen zaloguje
> WARN a terminál DOJEDE (vlna se nesmí shodit kvůli zápisu stavu). Marker když chybí,
> engine ho vloží pod H1.

---

## current-wave.md — aktivní vlna

Konkrétní task list aktuální wave. Orchestrátor zapisuje tasks při
dispatchu, agenti updatují status (in_progress, completed, blocked).

**Strojový stav (formalizace):** `templates/current-run.md` dává tomuto konceptu
strojově čitelný tvar — stav grafu `pipeline/delivery.yaml` (frontier/inflight,
completed, outcomes, skipped, counters, awaiting_human, halt_gate) v jednom `yaml` bloku. Čte ho
`scripts/pipeline/state.sh` (session-resume „hej Watsone") a `scripts/pipeline/next.sh`
(další uzel) — jednotně přes `scripts/pipeline/run.sh` (viz §Deterministický dispatch).
Próza zůstává lidská spec; runner je její deterministický executor nad tímto stavem.
