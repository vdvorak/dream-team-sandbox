---
cache_key: template-current-run-v1.0
type: template
---

# current-run.md — strojový stav běhu pipeline

Formalizuje koncept `flow.md §current-wave.md` jako **strojově čitelný** stav grafu
(`pipeline/delivery.yaml`). Vlastní orchestrátor. Čte:
`scripts/pipeline/state.sh` (reporting — „hej Watsone") a `scripts/pipeline/next.sh`
(další uzel). Jeden běh = jedna wave.

Routing řídí **dataflow frontier** (`run.sh drive` → `next.sh --emit frontier`): uzel je
*ready*, když doběhli všichni jeho aktivní producenti. Orchestrátor po dokončení uzlu
volá `run.sh done` (posune `completed`/`outcomes`/`frontier`). Po uzavření wave se stav
archivuje do handoffu a soubor se resetuje (`status: idle`, `run: null`). Tohle je
**runtime** soubor (projekt-specifický, synced se nepřepisuje).

```yaml
run: 2026-06-21-runtime-lifecycle
wave_base: ce416f24808fd65e0279d85cfb5813ea62afac88
graph: delivery
status: in_progress
active_node: performance
frontier: []
completed:
- intake
- spec-gate
- feasibility
- architecture
- backend
- code-lint
- qa
- performance
- security
- code-quality
- product
outcomes:
  intake: PASS
  spec-gate: PASS
  feasibility: PASS
  architecture: PASS
  backend: PASS
  code-lint: PASS
  qa: PASS
  performance: PASS
  security: PASS
  code-quality: PASS
  spec-audit: FAIL
  product: PASS
skipped: []
counters:
  spec-gate->product: 0
  spec-audit->product: 1
awaiting_human: []
halt_gate: null
last_outcome: PASS
class: feature
flags:
  has_ui: false
  touches_db: false
  touches_server: true
  touches_shared_ui: false
  has_deploy: false
note: 'resolve-loop: spec-gate->product odblokováno (counter 3→0) @ 2026-06-21T18:24:45.694413+00:00'
pending_delegations: []
findings:
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: 'specs/runtime-control-plane.md — 4 druhy porušení agnostiky (spec musí
    mluvit doménově, ne implementačně/kontraktně):

    1) ř.12: přímá cesta `contracts/runtime-contract.md` → přeformulovat na "implementuje
    slice 1 runtime kontraktu (v1.0.0)".

    2) ř.27,30,31,32,40,62-64: HTTP metody/cesty (POST ensure, GET {project_id}, /v1/healthz,
    …/git/files/terminal) → doménové akce (zajisti/stav/uspi/zruš prostředí; zdravotní
    kontrola).

    3) ř.35,55,95: HTTP/error kódy v textu (502 ERR_PROVISION_FAILED, 401 ERR_UNAUTHORIZED,
    503 ERR_RUNTIME_UNAVAILABLE) → "server vrátí chybu (fail-closed)" / "selhání ověření"
    / "server nedosažitelný".

    4) ř.40-41: operationId (ensureEnvironment/getEnvironment/sleepEnvironment/destroyEnvironment)
    → doménové pojmy "čtyři lifecycle operace: zajisti/stav/uspi/zruš prostředí".

    Acceptance soubor je OK (HTTP/error kódy tam patří). Oprav JEN spec.'
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: 'specs/runtime-control-plane.md — zbývá 6 výskytů agnostika-leaku (původní
    4 kategorie OPRAVENY). KOMPLETNÍ scrub, ne po položkách:

    - ř.5 note: "git/files/terminal" → "repozitář/soubory/terminál" nebo "AC-6/7/8".

    - ř.64 Scope Out: závorka "(git clone uvnitř kontejneru/workspace)" → smazat,
    nech jen "klonování repozitáře".

    - ř.71: "(název a tvar implementace jsou rozhodnutím CTO/architekta)" → smazat
    (role-reference; patří do handoffu, ne spec).

    - ř.78: "volá se z `healthz`" → "volá se z operace zdravotní kontroly".

    - ř.80-81: schema pole `control_url`/`terminal_url` → "opaque connection handle
    (adresy v connection objektu)".

    - ř.91: `2xx` → "úspěšná odpověď s aktuálním stavem".

    - ř.95-96: `http://localhost:9999` + "AC-11 grep test" → "placeholder adresa bez
    substrát-nounu" (vynech konkrétní URL i test-instrukci).

    NAVÍC projeď CELÝ spec řádek po řádku a odstraň JAKÝKOLI zbylý: HTTP sloveso/cesta/status/třída,
    error kód, název pole schématu, endpoint token, tool/command name, role/agent
    reference, file-path. Tohle musí být POSLEDNÍ cleanup — žádný další výskyt téhož
    druhu.'
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: 'STRUKTURÁLNÍ fix (ne další kosmetika): spec má být ČISTĚ BEHAVIORÁLNÍ.
    Vyhodit VŠECHNO "jak" — to patří downstream (architecture/contract/rules/stack),
    ne do product specu:

    - Auth mechanismus (mTLS / service token) → smazat; behaviorálně: "klient se autentizuje;
    neověřená identita → odmítnuto". (Mechanismus žije v kontraktu §3.)

    - Datová pole volání (project_id, repo.url, tool, phase, contract_version, connection,
    Environment jako typ) → smazat schema-tvary; behaviorálně: "zajisti prostředí
    pro projekt ze zdrojového repozitáře".

    - Storage/concurrency mechanika (in-memory store, serializace) → smazat; behaviorálně:
    "souběžné zajištění → jediné prostředí (idempotentně); stav přežívá mezi voláními".

    - Stub/dev provider jako test-double → behaviorálně: "enforcement je delegován
    na zaměnitelný provider; lokální varianta nevynucuje reálný enforcement".

    - CELÁ sekce §Enforcement-provider rozhraní s funkčními signaturami provision()/teardown()/sleep()/health()
    → SMAZAT ze specu. Návrh tohoto rozhraní je práce uzlu `architecture` (ted-architect),
    ne product specu. Spec smí jen: "server deleguje enforcement na zaměnitelný provider;
    provider garantuje aktivní enforcement nebo vrátí chybu; klient dostane connection
    handle JEN když je enforcement aktivní (fail-closed)".

    Výsledek = krátký behaviorální dokument (operace jako doménové akce, stavový automat,
    idempotence, fail-closed garance, standalone). Žádné signatury, schémata, mechaniky.'
- node: spec-gate->product
  severity: intervention
  returns_to: null
  signature: resolve-loop counter 3->0 @ 2026-06-21T18:24:45.694413+00:00
- node: spec-audit
  severity: blocking
  returns_to: product
  signature: 'acceptance/runtime-control-plane.md nesesynchronizován s kontraktem
    v1.1.0 (kód je správně, chyba jen v acceptance dokumentu):

    F1 (BLOCKER): AC-1g dovoluje "422 ERR_CLONE_FAILED nebo validační 400" pro syntakticky
    chybné repo.url. Kontrakt v1.1.0 §8: malformed URL = schema chyba = výhradně 400
    ERR_INVALID_REQUEST; ERR_CLONE_FAILED (422) je JEN runtime selhání klonu (validní
    url, nedostupný). Oprav AC-1g: PASS = 400 ERR_INVALID_REQUEST; 422 = FAIL.

    W1: AC-1b a AC-9a testují contract_version "1.0.0" -> oprav na "1.1.0".

    W2: AC-1h, AC-12b, AC-13b PASS jen "400 (additionalProperties odmítnuto)" bez
    kódu -> doplň "400 ERR_INVALID_REQUEST".

    (W3 healthz 503 v OpenAPI = advisory pre-existing, odloženo slice 2.)'
return_payload: {}
model_overrides: {}
epoch: 25
type_versions:
  spec: 19
  acceptance: 20
  has_ui: 19
  gate-output: 25
  reuse-decision: 11
  server-code: 13
  unit-tests: 13
node_versions:
  intake: 1
  spec-gate: 21
  feasibility: 22
  architecture: 23
  backend: 13
  code-lint: 14
  qa: 24
  performance: 25
  security: 17
  code-quality: 18
  product: 20
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
