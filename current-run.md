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
run: 2026-06-21-runtime-contract
wave_base: bae4948c571abc581856361d8da5cffee372ed02
graph: delivery
status: in_progress
active_node: spec-gate
frontier: []
completed:
- intake
- product
- spec-gate
outcomes:
  intake: PASS
  product: PASS
  spec-gate: PASS
skipped: []
counters:
  spec-gate->product: 1
awaiting_human: []
halt_gate: null
last_outcome: PASS
class: feature
flags:
  has_ui: false
  touches_db: false
  touches_server: false
  touches_shared_ui: false
  has_deploy: false
note: null
pending_delegations: []
findings:
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: 'spec-agnostika v specs/runtime-contract.md (7 míst): ř.20 "curl / CLI"
    → "generický klient bez aplikačního kódu"; ř.34 "healthz" → "zdravotní dotaz";
    ř.73 "HTTP+JSON" → smazat protokol; ř.79 "OpenAPI artefakt" → "verzovaný kontrakt";
    ř.91 "viz kontrakt (Ted)" → smazat jméno agenta; ř.93 "Ted definuje idempotency
    klíč/mutex" → "konkrétní mechaniku určí kontrakt"; ř.96 "listFiles" → "čtení souborů
    mimo sandbox". Acceptance je OK (neměnit).'
return_payload: {}
model_overrides: {}
epoch: 5
type_versions:
  spec: 4
  acceptance: 3
  has_ui: 3
  gate-output: 5
node_versions:
  intake: 1
  product: 4
  spec-gate: 5
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
