# Dream-team Framework — State

Živý stav frameworku. Edituje Watson (handoff mode) a orchestrátor.

## Aktuální fokus

**Wave:** `2026-06-13-watson-self-host` — **HOTOVÁ**. Uzavřena **mezera (A)** self-hostingu: Watson
neuměl onboardovat sám framework (self-reference). Fix dle scripts-not-LLM dělby: mechanická část =
skript `scripts/pipeline/core/self_host_init.py` (+ shim) — detekuje self-host, idempotentně seedne
PRODUCT vrstvu (`project-config` s `active_roles` odvozenými z grafu + `project_type: self-host`,
`PROJECT-CONSTITUTION`/`STATE`/`current-run` + `backlog/`/`handoffs/`), TODO značky (vize/targety)
nechá interview. Watson kontrakt rozšířen o detekci „Self-host" + recept. **Inverze structure-check**
(vytvoří ↔ ověří): round-trip seed→structure-check projde. Wired: selftest **60** (+round-trip), pytest
**101** (+6), mypy clean (18). `backlog/watson-self-host-mode.md` → FIXED. **Obě self-host mezery (A+B)
hotové.**

**Wave:** `2026-06-13-structure-validator` — **HOTOVÁ**. Dokončen resume bod z fold-conformance:
**structure-validator** — `scripts/pipeline/core/structure_check.py` (+ shim) ověřuje **PRODUCT-layer
tvar** projektu (S1 required sekce · S2 fyzické cesty existují · S3 project_type layout: self-host TOOL
na rootu vs normal `.agentic/` · S4 active_roles ∈ uzly grafu). Zavírá konvenční mezeru z otázky „má
projekt správný tvar" deterministickým skriptem (scripts-not-LLM). Sourozenec check.py. Wired: selftest
(+2 scénáře = **59**), pytest (+12 = **95**), CI krok, mypy clean (17). Distribuce automaticky (core/*.py
+ pipeline/*.sh globy). Design byl: `handoffs/2026-06-13-fold-conformance/HANDOFF.md §RESUME BOD`.

**Wave:** `2026-06-13-fold-conformance` — **HOTOVÁ.** Uzavřela
jediný explicitně odložený bod: **VISION fold** (`290019c`) — `VISION.md` sloučen do
`PROJECT-CONSTITUTION` (10/10 coverage; dvě vize-docs = drift anti-pattern), salvage „most engine→app"
tabulky do `backlog/app-platform.md`, 4 odkazy přesměrovány, README PRODUCT-tabulka narovnána.
**`.claude/` rozhodnutí** (`c6e6905`) — `settings.json` (gate allowlist) verzován, `settings.local.json`
ukotven do repo `.gitignore` (dřív jen globální = nepřenosné). **Self-host konformita ověřena naživo**:
brána zelená (check C1–C15 · selftest 57/57 · pytest 83 · mypy clean 16 *jen s `--config-file
scripts/pipeline/mypy.ini`*). Závěr: framework JE projekt-tvar (P5 dokázal), ale layout vědomě NENÍ
identický s generovaným projektem (TOOL na rootu vs `.agentic/`; `project_type: self-host`).
structure-validator → **DOKONČEN v navazující vlně** (viz výše).

**Wave:** `2026-06-13-p5-human-interaction` — **HOTOVÁ**. **První reálný self-hosted flow běh** —
„flow pracuje samo na sobě". P5 (human-interaction registry) protažen celým flow přes `run.sh drive`:
intake→product(Vision spec)→feasibility(Tony)→architecture(Ted kontrakt)→backend(Bob: `interactions.yaml`
v2 typovaný registr + `check.py` C10 produces-validace + 8 testů)→qa(Joey)→audit(Sheldon/Vitek PASS,
Heimdall advisory)→l2-review(ACK)→**done**. Produkt: `interactions.yaml` rozšířen na typovaný registr
(6 kindů vč. `delegate-or-provide` = upload XOR delegate, typové I/O `produces`). Gate: selftest 57/57,
check C1–C15, pytest **83**, mypy clean. **5 dogfood nálezů** (`backlog/flow-self-host-gaps.md`): project
flagy chyběly (has_server/db/deploy), klient fan-out není has_ui-gated, graf modeluje app-delivery ne
meta-práci, `skip` nevyřadí inflight, feature-vs-projekt flag tension. Archiv:
`handoffs/2026-06-13-p5-human-interaction/PROGRESS.md`. **#1/#2/#4 OPRAVENO** (frontier odvozuje
project flagy z targetů; web/mobile/desktop gated `&& spec.has_ui`; `skip` vyřadí z frontier) —
validováno, P5-like běh teď čistý bez workaroundů. **#5** flag scope formalizován (`vocabulary.yaml`:
project vs feature; routing = project && feature). **#3** vyjasněn jako **správná hranice, ne gap**:
delivery graf dodává PRODUKT (engine fit ověřen P5), agent-meta = Eywa off-graph, governance deliberate.
**Všech 5 dogfood nálezů vyřešeno.**

**Wave:** `2026-06-13-self-host-framework` — **HOTOVÁ**. Framework převeden na **standardní
projekt** (self-hosting): přidána PRODUCT vrstva (`PROJECT-CONSTITUTION.md`, `project-config.md`,
`current-run.md`, `backlog/`) ve frameworkových konvencích (ne Trabajario). Stack platformy = **Python
(FastAPI) + SolidJS**, web target. Vize z `VISION.md` přenesena do `PROJECT-CONSTITUTION` (§Vize a mise +
§Hard rules = I1–I8), roadmap → `backlog/` (app-platform, watson-self-host-mode, human-interaction-registry).
**VISION.md SLOUČEN** (fold, git drží historii): kanonický north-star = `PROJECT-CONSTITUTION §Vize a mise`;
unikátní „most engine→app" tabulka přesunuta do `backlog/app-platform.md`; 4 odkazy přesměrovány
(README/ARCHITECTURE/core-README/PROJECT-CONSTITUTION). Detail: `handoffs/2026-06-13-self-host-framework/HANDOFF.md`. Předchozí: docs konsolidace
(README front door + mapa, WORKFLOW/REVIEW smazány) + code-quality vlna (typy/dekompozice, mypy clean).

**Wave:** `2026-06-12-incremental-reflow` — **HOTOVÁ**. Řeší **E1-depth** (blocking re-flow byl depth-unscoped:
doc-only nález re-floutl 24 uzlů). Engine přepsán na **incremental rebuild (Make/Bazel model)**: uzel se
přepočítá, **jen když se mu reálně změnil vstup**. Mechanika: každé `done` orazítkuje verzí (`epoch`)
změněné output-typy (`type_versions`) + vlastní uzel (`node_versions`); uzel deklaruje `changed:[typy]`
(default = všechny jeho outputy → plný re-flow, ale lazily). Uzel M **stale** ⟺ ∃ jeho vstupní typ má
novější verzi než `node_versions[M]` (abstraktní `code` se rozbalí na subtypes). **5 fází, test-driven:**
(1) stav+stamping (`result.sh`, additivní); (2) FAIL+return un-completne **jen cíl** (`forward_closure`
zrušen → downstream lazily); (3) `next.sh` **version-staleness** nahradila E2 downward-closure (graceful
fallback na „producent valid" pro staré seedy bez verzí); (4) testy; (5) docs. **Order-independence drží**
přes monotonní `epoch` (resurrected completion neresurektne — vstupní verze přebije node-verzi). selftest
**45/45** — Fáze 4 naostro verzovou cestou: scoped (`changed:[spec]` → ted/chandler stale, **bob/joey
zůstávají**), default-all (bez `changed` → bumpne acceptance → joey stale taky = plný re-flow lazily),
version order-indep (contract v8 → chandler+bob stale tranzitivně, joey lazy zůstává). Determinismus
ověřen (PYTHONHASHSEED stress). Doc: `flow.md §FAIL+return`, `frontier-scheduler.md §FAIL/return`.
**✓ ACCEPTANCE NAOSTRO HOTOVÁ** — E2E `createdat` (backend-only) protažen **reálným grafem** přes
`run.sh drive`/`result.sh` (ne syntetický seed): happy intake→vision→ted→chandler→bob→joey→fan-out;
audit-vrstva = vitek advisory (bez re-flow) + sheldon **blocking** (spec open-question vs contract
CLOSED) → return vision. Vision opraví doc (`changed:[spec]`), ted re-runne ale `changed:none`
(contract beze změny). **Re-flow zasáhl PŘESNĚ spec-spine {vision, tony, ted, chandler, sheldon} (5),
kód (bob/joey) + code-auditoři (optimus/heimdall/vitek) zůstali completed** — `sheldon→vision=1`
(žádný BLOCKER), `status done`. Dřív (forward-closure) totéž re-floutlo 24 uzlů. Reproducer:
`handoffs/2026-06-12-incremental-reflow/accept-createdat.py`. **Vedlejší poznatek** (orchestrace, ne
blocker): non-blocking `l2-review` je nabízen souběžně se stale spec-spine; předčasný lidský ACK by
dojel do `done` s ted/chandler stále stale — neškodné (contract beze změny = identický produkt) a
self-correcting (kdyby ted změnil contract → bob/joey/auditoři stale → l2-review nedosažitelný dřív).
Disciplína: human-gate odbav až po vyprázdnění worker-frontieru.

**Wave:** `2026-06-11-agent-contracts` — **HOTOVÁ**. Agenti přepsáni na **slepé I/O kontrakty**: agent zná
jen identitu + typované vstupy/výstupy + jak soudí; **neví, že je ve flow** (nezmiňuje graf, endpoint, souseda).
Routing žije **jen v grafu** (`delivery.yaml`) + `/done` (result/next.sh). 17 delivery agentů přepsáno (plný
doménový detail zachován, ven jen „Handoff target"/„Gates" + jména kolegů), eywa = továrna na nový tvar,
`agents/ARCHITECTURE.md` = princip. **Joey (zkoušeč naslepo) FAIL → Ted (diagnostik)**, ne hádání vlastníka;
Ted jmenuje **doménu** vady (`fault: db-schema|contract|server-logic|spec`), graf přeloží na uzel (flow-blind).
Pojistka **C13** v check.sh (shodí build, když agent jmenuje kolegu / má routing sekci). Verdikt = kompetence
(Joey „rozbité" → Ted „rozbité kvůli DB"). selftest **39**, check **C1–C13** OK. Vzor: `agents/joey-qa.md`.
**Validováno NAOSTRO** (dogfood, smyčka joey→ted): reálný Joey vrátil jen příznak (nula hádání vlastníka);
engine auto-routoval joey→ted (single-return, slepý agent nejmenuje souseda); E1 payload donesl signature;
reálný **Ted prošel celý řetěz a správně diagnostikoval `fault: contract`** (ne pattern-match „created_at→DB" —
ověřil, že DB sloupec existuje), jmenoval doménu, ne kolegu. Nález: `fault: contract` (vlastní doména) = Ted
opraví+PASS, ne routovací fault (vyjasněno v `ted-architect.md`). Engine fix: `result.sh` **single-return
auto-resolve** (FAIL bez returns_to + 1 return cíl → engine routuje sám).
**PLNÝ END-TO-END NAOSTRO ✓** (`2026-06-12-createdat`, feature „get-user vrací created_at", intake→audit):
reální agenti na každém uzlu z nových slepých kontraktů — vision→tony→ted→chandler(no-op)→bob→joey→4 auditoři.
Prošlo: B3 model-routing (bob dispatchnut `haiku*` z Tonyho triage), B1 path-check, chandler B2 no-op, joey 25/25.
Audit-vrstva našla **2 reálné nálezy** (vitek advisory: UserView konstruktor 4× duplikát; sheldon blocking:
spec open-question vs kontrakt CLOSED) — **E1 severity naostro**: advisory zaznamenán bez re-flow, blocking
re-floutl + nesl signature k cíli (drive vytiskl `↻ re-flow finding`). **2 ENGINE nálezy:**
**(T1) target-gating** — nedeklarované `active_targets` → klient „unknown"→aktivní (spurious dispatch
peter/mob/winny na backend-only feature); **FIXNUTO** (`next.sh`: deklarované-prázdné = autoritativní, klienti
off; selftest guard). **(T2) E1-depth** — sheldonův *dokumentační* blocking nález (chování OK, 25/25) re-floutl
**24 uzlů** (celou pipeline od visionu); blocking re-flow je depth-unscoped (doc-fix nemá re-runnout kód/testy).
→ **VYŘEŠENO** vlnou `2026-06-12-incremental-reflow` (version-staleness, viz nahoře).

**Wave:** `2026-06-11-flow-finish-4` — **HOTOVÁ/UZAVŘENA**. Re-run profilu B (`dogfood/userflow/`) **reálnými
agenty** přes celý drive — feature `GET /users/{id}`. Protaženo vision→bob→joey→**paralelní audit-frontier**
(optimus∥sheldon∥heimdall∥vitek). **Engine (a-drift) happy-path = NULA**; B1 phantom PASS **FIXNUTO**
(result.sh path-existence, selftest 28/28). Audit-vrstva naostro našla 3 reálné obsahové nálezy (D1 heimdall
HIGH auth-gap, D2 spec-čistota, D3 typ) + **1 ENGINE nález E1** (frontier re-flow severity-blind + ztráta
finding-payloadu, empiricky ověřen). Live běh pauznutý na audit-vrstvě (nekrmen do re-flow). Sklizeň:
`handoffs/2026-06-11-flowfinish-4-realrun/CLOSE.md`.

**Engine wave:** `2026-06-11-flow-determinism` — **HOTOVÁ** (E1+E2). Návratová strana frontieru zdeterminizována:
severity gating (advisory bez re-flow) + payload-carry (signature ze stavu, ne z paměti) + order-independence
(downward-closed valid-cache, empiricky ověřeno). selftest **34**. Detail v Open Items.

**→ Engine-osa determinismu KOMPLETNÍ:** **B3 HOTOVO** (Tony triage → per-node model), **B2 HOTOVO**
(Ted `touches_db` → prořízne chandlera u read-only feature; default = `has_db`, fail-safe), **F3 HOTOVO**
(deterministický most handoff→envelope: `result.sh` auto-derivuje output typy/agent/phase z grafu, time
volitelné → minimal envelope `{run,node,outcome}`, konec ručního mapování = divergence-zdroj). selftest
**50/50**. Otevřené už jen **produktové** rozhodnutí **auth na get-user** (D1; člověk při návratu k feature).

---

**Engine wave:** `2026-06-11-frontier-scheduler` — **HOTOVÁ** (F1–F6 + REJECTED halt). Single `active_node` +
`pending` barrier → **frontier dataflow model** (blueprint: `frontier-scheduler.md`). selftest **26/26**,
check graf **C1–C12**. Vyrostlo z `flow-finish #3` (fork).

**Proč:** `drive` držel jeden `active_node` + jeden fan-out barrier → neuměl (a) skutečně paralelní
nezávislé tracky (UI ∥ backend, security ∥ review) ani (b) confluence (peter potřebuje `contract` z ted
**i** `ui-components` z leonard). Nález **F5** z wave-pipeline.

**Dvě uživatelská rozhodnutí (immutable):**
- **Více uzlů paralelně = ano** → frontier-set model (ne single active_node, ne fork-stack berlička).
- **Flow se NEvolí per stack** → je to **jeden graf, target/flag-gated** (`peter when: targets.web`,
  `winny when: targets.desktop`, `bob when: has_server`, …). Watson zadrátuje `active_targets` při
  foundingu; drive prořezává sám. Per-stack grafy = O(stacků) + porušení axiomu „žádní tech-specific".

**Co wave zavezla (4 commity, `457576d`→`4f6d4df`):**
- **F2 drive** = frontier executor: vydá **celou ready množinu** jako akce (paralelní `DISPATCH` +
  non-blocking `HUMAN-GATE` souběžně, `HALT` na blocking L3, `DECIDE`/`skip`, `DONE`, `BLOCKED`).
  join/router auto-advance. Nový `run.sh skip <node>` (judged-skip).
- **F3 result.sh** = `outcomes` map, inflight (`frontier`) maintenance, `class` z intake. FAIL+return =
  **re-flow** (un-complete cíl + forward-downstream → re-audit, counter++, 3× = BLOCKER). `pending` pryč.
- **F5 check.sh** = C11 (dataflow-orphan: non-entry uzel musí mít forward producenta) + C12
  (`join.requires` odvoditelný z hran). **F6** = `flow.md §Deterministický dispatch` + architecture doc.
- **REJECTED halt** = `drive` na `status:blocked` (REJECTED / 3× counter / BLOCKER) čistě zastaví
  (BLOCKED + důvod v `note`), ne re-nabídka gate. deploy-approve `REJECTED` → žádný production.
- Stav model: `current-run.md` = `frontier`/`completed`/`outcomes`/`skipped`/`awaiting_human`(list)/
  `halt_gate`/`class`. `templates/current-run.md` + `state.sh` srovnané.

**→ flow-finish #4 ROZBĚHNUTO** (viz §Aktuální fokus nahoře + handoff) — feature `GET /users/{id}`
zvolena, vision→bob hotovo (6 uzlů, reální subagenti, pytest 13/13 ověřeno), čeká joey. Engine
validován reálnými agenty (a-drift NULA); 4 b-drift nálezy B1–B4 zmapovány v handoffu.

---

**Předchozí wave:** `2026-06-11-flow-finish` — #1 human-gate continuation + #2 T3-post + #3a flag fix
HOTOVO; #3 fork → přešel do `frontier-scheduler`, #4 re-run profil B zbývá.

**Co flow-finish udělala (engine, ne agent):** `drive` se u human-gate **už nezasekne**. Root cause =
`result.sh` nevynuloval `awaiting_human` po `done` gate uzlu (F4-tvaru). Fixy:
- **result.sh** — `done` gate uzlu = lidský vstup → uvolní `awaiting_human` → `drive` routuje dál.
- **run.sh drive** — terminal pass-through (analog join): jediná eligible cesta do terminalu → `DONE`,
  nedispatchuj „práci" do `done`/`production`.
- **outcome vokabulář** sjednocen `result.sh`↔`next.sh` (+`ACK`/`REJECTED`/`PENDING`) — gate hlásí
  outcome z `interactions.yaml` věrně (ACK L2 / APPROVED|REJECTED L3), bez typovaného outputu.
- **selftest 14/14** — 2 nové scénáře: A) `has_deploy=false` continuation l2-review(ACK)→DONE;
  B) `has_deploy=true` **celá T3-post**: alfred→deploy-approve(APPROVED)→production→monitor→done.
- **flow.md** — HUMAN-GATE bullet má explicitní continuation mechanismus.

**Stav: per-issue flow JEDE deterministicky end-to-end VČETNĚ release** (`run.sh drive`). Jediný DECIDE =
intake (legitimní úsudek), zbytek deterministický DISPATCH/HUMAN-GATE.

_Níže původní diagnóza wave-pipeline (proč) — pro kontext:_

Dogfood `POST /users` nad čerstvě foundnutým `dogfood/userflow/` (python-fastapi+auth/jwt), profil B
(orchestrátor řídí `run.sh drive`). Cíl: otestovat per-issue flow (`drive` → T1→T2→T3) naostro.
Výsledek: **flow reálně NEBĚŽÍ end-to-end** — root cause = (a) chybějící/neintegrovaná engine vrstva
(ne (b) agent; Vision odvedl práci čistě).

**5 nálezů:**
- **F4 (BLOCKER)** — `result.sh:132` nuluje `active_node`, který `drive` potřebuje jako `--from` → smyčka `done→drive` nezavírá. `selftest.sh` to nikdy nechytil.
- **F2 (major)** — runner nemá zdroj project/spec flagů (`drive` nepředává `--flag`; `has_ui` z Vision nikdy nezapíše do strojového stavu) → každá strukturální větev = vynucený DECIDE.
- **F5 (major)** — `drive` neimplementuje `kind: fork`; paralelní odbočka míchána do DECIDE kandidátů.
- **F3 (major)** — žádný deterministický most handoff→envelope; ruční překlad orchestrátorem = divergence-prone.
- **F1 (minor)** — `pipeline/delivery.yaml` hlavička lže o stavu (říká „ZATÍM HO NEČTE žádný runner", runner existuje).

**Fixy (tatáž session):** F4 (`done` drží active_node = frontier, ne null), F2 (flag APPLY vrstva:
project-config `flags:` → next.sh, envelope `flags:` → current-run, drive je předá), F6 (ted→bob jen
`!has_db`), F7 (dev→joey `when: PASS`), F8 (auditor return `when: FAIL`), F9 (drive fan-out barrier +
join pass-through), F1 (doc). Detaily: FINDINGS.md §Fixes. F5 (kind:fork) pro backend vyřešen F2 (skip);
pravá paralelní fork-spawn pro UI featury = follow-up.

**→ NEXT (příští session):** **flow-finish (T3-post + human-gate)** — (1) human-gate **continuation**
(po L2/L3 vstupu pokračovat; dnes drive u human-gate zastaví, chybí „člověk OK → advance"); (2) T3-post
release path (alfred/deploy/monitor) protáhnout dogfoodem; (3) UI-feature dogfood (has_ui=true → fork
denisa, edna v T3) — ověří F5/F9 na paralelní větvi; (4) re-run profil B s reálnými agenty na (b) drift.

---

**Předchozí wave:** `2026-06-11-init-determinism` — HOTOVO; wave uzavřena
(handoff: `handoffs/2026-06-11-init-determinism/HANDOFF.md`; blueprint: `init-determinism.md`)

2-agent dogfood (java-quarkus, auth, jedna lidská věta) odhalil: scaffold.sh/feature.sh jen RESOLVNOU,
neAPLIKUJÍ → ze stejného vstupu `ja` auth nasadil, `jb` minul. Root cause = (a) chybějící APPLY
vrstva, ne (b) agent. Postaven **APPLY engine**: `compose.sh` + `apply-feature.sh` + zadrátováno do
`watson-interviewer.md` v1.9. Capstone re-run: byte-identický server/+contracts/, selftest 9/9, check OK.

---

**Starší wave:** `2026-06-10-scaffolds+engine-loop` — HOTOVO; wave uzavřena

Cíl: dokončit scaffoldy (všechny osy ready), uzavřít execution loop, adoptovat UnagyDev patterny.

Hotovo:
- **Scaffoldy ready (všechny osy):** `flutter` (Riverpod+go_router+dio+gen-l10n, plain modely),
  `electron` (electron-vite+builder, SolidJS renderer, security baseline); **docker-dev reálně**
  (python+solidjs `Dockerfile.dev`+`docker-compose.dev.yml`, java = DB-in-container model);
  manifest flutter/electron → `ready`; recommended-libs flutter+electron sekce.
- **Execution loop uzavřen:** `run.sh drive` = řidič — ze stavu vydá JEDNU direktivu
  (DISPATCH / DISPATCH-ALL / DECIDE / HUMAN-GATE / DONE), deterministicky posune `active_node`,
  free-text podmínku → explicitní DECIDE (ne tiché LLM rozhodnutí). `next.sh --emit json`.
  Zadrátováno do `flow.md §Deterministický dispatch` (drive = primární krok smyčky).
- **UnagyDev = pattern-donor** (nejpromyšlenější projekt): promotnuto do `rules/` — API model
  role `*View/*Data/*ExtData`, write-flow validate-only+commit, kolekce List/Page/Slice, typy
  operací, one-table=one-repo (backend); form-model, write-flow klient, domain-konstanty
  fail-closed (frontend). Scaffold bindingy: solidjs `createFormStore`+`TextField`, flutter
  `form_model.dart`; **python-fastapi dorovnán na java-quarkus** (validate-flow + model role +
  `ApiListOf/PageOf/SliceOf` + `ValidationResult`, **pytest 4/4**); electron renderer reuse note.
- **Reuse governance (anti-entropy):** `constitution §Reuse §Operační mechanismus`
  (Extraction Candidates registr, 2.výskyt = povinná akce, explicitní **back-fill**,
  katalog = autorita) + `templates/extraction-candidates.md`. Mechanický back-align:
  `scripts/catalog-conformance.sh` (deterministický scan) + per-stack `catalog-conformance.yaml`
  napříč **všemi 5 stacky** (solidjs/flutter/python/electron/java) + `catalog.md`; wired do
  Vitek gate vedle `drift-scan`. Ověřeno: clean na všech scaffoldech + detekce nasazených violací.
  Advisory candidate auto-detekce (C): `scripts/extraction-scan.sh` (najde opakované bloky ≥3×
  → návrh do registru; deterministické, neblokuje).
- **Formatter/style enforcement (scripty, ne LLM):** per-stack formatter + style-lint —
  python `ruff`, TS `prettier`(semi:false)+`eslint`(curly), flutter `dart format`+curly lint,
  java `spotless`(googleJavaFormat); `scripts/format-check.sh` (unified) → **Vitek gate**.
  Pravidla zpřesněna (`constitution §Standardy`): if vždy `{ }`+prefer-if, emoji+UI-ikona výjimka,
  **kód anglicky / specs česky**; ID=UUID default (`rules/backend §Identifikátory`). Komentáře ve
  scaffoldech přeloženy CZ→EN (60 souborů). Z dogfoodu: 2 nezávislé buildy stejného zadání =
  byte-identické modely, jediná divergence UUID/str (→ ID pravidlo) + formátování (→ formatter).
- **P7 — Feature library (pilot auth):** `feature` osa scaffoldu — `templates/features/<f>/` s
  `feature.yaml` (varianty + options + Watson otázka), stack-agnostic `spec.md` (vždy), per-stack
  `impl/` (jen security-critical → **audit-once** Heimdall, regenerate-never). Resolver
  `scripts/pipeline/feature.sh`; Watson init nabízí features (5. věc). **Auth pilot (python-fastapi):
  credentials + volba `token_strategy: jwt | session` — obě ověřené pytestem 8/8.** Java-quarkus impl
  (jwt+session) je **strukturálně kompletní, ale BUILD-VERIFICATION PENDING** (no gradle/jOOQ/Docker
  env) — security-critical, nenasazovat bez `./gradlew build` + QuarkusTest + Heimdall audit (task #12).
  Base conftest zlepšen na glob `V*.sql` (z dogfoodu — feature s migrací funguje bez úprav). VISION §5 P7.
- **Drift fix:** verzní patičky STATE/VISION → 0.35.0.

**Wave:** `2026-06-10-deploy-platform` — HOTOVO; wave uzavřena

Cíl: deploy platforma jako první třída stacku (Watson fáze 2, nové `_target/` fragmenty,
xyflow jako vetted DnD default pro SolidJS).

Hotovo:
- `_target/docker-compose.md` + `_target/wordpress-hosting.md` — nové fragmenty
- `stacks/README.md` — composition table s deploy fragmentem per projekt
- `watson-interviewer.md` v1.7 — deploy platform v Fáze 2, composition table, output format
- `_base/solidjs.md` v2.1 — xyflow jako podmíněný vetted default pro DnD/node-graph
- `Machina/stack/server.md` + `Machina/stack/web.md` — vytvořeny (chyběly)

**Wave:** `2026-05-30-model-routing` — HOTOVO (v0.14.0 + v0.15.0); wave uzavřena

Cíl: right-sized modely dle složitosti úkolu (jak Cursor auto mód).

Hotovo:
- **Per-agent model tiery** (v0.14.0): `model:` ve frontmatteru všech 19 agentů
  (opus = tony/ted/heimdall/eywa; sonnet = zbytek); propagace do `.claude/agents/`
  wrapperů přes `setup-claude-code.sh`.
- **Rubrika XS/S/M/L + override** (v0.15.0): `flow.md §Model routing`; Claude Code
  Task tool `model` parametr ověřen (přebíjí frontmatter); per-úkol dynamická
  routace funkční.
- **Bezpečná eskalace**: fail na levném modelu → tier +1 před BLOCKER
  (`constitution §Kritická pravidla #2`).
- **Měření**: `scripts/model-usage.sh` (derivuje routing z `runs/<run>/ledger.yaml`, ne
  z ručního logu — N5); prior `scripts/complexity-estimate.sh`; dekompozice L `templates/work-breakdown.md`.
- **Rollout**: sync + setup + CLAUDE.md sekce ve všech 6 dogfood projektech.
- **Bug (Open Item)**: `agentic-sync.sh --yes` self-replacement crash.

**Wave:** `2026-05-30-session-hygiene` — HOTOVO (v0.13.0); wave uzavřena

Cíl: opravit tři session hygiene problémy (PROJECT.md přežívalo, handoff nevolal
Watsona, framework sync bez zpětné vazby).

Hotovo:
- **PROJECT.md → STATE.md**: setup-claude-code.sh automaticky přejmenuje při
  setupu; concept vymazán z flow.md a watson-interviewer.md
- **Watson auto-invoke při startu session**: CLAUDE.md šablona má "SESSION START —
  VŽDY" sekci + keyword trigger tabulku; Cursor cursorrules mají Watson ritual;
  Aider má manuální pokyn; flow.md má Keyword triggery sekci (tool-agnostic)
- **framework-sync-log.md**: agentic-sync.sh po každém syncu (CHANGED>0 nebo NEW>0)
  zapíše záznam do root `framework-sync-log.md`; Watson session-resume čte a
  prezentuje PENDING_REVIEW záznamy uživateli

**Wave:** `2026-05-30-audit-coherence` — HOTOVO (v0.12.0); wave uzavřena

Cíl: kompletní audit koherence (agenti, scaffoldy, dispatch dokumentace) + oprava
nalezených nesouladů. Všechny změny jsou v jednom commitu (v0.12.0).

Hotovo:
- **F1–F8 security checklist** — přidán jako explicitní normativní sekce do
  `constitution.md` (v1.3); agenti teď mají resolovatelné reference
- **G1–G10 cross-reference** — přidán ke §Standardy kódu v constitution
- **Souřadnicový systém** — odstraněny old-style §A4/§B2/§G2/§H3 atp. ve všech
  19 agent souborech; nahrazeno aktuálními názvy sekcí
- **Deploy scaffold wiring** — `alfred-devops.md` má vstupy `templates/scaffolds/deploy/`
  + pokyn pro platform scaffold při zavádění deploye; (Parker) odstraněno z write-scope
- **Počty agentů** — narovnáno 15/16 → 19 v README, USAGE, Watson
- **§Stop body #4** — upřesněn gate seznam (Joey + Optimus + Sheldon + Heimdall +
  Vitek + Edna-pokud-UI); `flow.md` nyní konzistentní s INDEX/README/Alfred
- **Leonard↔Peter CSS hranice** — upřesněna v INDEX.md write-scope tabulce
- **agent-graph-check.sh header** — opravena hlavička (neslibuje kontroly #4/#5)
- **`spec-structure-check.sh`** — odstraněn z Sheldonových Tools (script neexistuje)
- **`ParkerError`** — odstraněn z Bob agent (nahrazen generickým `ApiError`)

**Wave:** `2026-05-30-scaffold-uniformita` — Fáze 0–4 HOTOVO (v0.10.0); wave uzavřena

Cíl: **stejný stack → stejný kód všude** přes kanonický stack reference +
reálnou kostru kódu (scaffold), ne přes stack-specialisty (ti plodí variabilitu
a vyžadují O(role×stacků) agentů).

Hotovo (3 stacky, všechny scaffoldy reálně ověřené build/test):
- **Fáze 0** — SSR→SSG (runtime SSR zakázán, SEO=SSG/CMS-native); constitution
  §Standardy kódu +primitives/inference/type-refs; §Kritická pravidla #8 +ochrana
  dev-dat; nový `templates/rules/defaults.md`.
- **Fáze 1** — `java-quarkus`: kanonický `_base` (z UnagyDev) + kostra (jOOQ,
  shared infra, vertical slice). Ověřeno: gradle codegen+compile+test 2/2.
- **Fáze 2** — `python-fastapi`: kanonický `_base` (z murio) + kostra (SQLAlchemy
  Core async, `{code,details}`). Ověřeno pytest 2/2. `solidjs`: kanonický `_base`
  + kostra (**Kobalte headless + design tokeny + CSS Modules**, openapi-fetch).
  Ověřeno vitest 2/2 + typecheck + build. Watson scaffold krok pro všechny.

## Open Items

- [x] **Review `PROJECT-CONSTITUTION §Vize a mise` + osud `VISION.md` — HOTOVO (FOLD).** Coverage
  VISION→PROJECT-CONSTITUTION 10/10; zbytek VISION historický (roadmap P1–P7 hotová, status-table
  zastaralá). Rozhodnuto **sloučit** (dvě vize-docs s 10/10 překryvem = drift anti-pattern, který
  engine potírá; ústava se deklaruje jako kanonický kondenzát). Unikátní „most engine→app" tabulka
  zachráněna do `backlog/app-platform.md`; 4 navigační odkazy přesměrovány; `git rm VISION.md`
  (historie v gitu). README PRODUCT-tabulka narovnána (přidán PROJECT-CONSTITUTION + backlog/).
- [ ] **Structure-validator (ROZBĚHNUTO, nula kódu)** — brána ověřuje graf+engine, ne „má projekt
  správný PRODUCT-layer tvar" (konformita = dnes konvence, ne kontrola). Návrh: `scripts/pipeline/
  structure-check.py` (+ shim) — required sekce v `project-config.md`, existence required cest z
  `## Fyzické cesty` (lazy specs/stack allowed-absent), `project_type` dispatch (self-host→TOOL na
  rootu / normal→`.agentic/`), `active_roles` ∈ node-id grafu. Test-driven do selftest + CI + sync.
  Kompletní design + konvence: `handoffs/2026-06-13-fold-conformance/HANDOFF.md §RESUME BOD`.
- [ ] **App-platforma (node editor)** — north-star, samostatný budoucí projekt konzumující engine.
  `backlog/app-platform.md`. Předpoklad P5 (human-interaction registry) HOTOVO.
- [x] **Code-quality pass nad enginem — HOTOVO (constitution §Standardy kódu).** Po OO refactoru
  dotažen i Python na tvoje pravidla (feedback „není to kód který bych chtěl číst, ne vibe coding").
  **Type anotace napříč `core/`** (16 souborů mypy-clean, `mypy.ini` non-strict, CI krok) + duck-type
  kontrakty jako **Protocol** (`EvalContext`/`ActivationContext`/`Expr`); **dlouhé `main()` rozloženy**
  na pojmenované kroky (result/check/run); vnořené ternáry/lambdy pryč; dead code (`passthru`) odstraněn;
  DRY (result.py inline zápis → `common.write_state`). **Rozhodnutí** (delegoval jsi): bash shimy ZŮSTÁVAJÍ
  (agent-facing kontrakt, ne problém); komentáře ČESKY (vědomá výjimka, interní nástroj). Čistý refactor,
  nula změny chování — výstup check.py byte-identický, brána 57/57 + pytest 75 + mypy + parity zelená po
  každém z 11 commitů. Detail: `handoffs/2026-06-13-code-quality/CLOSE.md`. Commity `0549113`→`532eecf`.
- [x] **OO refactor enginu (doménový model) — HOTOVO (všechny 4 fáze).** Procedurální if/regex/
  `eval()` slepenec nahrazen doménovým modelem; engine iteruje nad objekty, ne nad dicty.
  **Fáze 1** (`611b0a5`) Predicate AST (`eval()` pryč, parity 19208/0); **Fáze 2** (`c388605`)
  Node/Edge/Graph + RunState (Frontier třída, result.py na Graph/Vocabulary/RunState);
  **Fáze 3a** (`78591fc`) result.py outcome if/elif → polymorfní handlery (AdvisoryFail/ReturnFail/
  BareFail/Rejected/Completion); **Fáze 3b** (`960f012`) run.py drive string-žebřík → `node.drive_category`
  partition; **Fáze 4** check.py C1–C15 nad Graph/Vocabulary/`Predicate.problems` (poslední duplicitní
  when-parser pryč) + status.py přes Graph.load + docs. Čistý refactor, **nula změny chování** — výstup
  check.py byte-identický (real i broken graf), brána 57/57 + check C1–C15 + createdat + parity zelená
  po každé fázi. Plán: `~/.claude/plans/ancient-singing-pnueli.md`.
- [x] ~~**OO refactor enginu — NAPLÁNOVAT**~~ — engine byl procedurální if/regex/`eval()`
  slepenec (frontier.py: 91 if, 13 regex, 2 eval; jádro = `when` evaluace duplikovaná 3× v atom/
  classify/flag_live). Návrh: `core/model.py` s **Predicate AST** (keystone — `when` jako parsovaný
  strom typovaných atomů, ne string+eval; validace slovníku padne zadarmo) + `Node`/`Edge`/`Graph`/
  `RunState` třídy; engine moduly je konzumují. Čistý refactor, nula změny chování, **57 testů jako
  brána**. App-ready (node-editor konzumuje doménový model, ne YAML stringy). Plán + fázová cesta +
  rizika + otevřené design otázky: **`handoffs/2026-06-12-engine-oo-refactor/HANDOFF.md`**.
- [x] **vocabulary registr + fail-closed validace** — **HOTOVO**. Slovníky enginu byly volné stringy
  s tichým fallbackem (typo flagu → „FREE" → judgment prompt; neznámá severity → tiše blocking) =
  proti determinismu. Nově `pipeline/vocabulary.yaml` = jediný zdroj pravdy (flags bool|enum, classes,
  faults, targets, node_types, edge_kinds, severities, model_tiers, phases). **check.py C14** (každý
  `when` flag/hodnota ∈ registr; free-text judgment se skipuje) **+ C15** (node.type/edge.kind/phase ∈
  enum). **result.py fail-closed** (neznámá severity/fault/model → reject envelope, ne tichý default).
  Graceful: chybí-li registr → SKIP. selftest **57/57** (negativní: typo flagu/enum/type/kind/severity/
  fault odmítnuty). Auto-distribuováno (sync `pipeline/*` + create-project klon).
  **Follow-up navržený:** OO refactor enginu (Node/Edge/Graph třídy místo if-spaghetti) — viz níže.
- [x] **design_source jako projektová politika (ne per-feature gate)** — **HOTOVO**. `design-source`
  human-gate se ptal „kdo dodá mockup?" u KAŽDÉ UI featury a odpověď nic neroutovala (oba konce →
  denisa). Anti-pattern (engine má routovat, ne člověk volit „koho spustit"). Nově `design_source`
  = projektový value-flag (`author|intake|derive`, default author), Watson nastaví 1× při initu
  (solo→derive), **engine routuje deterministicky**: author→denisa, intake→gate(upload)→denisa,
  derive→leonard (UI ze specu, žádný mockup). Human-gate přežije JEN pro intake (reálný upload).
  Engine: frontier.py atom/flag_live umí `<flag> == <value>` (dřív FREE→judgment→prompt). Mockup =
  volitelný vstup (leonard/peter/mob/winny/edna — derive). selftest **52/52** (author/intake/derive).
  Dotčeno: `delivery.yaml`, `interactions.yaml`, `frontier.py`, `watson-interviewer.md`, 6 agentů.
  **Pozn.:** odhalilo hlubší cíl → role-typed uzly grafu (níže).
- [x] **role-typed uzly grafu (cast role→agent) — pro vizuální editor** — **MACHINE LAYER HOTOVÁ.**
  Uzly `delivery.yaml` přejmenovány z OSOB na ROLE; `agent:` = cast binding (kdo roli plní). Hrany
  drátují role → graf modifikovatelný vizuálním editorem, výměna agenta na roli = změna bindingu, ne
  grafu (agenti znají jen typy artefaktů → nedotkne se jich). Mapování: vision→**product**, ted→
  **architecture**, chandler→**db-schema** (= fault-doména i artefakt, koherentní), bob→**backend**,
  denisa→**ux-design**, leonard→**ui-system**, peter/mob/winny→**web/mobile/desktop**, joey→**qa**,
  optimus→**performance**, sheldon→**spec-audit**, heimdall→**security**, vitek→**code-quality**,
  edna→**design-audit**, alfred→**devops**, tony→**feasibility**, design-source→**design-intake**.
  Dotčeno: `delivery.yaml` (node-id + hrany + requires), `check.py` C7 (SPEC_AUTHORITY=product),
  `selftest.sh`, createdat reproducer, `pipeline/README.md`. selftest **52/52**, check C1–C13, reproducer.
  **Prose sladěna** (commit `5c701a8`): strategie = stroj/topologie role, lidské docs persony +
  orientační nota na role-mapping. INDEX.md cast tabulka má sloupec „Uzel grafu (role)" (most
  persona↔role) + dispatch matrix v rolích + design-source touchpoint opraven na design_source
  politiku. flow.md/OVERVIEW/ARCHITECTURE orientační noty. WORKFLOW.md ponechán persona (lidský
  explainer). Persona-readability je vědomá volba — persony zůstávají jako agenti na rolích.
- [x] **bash→python refactor (pipeline engine)** — **HOTOVO** (3 commity). Logika scriptů byla
  ~85 % Python uvězněný v bash-heredocích, s duplikací (coerce_flag/OUTCOMES/state-blok napříč
  soubory + „drž v sync" pozn.) a neimportovatelný (blokovalo app vrstvu z VISION §Most). Vytaženo
  do **`scripts/pipeline/core/*.py`** (12 modulů + `common.py` = sdílené jádro), `.sh` = 3-řádkové
  shimy (dokumentované rozhraní beze změny). `run.py drive` importuje `frontier` přímo (konec
  subprocess+JSON). Distribuce: `agentic-sync.sh` rozesílá `core/*.py` (jinak shimy nefungují);
  `create-project` klon je nese; CI běží přes shimy. Ověřeno: selftest **50/50**, check C1–C12,
  createdat reproducer, end-to-end projekt přes create-project (engine běží uvnitř `.agentic/`).
  Arch: `scripts/pipeline/core/README.md`. **Follow-up:** pytest unit-vrstva nad `core/`.
- [x] **E1-depth — scopovaný re-flow (incremental rebuild)** — **HOTOVO** (5 fází, viz §Aktuální
  fokus). Blocking re-flow byl depth-unscoped (E2E `createdat`: doc-only nález re-floutl 24 uzlů).
  Fix = Make/Bazel model: uzel deklaruje `changed:[typy]`, engine stampuje verze (`epoch`/
  `type_versions`/`node_versions`), downstream re-run jen když vstupní typ má novější verzi.
  Nahradilo `forward_closure` re-flow (→ un-complete jen cíl) + E2 downward-closure (→ version-
  staleness, order-independence drží přes monotonní epoch; graceful fallback pro staré seedy).
  selftest **45/45** (Fáze 4: scoped-reflow + default-all + version order-indep). **Acceptance naostro
  HOTOVÁ** (E2E `createdat` reálným grafem: re-flow = spec-spine {vision,tony,ted,chandler,sheldon},
  kód+auditoři zůstali; viz §Aktuální fokus). Plán+HOTOVO: `handoffs/2026-06-12-incremental-reflow/`.
- [x] **Fáze 2** — `python-fastapi` + `solidjs` kanonické `_base` + scaffoldy
  (ověřeno). Solidjs styling = Kobalte headless + tokeny (rozhodnuto, viz níže).
- [x] **Fáze 3** — activation profily `solo|standard|full` (`INDEX.md`
  §Activation profily); skeleton default `standard` (ne 19×active); Watson fáze 5
  doporučí profil dle složitosti + target-gating. Vypnutí ≠ smazání.
- [x] **Fáze 4** — value-stream struktura: `value-streams.md` (design only).
  Delivery = jediný aktivní proud; marketing = sketch (nestaví se). Odhalilo:
  `constitution.md` míchá universal + delivery-specific.
- [ ] **constitution split** (předpoklad 2. proudu, NE teď) — rozdělit
  `constitution.md` na universal axiomy vs delivery-stream pravidla (např.
  „spec=source of truth", „žádné emoji" jsou delivery, ne universal)
- [x] **pipeline-architecture F0–F4** (v0.19.0) — flow jako deklarativní stavový graf.
  - F0: `pipeline-architecture.md` (design, feasibility, fázová cesta; vize node-editor app).
  - F1: `pipeline/delivery.yaml` (25 uzlů, 44 hran, dnešní flow 1:1) + `pipeline/README.md`.
  - F2: `templates/current-run.md` (strojový stav běhu) + `scripts/pipeline/state.sh`.
  - F3: `scripts/pipeline/next.sh` (deterministický runner — routing dělá script, ne LLM).
  - F4: `CLAUDE.md` generovaný jako tenký adaptér z neutrálního kontraktu
    (`setup-claude-code.sh` zeštíhlen; orchestrační logika v `flow.md`/`constitution.md`).
  Additivní — live flow běží beze změny, runner zatím nevykonává. SCRUM odložen.
- [x] **pipeline guardrail + distribuce + strict-SDD** (v0.19.0) —
  `scripts/pipeline/check.sh` (C1–C7: parse, refy, join.requires, neznámý agent,
  dead-end, orphan, **spec-driven invariant**). Strict spec-driven vynuceno
  strukturálně: Vision dominuje všem produkujícím uzlům; `intake` routuje feature
  i improvement přes Vision (žádná zkratka do ted/tony). Distribuce: `pipeline/` +
  `scripts/pipeline/` přidány do `agentic-sync.sh` allowlistu + USAGE synced list.
  Eywa spouští check.sh při změně cast.
- [x] **VISION.md** (North-Star) — celá vize organizovaná: meta-cíl determinismu,
  invarianty I1–I8, subsystémy, most souborový engine→aplikace, roadmap P1–P6.
  Rozhodnutí: scripty Python+sh; SCRUM odložen; determinismus = akceptační kritérium;
  vtodo = vzor app vrstvy. Vstupní bod v README.
- [x] **P1 typované I/O** (v0.20.0) — `pipeline/artifacts.yaml` (24 typů; kind/desc/
  external/abstract+subtypes), `delivery.yaml` I/O normalizováno na typy, `check.sh`
  rozšířen o C8 (slovník) + C9 (existence producenta, vč. abstract `code`→subtypy).
  Ověřeno: čistý graf OK; typo v I/O zachycen C8+C9. Základ pro node-editor kompatibilitu
  a scaffold-passing.
- [x] **P2 node-result obálka („/done" v souboru)** (v0.21.0) — `templates/node-result.md`
  (schéma: outputs typované + outcome + gate + cost + čas) + `scripts/pipeline/result.sh`:
  ověří (uzel∈graf, outputs.type∈artifacts), připíše do `runs/<run>/ledger.yaml`
  (append-only multi-doc), posune `current-run.md` (completed/last_outcome/counters;
  FAIL+returns_to → bump). Loop: uzel hotov → result.sh (/done) → next.sh. `runs/` přidán
  do setup runtime dirs. Ověřeno: validní/nevalidní/FAIL+counter scénáře.
- [x] **P3 cost+čas ledger** (v0.22.0) — `scripts/pipeline/ledger.sh` agreguje
  `runs/<run>/ledger.yaml` → wall-clock + compute čas, kredity, tokeny, per model/uzel,
  return loops; zapíše `runs/<run>/summary.md`. Volitelný indikativní `pipeline/model-prices.yaml`
  dopočítá odhad kreditů z tokenů (chybí-li zaznamenané). Odpověď na „jak dlouho + kolik".
  Ověřeno: 3-uzlový run (wall vs compute), odhad opus 20k/8k tok = 0.90.
- [x] **P4 scaffold systém v2 — foundation** (v0.23.0) — `templates/scaffolds/manifest.yaml`
  (strojový index: axis platform/backend/frontend/deploy/agent · path · docker_dev ·
  newest · produces typed), `templates/scaffolds/README.md` (taxonomie + politiky Docker
  dev-run a newest-stack), `templates/agent-template.md` (kanonický agent scaffold — unblockl
  Eywa referenci), `scripts/pipeline/scaffold.sh` (deterministický resolver pro
  scaffold-passing), `scaffold` typ v artifacts.yaml, manifest přidán do sync. Ověřeno:
  resolver filtruje dle os, planned skryté bez --all.
  - [x] **P4 zbytek** (HOTOVO 2026-06-10) — flutter + electron scaffoldy postavené a
    `status: ready` v manifestu; docker dev-run reálně (python+solidjs `Dockerfile.dev`+compose,
    `docker compose config` OK); flutter dart-format clean, python pytest 4/4. Flutter/electron
    reálný build vyžaduje SDK/GUI toolchain (ověřeno strukturálně + syntakticky).
- [x] **P5 human-interaction registry** (v0.24.0) — `pipeline/interactions.yaml`
  (design-source/l2-review/deploy-approve: prompt · kind choice/approval/ack/upload/text ·
  options · produces · level · blocking), human-gate uzly v `delivery.yaml` mají
  `interaction:` ref, `check.sh §C10` ověří platnost + kind. App z toho deterministicky
  vyrenderuje ovládací prvek; odpověď přes result.sh. Ověřeno: graf OK, chybějící ref zachycen.
- [x] **P6 Watson init polish** (v0.25.0) — „Chci založit projekt" headline tok:
  4 věci (název/platformy/stack/popis) → deterministická kompozice (scaffoldy přes
  `scaffold.sh`/manifest, stack docs z fragmentů, seed idle `current-run.md`) → Vision →
  házení issues do grafu. `watson-interviewer.md` v1.8; `setup-claude-code.sh` seedne
  `current-run.md`. Ověřeno: setup vyseedoval idle stav, state.sh přečetl.
- **VISION roadmap P1–P6 KOMPLETNÍ.** Engine: deterministický, typovaný (I/O), spec-driven,
  scaffold-driven, účtovaný (cost+čas), human-interakce typované, init tok, vše v souborech,
  tool-agnostic, app-ready. Guardrail check.sh C1–C10.
- [x] **Runner executor + selftest** (v0.26.0) — `scripts/pipeline/run.sh` (jednotný vstup:
  start/active/status/next/done/summary/check/scaffold; „runner" executor z VISION, app
  volá tutéž logiku) + `scripts/pipeline/selftest.sh` (end-to-end smoke test smyčky, 9/9
  prošlo). Engine je teď ucelený a otestovaný jako celek, ne jen po kusech.
- [x] **CI guardrail** (v0.28.0) — `.github/workflows/pipeline-guardrails.yml` na push/PR
  spustí `check.sh` (C1–C10) + `selftest.sh`. Běží jen pro dream-team repo (root .github);
  po klonu jako `.agentic/` se nespouští → žádný leak do CI projektů.
- [x] **Standardizace knihoven** (v0.30.0) — z průzkumu 5 projektů (Parker2/UnagyDev/murio/
  Vdoklad/Trabajario): `templates/stacks/recommended-libs.yaml` (vetted libs per stack
  indexované SCHOPNOSTÍ; core/dev/capabilities + co je každá zač) + `scripts/pipeline/lib.sh`
  (resolver: „přidej drag-and-drop" → AI koukne sem). Scaffold core narovnán: solidjs
  +lucide-solid/i18next/solid-i18next/msw, python +python-multipart (DB libs zůstávají v
  `_db/` vrstvě). Styling = Kobalte + CSS/SASS Modules (Tailwind zakázán). SQL v jazyce
  (jOOQ/SQLAlchemy) už v rules/backend. Constitution: před volbou knihovny koukni do
  recommended-libs. Trabajario = vtodo (React+Tailwind — mimo standard, app vzor).
- [x] **pipeline — adopce (zadrátováno)** (v0.27.0) — `flow.md §Deterministický dispatch`
  dělá z runneru dokumentovaný mechanismus: orchestrátor počítá routing/stav přes
  `run.sh status/next/done/summary`, LLM dodává jen úsudek a obsah uzlů. Próza = lidská
  spec, runner = executor. Generovaný CLAUDE.md routing sekce na to odkazuje. Reálné
  habituální používání = přirozený důsledek (orchestrátor čte flow.md). Pozn.: dekompozice
  (issue→plán→todos→delegace) je normální výstup uzlu + dispatch, ne mutace grafu.
- [x] **Enforcement** (Vitek scaffold-conformance) — TRIGGER SPADL 2026-05-30,
  IMPLEMENTOVÁNO: `scripts/drift-scan.sh` (odvodí cizí otisky ze jmen
  sourozeneckých projektů + volitelně jejich `domain_keywords:`; grepne projektový
  obsah odděleně od .agentic/.claude framework snapshotu; detekuje tvary live
  secrets; exit 1 = nález). Wired do Vitek gate (`agents/vitek-quality.md` +
  gate-output). Skill = mechanismus, Vitek = judgment (kontaminace vs historie/
  persona/feature; secret → Heimdall). Ověřeno na murio (čistý až na historii).
  Budoucí: projekty můžou deklarovat `domain_keywords:` v project-config pro
  záchyt doménového slovníku (ne jen jmen).
- [ ] **Drift-align 5 projektů** (SEPARÁTNÍ follow-up, per-projekt schválení):
  - copy-paste bug: `error-responses.md`+`logging.md` táhnou Parker2 obsah
    (PARKER_*, „manuscript", OpenAI) do murio/Vdoklad/pneukarnik
  - `programming.md` 4× = kopie constitution → po syncu zrušit
  - Tailwind v murio/pneukarnik → migrace na tokeny+Kobalte (rozhodnuto: ne
    Tailwind kvůli čistotě zdrojáku); separátní follow-up
  - projekty přeaktivovávají agenty (16/19 i na pneuservisu) → profily (Fáze 3)
- [ ] **Backlog-item formát** — `templates/backlog-item.md` přidán (frontmatter
  id/type/priority/status/owner/source/created + sekce Problém/Rozsah/Akceptace).
  Napojeno v constitution §5. **Rollout do všech 6 projektů PENDING** (jako
  drift-align: per-projekt, scaffold-sync nebo ruční kopie do `templates/` repa).
  `/backlog` skill (dedup/auto-index/řazení) = až přibude procedura, ne teď.
- [ ] **murio drift-align zbývá** — `backend.md`+`frontend.md` pořád Parker copy-paste;
  flagnuté v murio `improvements/`. Postup: čistá session v `~/dev/AI/murio` →
  Ted opraví integrace (BankID/ISDS/payment/AI, pohřební doména) → Vitek/Heimdall/Sheldon
  gate → commit. Detaily viz `handoffs/2026-05-30-drift-align-rollout/HANDOFF.md §4`.
- [ ] **Watson → deploy scaffold copy** — Watson (v1.7) ví, který `_target` fragment použít,
  ale stále nekopíruje fyzické deploy soubory (Dockerfile, fly.toml, docker-compose.yml)
  při setupu. Doplnit krok do §Template library (po vzoru app scaffold copy). Alfred
  workaround přetrvává (v0.12.0).
- [ ] **Watson → ruční deploy setup step** — v USAGE.md chybí kapitola „Jak nastavit
  deploy u existujícího agentic projektu" (kde Alfred dostane pokyn použít scaffold).
  Přidat do USAGE §Daily operations nebo nová sekce §Deploy setup.
- [ ] **@xyflow v SolidJS** — `@xyflow/solid` neexistuje na npm (potvrzeno Machinou).
  Vetted default je `@xyflow/react`, ale cross-framework integrace nevyzkoušena.
  Ověřit až pipeline-editor feature přijde na řadu; případně najít alternativu.
- [x] **agentic-sync.sh --yes self-replacement crash** (v0.19.2) — OPRAVENO:
  atomický zápis `apply_file()` (temp + `mv`); rename nepřepisuje inode běžícího
  skriptu, takže sync doběhne i když přepíše sám sebe. Ověřeno izolovaným e2e
  testem (framework_version + sync-log se zapíšou, žádné `.synctmp` zbytky).
  Bonus: opraven greedy regex pro `LOCAL_VER` (sync-log ukazoval `0→` místo verze).
- [x] **model-routing-log.md** — VYŘEŠENO (N5, determinism-hardening fáze 3). Ruční log
  zrušen; `model-usage.sh` derivuje routing přímo z `runs/<run>/ledger.yaml` (jediný zdroj
  pravdy). Jediný úsudek `tier` nese envelope (`tier:`), zbytek (agent/model/cost) se odvodí.
- [x] **pipeline-loop-fix F4 (BLOCKER)** — HOTOVO (`wave-pipeline`). `result.sh`: `done` nechá
  `active_node` = dokončený uzel (frontier pro `drive`), ne `null`; `pending -= node`. Smyčka
  `done→drive` se zavírá. Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F2 (major)** — HOTOVO. Flag APPLY vrstva: `next.sh` čte `flags:` z
  `project-config.md`; `result.sh` ingestne `flags:` z envelope do `current-run.md`; `drive`
  předá flagy do `next.sh`. Strukturální větve deterministické. `current-run.md` má pole `flags`.
  Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F5 (major)** — ČÁSTEČNĚ. Backend cestu obchází F2 (skip); pravá
  paralelní fork-spawn pro UI featury (`has_ui=true → fork denisa/edna`) zatím chybí + `flow.md`
  pravidlo pro `kind: fork` chybí. Přesunuto do `flow-finish` níže.
- [x] **pipeline-loop-fix F6 (nový, z verifikace)** — HOTOVO. `ted→bob` osazeno
  `when: "has_server && !has_db"` → s DB jde bob přes chandlera. Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F7** — HOTOVO. `dev→joey` hrany: prózní podmínka → `when: PASS`
  (deterministický DISPATCH). Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F8** — HOTOVO. Auditorské return hrany osazeny `when: FAIL`
  (return jen na finding; na PASS → join). Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F9 (nový, z verifikace)** — HOTOVO. `run.sh drive`: fan-out barrier
  (neadvancuj k join, dokud `pending != []`) + join pass-through (join neprodukuje práci → auto-advance).
  Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix F3 (major)** — ZŮSTÁVÁ BUDOUCÍ (nezávislé). Deterministický most
  handoff(GATE OUTPUT)→envelope: F2 napojeno přes samostatné pole `flags:` (ne přes `outputs`), takže
  F3 (handoff→envelope extractor) zůstává nezávislý a neblokuje flow. Bez blocker dopadu.
- [x] **pipeline-loop-fix F1 (minor)** — HOTOVO. `delivery.yaml` hlavička opravena (runner graf
  vykonává). Viz `FINDINGS.md §Fixes applied`.
- [x] **pipeline-loop-fix regression guard** — HOTOVO. `selftest.sh` nově honí celou `drive`
  smyčku (fresh → human-gate l2-review). selftest **11/11**, check OK.
- [x] **dogfood/userflow/ substrát** — po fixech znovu projeto `drive` end-to-end (live důkaz
  v §Aktuální fokus); `drive` protáhl intake→…→human-gate deterministicky. Substrát zachován pro
  UI-feature dogfood (`has_ui=true`, fork denisa/edna → ověří F5/F9 na paralelní větvi) a re-run
  profil B s reálnými agenty na (b) drift.
- [x] **flow-finish #1 — human-gate continuation** — HOTOVO (`flow-finish`). `result.sh` po `done`
  gate uzlu vynuluje `awaiting_human` → `drive` routuje dál; `run.sh drive` terminal pass-through;
  outcome vokabulář sjednocen (`ACK`/`REJECTED`/`PENDING`). selftest scénář A (continuation→DONE).
- [x] **flow-finish #2 — T3-post release path** — engine/routing HOTOVO (`flow-finish`). selftest
  scénář B protáhne `has_deploy=true` celou release: alfred→deploy-approve(APPROVED)→production→
  monitor→done. Reálný-agent dogfood pass se skládá do #4 (re-run profil B).
- [x] **flow-finish #3a — design_source non-bool flag** — HOTOVO. `result.sh`+`next.sh` sdílený
  `coerce_flag()` (bool-ish→bool, jinak verbatim); `run.sh drive` serializuje non-bool verbatim.
  Ověřeno: `done design-source {design_source: author}` zachová „author".
- [→] **flow-finish #3 — UI-feature fork** — PŘEŠLO do vlny `frontier-scheduler` (fork = paralelní
  track + confluence barrier = dataflow scheduler, ne `kind:fork` speciál). Viz níže.
- [x] **frontier-scheduler — HOTOVO** (F1–F6 + REJECTED). single `active_node`+`pending` → dataflow
  frontier (blueprint `frontier-scheduler.md`). F2 drive = frontier executor (ready množina jako akce,
  paralelní DISPATCH + non-blocking HUMAN-GATE souběžně, HALT L3, DECIDE+`run.sh skip`); F3 result.sh
  outcomes/inflight/`class`/FAIL-re-flow (un-complete cíl+downstream, 3× BLOCKER); F5 check C11/C12;
  F6 doc. selftest **26/26**, `pending` model pryč. Commity `457576d`→`d7774e6`.
- [x] **flow-finish — REJECTED halt** — HOTOVO (`4f6d4df`). `drive` na `status:blocked` (REJECTED /
  3× counter / BLOCKER) čistě zastaví (BLOCKED + důvod v `note`), ne re-nabídka gate; deploy-approve
  `REJECTED` → production se NEspustí. selftest +2.
- [x] **flow-finish #4 — re-run profil B reálnými agenty — HOTOVO/UZAVŘENO** — feature `GET /users/{id}`
  nad `dogfood/userflow/`, drive `2026-06-11-get-user`. Protaženo vision→bob→joey→**paralelní audit-frontier**
  (optimus ∥ sheldon ∥ heimdall ∥ vitek; edna správně vynechána `has_ui=false`). pytest **18 passed**
  (joey 5 integration AC, nezávisle ověřeno). **Engine (a-drift) happy-path = NULA** (fan-out i join čistě).
  Nálezy: 4 b-drift z vision→bob (B1 phantom PASS → **FIXNUTO**; B2 project-vs-feature DB flag; B3 statický
  graf-model vs Tony triage; B4 triage podcenila iterační režii) + **3 obsahové nálezy z audit-vrstvy**
  (D1 heimdall HIGH: neautentizovaný get-user = PII/enumerace, F8 → otevřené produktové rozhodnutí auth;
  D2 sheldon: impl detail ve spec; D3 vitek: chybějící typová anotace) + **1 ENGINE nález E1** (viz níže).
  Live běh ponechán pauznutý na audit-vrstvě (4 inflight), NEcommitnut do re-flow kaskády. Plná sklizeň:
  `handoffs/2026-06-11-flowfinish-4-realrun/CLOSE.md` (+ původní `HANDOFF.md`).
- [x] **flow-determinism E1+E2 — návratová strana frontieru HOTOVO** (vlna `2026-06-11-flow-determinism`).
  `frontier-scheduler` uměl *vydat* paralelní set, ale neměl deterministický příběh pro to, co se vrátí
  (nález #4). Doplněno tak, že gate dodá `(outcome, severity, returns_to, signature)` → engine přechod
  počítá deterministicky, **bez paměti orchestrátora**:
  - **E1 severity gating** — `blocking` (default, re-flow jako dřív) | `advisory` (finding zaznamenán,
    ŽÁDNÝ re-flow, uzel hotov → join pokračuje). Kosmetický nález (sheldon) se odděluje od blocking
    (heimdall) jako VSTUP, ne úsudek drive. (Dřív severity-blind: i kosmetika srazila 24 uzlů.)
  - **E1 payload-carry** — `signature` → `return_payload[cíl]`; `drive` ji deterministicky vytiskne při
    re-dispatchi (`↻ re-flow finding:`). Re-běh dostane CO opravit ze stavu, ne z paměti. Po PASS smazána;
    `findings` = append-only ledger (l2-review).
  - **E2 order-independence** — `completed` je cache; ready-rule počítá největší **downward-closed**
    podmnožinu (uzel platně-completed jen když i jeho aktivní producenti). Concurrent re-flow+completion
    nemůže „resurrektnout" stale uzel → frontier nezávislý na pořadí envelopů. **Empiricky ověřeno**
    (audit-batch ve 2 pořadích → identický ready set i payload).
  Dotčeno: `result.sh` (advisory/payload/findings), `run.sh drive` (tisk payloadu), `next.sh` (valid-fixpoint),
  `state.sh`, `templates/current-run.md`, `flow.md`, `frontier-scheduler.md`. selftest **34** (E1 +5, E2 +1).
  Zpětně kompatibilní (chybí-li severity = blocking).
- [x] **B3 — Tony triage → per-node model do stavu (determinismus, z #4)** — HOTOVO. Graf má statický `model:`
  per uzel, ale Tony feasibility triage rozhodne složitost→model za běhu; dřív drive vydal STATICKÝ model a
  override se „honoroval" ručně (nedeterministické). Nově Tony envelope nese `models: {node: model}` → result.sh
  validuje (∈ haiku/sonnet/opus, uzel ∈ graf) + zapíše do `model_overrides`; `drive` overlayuje
  (`model = override ∨ graf`, `*` = rozhodl triage). Přežívá re-flow. selftest +3 = **37**.
- [x] **B2 — feature-level DB flag `touches_db` (determinismus, z #4)** — HOTOVO. Chandler byl gated jen
  `project.has_db`, ale DB-projekt může mít **read-only featuru** (createdat/get-user: chandler běžel jako
  no-op). Nově Ted (zodpovědný architekt) emituje `touches_db` (vlastnost featury, NE jméno uzlu → flow-blind);
  graf gatuje chandlera `project.has_db && touches_db`, `ted→bob` má bypass `!(has_db && touches_db)`. `next.sh`
  flag() default `touches_db = has_db` (fail-safe: vynechá-li Ted, chandler běží jako dřív → backward-compat).
  Zrcadlí B3 (runtime úsudek agenta přebíjí statický graf). Dotčeno: `delivery.yaml` (chandler/ted→chandler/
  ted→bob), `next.sh` (PROJ regex + flag default), `ted-architect.md §5`. selftest **+2 = 47** (touches_db=false
  prořízne chandlera + default backward-compat). check C1–C12 OK; createdat reproducer drží (regrese čistá).
- [ ] **Auth na get-user (otevřené PRODUKTOVÉ rozhodnutí, z #4 D1)** — `GET /users/{id}` vrací email+role bez
  tokenu. Buď `security: [bearerAuth]`+`Depends(get_current_user)` (infra hotová, ~1ř) + rozhodnutí v
  decision.md/openapi, NEBO vědomě public s odůvodněním (F8: mlčení ≠ public). Autorizace zůstává deferred.
  Rozhodne člověk při návratu k feature; #4 jen odhalilo.
- [x] **B1 fix — result.sh path-existence (z #4)** — HOTOVO. `result.sh` output-validace nově ověří, že
  `outputs[].path` (je-li deklarováno) reálně existuje na disku; external/abstract typy přeskočeny,
  bez artifacts.yaml konzervativně přeskočeno. Zachytí phantom PASS (ledger tvrdí artefakt, soubor
  nikdy nevznikl — přesně #4 contract-bez-openapi nález). selftest **+2** (phantom path odmítnut /
  existující path projde) = **28/28**. Distribuce krytá `scripts/pipeline/` allowlistem. Zbývají
  b-drift B2–B4 (routing/triage — design, ne přímý engine fix).
- [x] **pipeline-loop-fix F3 — deterministický most handoff→envelope** — HOTOVO. Subagent dodá jen
  JUDGMENT (`outcome` + `changed`/`flags`/`severity`/`fault`/`models` + měření); `result.sh`
  **auto-derivuje z grafu** to, co je v něm zdroj pravdy: output typy uzlu (orchestrátor je už nemapuje
  ručně — to byl divergence-zdroj: dva orchestrátoři → různé envelopy ze stejného výstupu), `agent`,
  `phase`. Explicitní `outputs` s `path` přebijí → B1 path-check drží. `time` volitelné → `seconds=0`
  (honest „neměřeno", ne fabrikace). **Minimal envelope = `{run, node, outcome}`.** `returns_to` se
  nenese ručně (engine: `fault`→uzel / single-return; flow-blind). Dotčeno: `result.sh` (auto-derive +
  time optional), `templates/node-result.md` (minimal + ⊙/× anotace), `templates/handoff.md` (GATE
  OUTPUT srovnán na flow-blind judgment, `returns-to` pryč), `flow.md §dispatch krok 3`. selftest
  **+3 = 50** (minimal auto-derive + stav posun + explicitní path B1 drží). Detail: `FINDINGS.md §F3`.

## Architektonická rozhodnutí (immutable)

- **Žádní tech-specific agenti** — obecný Bob + `templates/stacks/` + `rules/`.
  Rozhodnutí: 2026-05-29.
- **Single source of truth: princip nahoru, nástroj dolů** — universal hygiena
  jen v `constitution.md`; tech-agnostic tvar v `rules/`; nástroj v `stack/`.
  Templaty NIKDY neopakují constitution. Rozhodnutí: 2026-05-30.
- **Uniformita = kanonický reference + scaffold, ne specialista** — „same stack
  → same code" vynucuje to, proti čemu se měří (soubor+kostra čtená všemi
  agenty), ne expertní agent. Enforcement (Vitek conformance) se přidá až při
  reálném driftu. Rozhodnutí: 2026-05-30.
- **Cast roste (učení), activation se zmenšuje (produkce)** — definovaný-ale-
  -neaktivní agent stojí ~0; profily aktivují podle složitosti. Rozhodnutí: 2026-05-30.
- **Runtime SSR zakázán** — SEO přes SSG/prerender nebo CMS-native; SSG≠SSR
  (build-time render = bezpečné). Rozhodnutí: 2026-05-30.
- **Frontend styling: tokeny + headless lib + CSS Modules** — NE Tailwind
  (zapleveluje markup), NE raw CSS sprawl. Chování/a11y z headless knihovny
  (solidjs → Kobalte), vizuál z tokenů + CSS Modules. Mezi projekty se liší
  jen tokeny (design = vědomá proměnná); komponentové API a chování identické.
  Rozhodnutí: 2026-05-30.
- **Rules/stack templaty jsou defaults, ne lock-in**; **constitution overlays
  additive a kombinovatelné**, vyšší vrstva přebíjí `rules/` default.

## Verze

Framework: 0.35.0
Wave `2026-06-11-frontier-scheduler` HOTOVÁ (F1–F6 dataflow frontier + REJECTED halt, selftest 26/26,
check C1–C12) — engine rewrite, bez verzovacího tagu. Předchozí: `flow-finish` (#1/#2/#3a, 14/14),
`wave-pipeline` (F1–F9, 11/11).
