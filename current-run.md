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
active_node: product
frontier: []
completed:
- intake
- product
outcomes:
  intake: PASS
  product: PASS
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
epoch: 2
type_versions:
  spec: 2
  acceptance: 2
  has_ui: 2
node_versions:
  intake: 1
  product: 2
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
