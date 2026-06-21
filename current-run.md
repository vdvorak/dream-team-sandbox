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
run: null
wave_base: null
graph: delivery
status: idle
active_node: null
frontier: []
completed: []
outcomes: {}
skipped: []
counters: {}
awaiting_human: []
halt_gate: null
last_outcome: null
class: null
flags: {}
note: null
pending_delegations: []
findings: []
return_payload: {}
model_overrides: {}
epoch: 0
type_versions: {}
node_versions: {}
```

## Lidský přehled

Idle — wave `2026-06-21-motor-wave2a` uzavrena (terminal_reached: true, DONE, 2026-06-21).
Dalsi wave: 2b (AC-8 PTY/terminal) nebo 2c (Fly deploy + hardening) dle priority uzivatele.
