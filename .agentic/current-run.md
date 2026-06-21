# current-run.md — strojový stav běhu pipeline

Strojově čitelný stav grafu (`pipeline/delivery.yaml`). Vlastní orchestrátor. Čte
`scripts/pipeline/state.sh` (reporting — „hej Watsone") a `scripts/pipeline/next.sh`.
Jeden běh = jedna wave; po uzavření se stav archivuje do handoffu a resetuje na idle.

```yaml
run: null
graph: delivery
status: idle
class: null
active_node: null
frontier: []
completed: []
outcomes: {}
skipped: []
counters: {}
epoch: 0
type_versions: {}
node_versions: {}
findings: []
return_payload: {}
model_overrides: {}
awaiting_human: []
halt_gate: null
last_outcome: null
flags: {}
note: null
```

## Lidský přehled

Idle. Poslední vlna: `2026-06-13-p5-human-interaction` — **DONE** (P5 human-interaction registry
dodán přes celý self-hosted flow; archiv `handoffs/2026-06-13-p5-human-interaction/PROGRESS.md`,
ledger `runs/2026-06-13-p5-human-interaction/ledger.yaml`). Dogfood nálezy → `backlog/flow-self-host-gaps.md`.
