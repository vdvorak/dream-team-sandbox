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
active_node: spec-gate
frontier: []
completed:
- intake
outcomes:
  intake: PASS
skipped: []
counters:
  spec-gate->product: 2
awaiting_human: []
halt_gate: null
last_outcome: FAIL
class: feature
flags:
  has_ui: false
  touches_db: false
  touches_server: true
  touches_shared_ui: false
  has_deploy: false
note: null
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
return_payload:
  product:
  - 'specs/runtime-control-plane.md — zbývá 6 výskytů agnostika-leaku (původní 4 kategorie
    OPRAVENY). KOMPLETNÍ scrub, ne po položkách:

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
model_overrides: {}
epoch: 5
type_versions:
  spec: 5
  acceptance: 5
  has_ui: 5
node_versions:
  intake: 1
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
