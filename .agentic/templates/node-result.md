---
cache_key: template-node-result-v1.0
type: template
---

# node-result — strojová obálka výsledku uzlu („/done" v souboru)

Co uzel vyprodukoval, když dokončil práci. Jednotná struktura = **strojový
ekvivalent** handoff `=== GATE OUTPUT ===` bloku + cost/čas. Zpracuje
`scripts/pipeline/result.sh`: ověří (typy proti `pipeline/artifacts.yaml`, uzel proti
grafu), připíše do `runs/<run>/ledger.yaml` (append-only) a posune `current-run.md`
(completed / last_outcome / counters). V budoucí aplikaci je tohle payload endpointu
`/done` — odtud živé sledování běhu.

Loop: uzel dokončí → `result.sh <envelope>` (= „/done") → stav se posune →
`next.sh` spočítá další uzel. Žádné ruční přepisování stavu LLM (determinismus).

**Most handoff→envelope (F3):** orchestrátor NEmapuje výstupy na typy ručně (divergence-zdroj).
`result.sh` **auto-derivuje z grafu** (`delivery.yaml` je zdroj pravdy), co uzel produkuje
(`outputs` typy), kdo ho dělá (`agent`) a v jaké fázi (`phase`). Orchestrátor dodá jen **JUDGMENT**.

**Tři druhy polí** (legenda značek níže): `⊙` judgment (úsudek orchestrátora/agenta) ·
`×` auto-derive z grafu (engine doplní) · `×` **měřeno** platformou/wrapperem (propsat z telemetrie,
nikdy z hlavy). Měřená pole (`cost`, `time`) NEjsou úsudek — viz pravidlo měření níže.

**Minimal envelope** (vše ostatní doplní `result.sh` z grafu):
```yaml
run: <YYYY-MM-DD-feature-slug>     # = wave/run id
node: <node id z delivery.yaml>
outcome: PASS                      # PASS | FAIL | APPROVED | ACK | DONE | BLOCKER
```

**Plný envelope** (× = auto-derive z grafu, lze vynechat; ⊙ = judgment, dodá agent/orchestrátor;
× = měřeno platformou/wrapperem — propsat, NIKDY psát z hlavy):
```yaml
run: <YYYY-MM-DD-feature-slug>     # ⊙ run id
node: <node id z delivery.yaml>    # ⊙ který uzel (orchestrátor zná z drive DISPATCH)
outcome: PASS                      # ⊙ PASS | FAIL | APPROVED | ACK | DONE | BLOCKER
agent: <short>                     # × z grafu (null u router/join/human-gate)
phase: T1|T2|T3|T3-post            # × z grafu
outputs:                           # × default = output typy uzlu z grafu. Explicitní
  - type: server-code              #   (typicky s `path`) PŘEBIJE → B1 path-check ověří existenci.
    path: server/
changed: [server-code] | none      # ⊙ co se reálně změnilo (re-flow scoping); vynech = všechny outputy
flags: { has_ui: false }           # ⊙ spec/feature flagy (Vision has_ui, Ted touches_db)
severity: blocking | advisory      # ⊙ gate FAIL: blokuje re-flow vs jen zaznamenej
signature: <co opravit>            # ⊙ FAIL: actionable payload k cíli (= weak-spot)
fault: db-schema|contract|...      # ⊙ diagnostik (Ted): doména vady → graf přeloží na uzel
models: { bob: haiku }             # ⊙ triage (Tony): per-node model override
tier: XS|S|M|L                     # ⊙ orchestrátor: rubrika složitosti (jediný úsudek v měření;
                                   #   model/cost/agent se derivují z ledgeru → routing-log z ledgeru, ne ruční řádek)
cost: { model: sonnet, input_tokens: 0, output_tokens: 0, credits: 0.0 }   # × MĚŘENO platformou
time: { started: <ISO>, ended: <ISO>, seconds: null }   # × MĚŘENO wrapperem; chybí → seconds=0 (honest)
note: <one-line nebo null>         # ⊙
```
**Měřené veličiny (`cost`, `time`) se NIKDY nepíšou z hlavy.** Jsou to objektivní data
platformy/wrapperu, ne úsudek. Orchestrátor je **propíše** z `<usage>` bloku Agent toolu:
`subagent_tokens` → `cost.input_tokens`/`output_tokens`, `duration_ms` → `time.seconds`.
Chybí-li telemetrie → honestně `0` / `seconds: null` (engine to označí **„neměřeno"**), NIKDY fabrikace.
Priorita ceny v summary: **měřeno (`credits`) > odhad z `model-prices.yaml` (z tokenů) > neměřeno**.

Pozn.: `returns_to` envelope NEnese ručně — engine ho odvodí z grafu (`fault`→uzel, nebo
single-return auto-resolve). Agent zůstává **slepý vůči flow** (nejmenuje souseda).
