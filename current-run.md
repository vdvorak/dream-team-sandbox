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
counters:
  spec-gate->product: 2
awaiting_human: []
halt_gate: null
last_outcome: PASS
class: feature
flags:
  has_ui: false
  has_db: false
  has_deploy: true
  touches_db: false
  touches_server: true
  touches_shared_ui: false
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
- node: spec-gate
  severity: blocking
  returns_to: product
  signature: 'spec-cleanliness (3 zbylé konkrétnosti v specs/containment-cage.md):
    ř.37 "agent.py" → "workspace agent proces"; ř.35 konkrétní domény (api.github.com,
    <CF_ACCESS_TEAM>.cloudflareaccess.com) → "proxy s doménovým allowlistem (konkrétní
    domény v contracts/)"; ř.54 CIDR 169.254.0.0/16 → "metadata endpoint". Plus kompletní
    sweep: žádný název souboru/IP/CIDR/doména/port/env-var v specs/**. AC tagy jsou
    OK (neměnit), stack/ + contracts/ OK.'
return_payload: {}
model_overrides: {}
epoch: 10
type_versions:
  spec: 6
  acceptance: 5
  has_ui: 5
  gate-output: 8
  contract: 9
  error-codes: 9
  rules: 9
  server-code: 10
  unit-tests: 10
node_versions:
  intake: 1
  product: 6
  spec-gate: 7
  feasibility: 8
  architecture: 9
  backend: 10
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
