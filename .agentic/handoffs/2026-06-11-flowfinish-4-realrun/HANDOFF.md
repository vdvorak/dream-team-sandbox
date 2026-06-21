---
wave: 2026-06-11-flow-finish-4
from: orchestrator (Watson session)
to: next-session
type: mid-run-handoff
returns_to: null
timestamp: 2026-06-11T12:10:00+02:00
---

# Handoff: flow-finish #4 — profil B reálnými agenty (ROZBĚHNUTO, vision→bob hotovo)

## JAK NAVÁZAT (TL;DR — řekni „pokračuj")

Drive běh `2026-06-11-get-user` je **živý, uprostřed** (6/~11 uzlů hotovo, čeká `joey`).
Engine se nesahá — jen pokračuj v driveru a dispatchuj reálné subagenty. **Default akce
= moje doporučení: nejdřív C, pak B** (viz §Rozhodnutí). Pokud chce uživatel A (dorazit
track), recept je v §A.

**Pracovní kontext (každá session si nastav):**
```bash
cd /home/vitek/dev/AI/dream-team/dogfood/userflow
export PIPELINE_GRAPH=/home/vitek/dev/AI/dream-team/pipeline/delivery.yaml
RUN=/home/vitek/dev/AI/dream-team/scripts/pipeline/run.sh
bash $RUN status        # ověř: completed=6, active_node=joey, status=in_progress
bash $RUN drive         # vydá DISPATCH joey (agent joey-qa, model sonnet)
```
Dogfood **nemá vlastní `.agentic/`** → `PIPELINE_GRAPH` musí ukazovat na framework graf,
jinak run.sh/next.sh/result.sh graf nenajdou. Platí pro `drive`, `done`, `status`, `check`.

## Co se dělá a proč (účel #4)

**Úkol z STATE.md:** flow-finish #4 = re-run profilu B (`dogfood/userflow/`) **reálnými
agenty** přes celý drive (ne selftest stub) → ověřit runner proti realitě, měřit **(b)
drift** v obsahu uzlů (engine (a) už ověřen selftestem 26/26).

**Zvolená feature:** `GET /users/{id}` — fetch jednoho uživatele. Vybráno protože substrát
už má `create-user` (POST /users) **kompletně postavený** → re-run create-user by jen
přepisoval existující soubory (slabý test). `GET /users/{id}` neexistuje → agenti reálně
produkují; staví na existujícím `UserView` + `app_user` tabulce → čistě testuje read/query
cestu + reuse-decision. has_ui=false (lineární backend track, bez fork).

## Co session udělala (vision→bob, 6 uzlů)

Driveno přes `run.sh drive` → reálný subagent → `run.sh done <envelope>`. Subagenti =
`general-purpose` Task s **model override dle routingu** (Agent tool `model:` param),
naprimovaní z `agents/<short>.md` definice. Envelopy do `/tmp/gu-*.yaml`.

| # | uzel | agent / model | výsledek (reálný) |
|---|---|---|---|
| 1 | `intake` | router (můj úsudek) | DECIDE → **class: feature** |
| 2 | `vision` | vision-po / sonnet | spec + acceptance (5 AK), has_ui=false, reuse UserView+find_by_id |
| 3 | `tony-feasibility` | tony-cto / opus | PASS, XS→**haiku**, reuse claim potvrzen na real kódu, UUID→path param typ |
| 4 | `ted` | ted-architect / opus | NON_BREAKING, reuse-existing, prefix `/users/{id}`, kód `user_not_found`, contracts/api/* |
| 5 | `chandler` | chandler-db / sonnet | schema-change **NONE** (no-op správně), app_user.id TEXT PK |
| 6 | `bob` | bob-backend / **haiku** | `server/src/users/{router,service}.py` + test, **pytest 13/13 (ověřeno nezávisle)** |

**Reálné artefakty na disku** (dogfood NENÍ pod git parent repa — `.gitignore` jen
*.pyc/*.db; nové soubory vratné jen smazáním, existující create-user nedotčen):
- `specs/get-user.md`, `acceptance/get-user.md`
- `contracts/api/openapi.yaml`, `contracts/error-codes.md`, `contracts/api/get-user.decision.md`
- `server/src/users/__init__.py`, `router.py`, `service.py`; `server/tests/test_users.py`; `server/src/main.py` (router registrace)
- ledger: `dogfood/userflow/runs/2026-06-11-get-user/ledger.yaml` (6 záznamů)

## Výsledek měření

**Engine (a-drift): NULA.** Frontier executor prohnal reálný multi-agent řetěz bezchybně:
reset → DECIDE(intake) → DISPATCH vision→tony→ted→chandler→bob → (joey ready). Každý
`done`/`drive`/`frontier` přechod správně. **Selftest-ověřený engine drží i proti reálným
agentům.** Hlavní validace #4 ✓.

**Obsah/realita (b-drift): 4 nálezy** (= to, co #4 mělo najít — engine OK, hranice
člověk/obsah má mezery):

- **B1 (nejdůležitější, má přímý fix) — stub ledger LHAL o artefaktu.** Minulý
  `post-users` běh zapsal `ted→contract: PASS`, ale `contracts/api/openapi.yaml` +
  `error-codes.md` v repu **nikdy nevznikly**. Reálný Ted to odhalil a musel create-user
  contract dofouknout. → **`result.sh` validuje `outputs[].type` proti artifacts.yaml, ale
  NEověřuje, že `outputs[].path` reálně existuje na disku** → phantom PASS projde.
  **FIX: přidat do result.sh deterministickou kontrolu existence cesty** (viz §C).
- **B2 — project-level vs feature-level flagy.** `has_db=true` je projektový → routuje
  ted→chandler u KAŽDÉ feature, i read-only bez DB práce. Chandler správně no-opnul, ale
  je to zbytečný dispatch. Graf nemá feature-level signál „tahle feature sahá na DB".
  → buď spolehnout na agentní disciplínu (risk hallucinace migrace), nebo Ted nastaví
  feature-flag (např. `touches_db: false`) a frontier chandlera prořízne (`run.sh skip`).
- **B3 — statický model v grafu vs Tony triage.** Graf má `bob: model: sonnet` natvrdo,
  ale Tony triage (jeho práce) řekl XS→haiku. `drive` vydává STATICKÝ model; nic
  nepropojuje Tonyho per-task rozhodnutí do DISPATCH řádku — honoroval jsem haiku ručně.
  Design říká „triage přebíjí statiku", runner mechanismus nemá. → Tony gate-output by mohl
  zapsat per-node model override do current-run (jako flagy), `drive` by ho četl.
- **B4 — triage podcenila iterační režii.** haiku XS slice ZVLÁDL (13/13), ale **66
  tool-uses / ~50 min wall**. „XS→haiku" počítal s one-shot; realita multi-file slice
  (router+service+testy+main wiring+spuštění pytestu) = hodně iterací i když triviálních.
  Levný-per-token ≠ levný-per-wall. → triage by měl vážit i koordinační/iterační náklad.

## Rozhodnutí (čeká na uživatele) — doporučuju C pak B

- **A) Dorazit track** — joey → optimus/sheldon/heimdall/vitek gaty → audit-join →
  l2-review (human-gate). Ověří gate uzly + human-gate na reálných agentech. ~5 dispatchů.
  Recept v §A. Volitelné (engine už validován; tohle testuje gate-uzly naostro).
- **B) Zabalit + zaznamenat** — nálezy B1–B4 do STATE.md Open Items + uzavřít wave. #4
  splnilo účel (engine validován, drift zmapován).
- **C) Hned implementovat B1** — `result.sh` path-existence check. Jediný nález s přímým
  deterministickým fixem do engine; chytil by přesně ten phantom-PASS, co #4 odhalil.
  Detail v §C.

## §C — recept na B1 fix (result.sh path-existence)

`scripts/pipeline/result.sh`, validační blok (po kontrole `outputs.type ∈ artifacts`,
kolem ř. 114 `for o in (env.get("outputs") or []):`). Přidat: pokud `o.get("path")` a
cesta je projektová (ne external typ) → ověřit `os.path.exists(path)`; když ne → `fail()`
(nevalidní envelope, nic se nezapíše). Pozor: některé typy jsou abstraktní/external
(viz `artifacts.yaml` `external:`/`abstract:`) — těm path-check přeskočit. Přidat
negativní test do `selftest.sh` (envelope s neexistující path → exit 1). Pak `check.sh`
beze změny, selftest +1. Zaktualizovat STATE.md Open Item B1 na hotovo.

POZN: tohle je fix v ENGINE (`scripts/pipeline/`), ne v dogfoodu. Po fixu rozšířit
`agentic-sync.sh` distribuci (už tam result.sh je) — ověř `bash scripts/pipeline/selftest.sh`.

## §A — recept na dorážení tracku (pokud A)

Pokračuj stejným patternem (drive → reálný subagent z `agents/<short>.md` → `run.sh done`):

1. `bash $RUN drive` → DISPATCH **joey** (joey-qa / sonnet). Joey = integration/acceptance
   testy nad 5 AK z `acceptance/get-user.md`. Reálně spusť pytest. Envelope outputs:
   `integration-tests`. POZOR: joey může najít FAIL → return hrana `when: FAIL` zpět na bob
   (re-flow, counter++). Tady se testuje FAIL-re-flow naostro.
2. Po joey PASS → drive vydá **paralelní frontier**: optimus (perf) ∥ sheldon (spec-check)
   ∥ heimdall (security) ∥ vitek (quality). Dispatchni je SOUBĚŽNĚ (frontier model je
   paralelní). Modely dle grafu/routingu (heimdall=opus, zbytek sonnet). Každý `run.sh done`.
3. Po všech čtyřech → **audit-join** (join, auto-advance, neprodukuje práci) → drive sám
   přepočítá → **l2-review** (human-gate, non-blocking, interaction `l2-review`). Drive
   vydá HUMAN-GATE → čeká lidský ACK. To je terminál tracku pro tuhle feature (has_deploy
   =false → žádná T3-post release větev).
4. Pak `run.sh summary 2026-06-11-get-user` (ledger.sh) = cost+čas přehled celého běhu.

Naprimování subagenta: přečti `agents/<short>.md` (identita + odpovědnosti + výstupní GATE
OUTPUT formát), dej mu reálné vstupy (spec/contract/kód v dogfoodu), nech ho psát do jeho
write-scope, vrať GATE OUTPUT blok. Model override přes Agent tool `model:` param.

## Klíčové cesty / fakta pro rychlou orientaci

- Runner: `scripts/pipeline/run.sh` (start/drive/done/status/skip/summary/check); frontier
  executor je funkce `drive()` v run.sh; výsledky `result.sh`; routing `next.sh --emit frontier`.
- Stav běhu: `dogfood/userflow/current-run.md` (frontier model: completed/outcomes/frontier/
  awaiting_human/halt_gate/class/flags).
- Graf: `pipeline/delivery.yaml` (uzly+hrany); typy `pipeline/artifacts.yaml`; human-gaty
  `pipeline/interactions.yaml`.
- Agent definice: `agents/<short>.md` (vision-po, tony-cto, ted-architect, chandler-db,
  bob-backend, joey-qa, optimus-perf?, sheldon-?, heimdall-security, vitek-quality — ověř
  přesné soubory `ls agents/`).
- Envelope formát: `templates/node-result.md`. Envelopy pro tenhle běh: `/tmp/gu-*.yaml`
  (transientní; ledger v projektu je trvalý).

## Weak spot / na co dát pozor

- Bez `export PIPELINE_GRAPH=...` z dogfood adresáře runner graf nenajde (dogfood nemá
  `.agentic/`). To je samo o sobě drift-pozorování (profil B předpokládá projekt se
  zadrátovaným grafem; dogfood ho nemá).
- Dogfood není pod git → žádný `git checkout` rollback artefaktů; jen ruční smazání nových.
- haiku dispatch trval ~50 min wall (B4) — počítej s tím u dalších levných dispatchů.
- Pokud uživatel řekne jen „pokračuj" bez volby A/B/C → default = **C** (engine fix, jediný
  s přímým dopadem), pak nabídni B (zaznamenat) a zeptej se na A.
