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
run: 2026-06-21-motor-wave2a
wave_base: d647abd4ffa23e11c92500645c32d24f333cdb20
graph: delivery
status: in_progress
active_node: code-lint
frontier: []
completed:
- intake
- product
- spec-gate
- feasibility
- backend
- code-lint
- architecture
outcomes:
  intake: PASS
  product: PASS
  spec-gate: PASS
  feasibility: PASS
  backend: PASS
  code-lint: PASS
  architecture: PASS
skipped: []
counters:
  qa->architecture: 1
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
note: null
pending_delegations: []
findings:
- node: qa
  severity: blocking
  returns_to: architecture
  signature: ''
return_payload: {}
model_overrides: {}
epoch: 11
type_versions:
  spec: 2
  acceptance: 2
  has_ui: 2
  gate-output: 11
  contract: 9
  error-codes: 9
  reuse-decision: 9
  server-code: 10
  unit-tests: 10
node_versions:
  intake: 1
  product: 2
  spec-gate: 3
  feasibility: 4
  backend: 10
  code-lint: 11
  architecture: 9
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
