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
run: null                          # <YYYY-MM-DD-feature-slug> = wave-id; null když idle
graph: delivery
status: idle                       # idle | in_progress | blocked | done
class: null                        # feature | bugfix | improvement (intake klasifikace)
active_node: null                  # poslední dotčený uzel (inspekce/kompat); NEřídí routing
frontier: []                       # inflight: dispatchnuté-ale-ne-hotové uzly
completed: []                      # hotové uzly (= todo log běhu)
outcomes: {}                       # node -> OUTCOME (PASS/ACK/APPROVED…); fired() to čte
skipped: []                        # judged-skip uzly (run.sh skip); confluence je nepočítá
counters: {}                       # "from->to": N (failure-signature loop; 3 = BLOCKER)
epoch: 0                           # monotonní čítač verzí (incremental rebuild — stamp při completion)
type_versions: {}                  # artifact-type -> epoch: kdy byl typ naposledy změněn
node_versions: {}                  # node -> epoch: kdy uzel naposledy doběhl (staleness: vstupní typ novější než moje verze → re-run)
findings: []                       # append-only ledger gate-nálezů {node,severity,returns_to,signature}; člověk čte na l2-review
return_payload: {}                 # node -> [failure-signature]: blocking nález nesený do re-dispatch (E1 payload-carry)
model_overrides: {}                # node -> model: Tony triage přebíjí statický grafový model; drive ho čte (B3)
awaiting_human: []                 # non-blocking gaty (L2) čekající na člověka
halt_gate: null                    # blocking gate (L3 deploy-approve) držící celý běh
last_outcome: null                 # PASS | FAIL | APPROVED | ... z posledního gate
flags: {}                          # spec-odvozené flagy z uzlů (has_ui …); routing je čte
note: null                         # jednořádkový lidský kontext
```

## Lidský přehled

<orchestrátor sem píše 1-3 věty: co se zrovna dělá, na co se čeká, proč blocked>
