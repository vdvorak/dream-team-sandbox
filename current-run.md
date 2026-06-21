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
  spec-gate->product: 1
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
return_payload:
  product:
  - 'specs/runtime-control-plane.md — 4 druhy porušení agnostiky (spec musí mluvit
    doménově, ne implementačně/kontraktně):

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
model_overrides: {}
epoch: 3
type_versions:
  spec: 3
  acceptance: 3
  has_ui: 3
node_versions:
  intake: 1
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
