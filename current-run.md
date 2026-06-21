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
active_node: backend
frontier: []
completed:
- intake
- product
- spec-gate
- feasibility
- architecture
- backend
outcomes:
  intake: PASS
  product: PASS
  spec-gate: PASS
  feasibility: PASS
  architecture: PASS
  backend: PASS
skipped: []
counters: {}
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
findings: []
return_payload: {}
model_overrides: {}
epoch: 6
type_versions:
  spec: 2
  acceptance: 2
  has_ui: 2
  gate-output: 4
  contract: 5
  error-codes: 5
  reuse-decision: 5
  server-code: 6
  unit-tests: 6
node_versions:
  intake: 1
  product: 2
  spec-gate: 3
  feasibility: 4
  architecture: 5
  backend: 6
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
