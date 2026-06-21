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
run: 2026-06-21-containment-cage
wave_base: d15032c244be306133f70d7bbd9d271a2b976e6f
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
counters:
  spec-gate->product: 1
awaiting_human: []
halt_gate: null
last_outcome: PASS
class: feature
flags:
  has_ui: false
  has_db: false
  has_deploy: true
note: null
pending_delegations: []
findings:
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: '(1) spec-agnostika: odstranit stack/tool názvy ze specs/containment-cage.md
    — Smokescreen→"egress proxy", Fly/6PN/Network Policy/fly.workspace.toml→"host-enforced
    síťová politika / privátní síť", smazat názvy souborů (Dockerfile.workspace, entrypoint.sh)
    → "hardened workspace overlay artefakty", smazat env+port ($http_proxy=...:4750),
    smazat reference na agenty (alfred/ted) a gate (T2); konkrétní stack přesunout
    do stack/ nebo contracts/. Nadstandardní §Rozhraní přesunout do contracts/. (2)
    acceptance/containment-cage.md: doplnit povinné tagy ke VŠEM AC; bezpečnostní
    invarianty I1-I7 → [security].'
return_payload: {}
model_overrides: {}
epoch: 4
type_versions:
  spec: 4
  acceptance: 4
  has_ui: 3
node_versions:
  intake: 1
  product: 4
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
