---
wave: 2026-06-11-flow-determinism
from: orchestrator (Watson session)
to: next-session
type: wave-close
returns_to: null
timestamp: 2026-06-11T22:30:00+02:00
---

# Handoff: flow-determinism — return-strana frontieru + dispatch-model zdeterminizovány

Vlna vyrostla z nálezů `flow-finish #4` (engine E1 + b-drift B3) pod jediným vodítkem:
**flow = čistá funkce vstupů.** Stejné vstupy (graf + intake-class + sekvence envelopů) →
deterministické kroky i výstupy; žádná závislost na paměti orchestrátora ani ručním
„honorování". Tři genuine determinismové mezery zavřené a otestované; B2 + auth ponechány
jako rozhodnutí (níže).

## Co se zavezlo (4 commity)

| # | commit | co |
|---|---|---|
| B1 | `a3fde52` | `result.sh` path-existence — phantom PASS odmítnut (output musí existovat na disku) |
| E1 | `2c343d3` | severity gating + payload-carry + findings ledger (return-strana) |
| E2 | `732b6ef` | frontier order-independence (downward-closure self-heal) |
| B3 | `fa237dd` | Tony triage → per-node model do stavu (drive ho čte, ne ruční override) |

selftest **37** (z 26), `check` graf C1–C12 OK. Vše zpětně kompatibilní.

## Princip přechodu (nový kontrakt return-strany)

Gate uzel dodá `(outcome, severity, returns_to, signature [, models])`; **engine přechod
počítá deterministicky**:

- **severity** (E1): `blocking` (default) → re-flow (un-complete cíl + forward-downstream,
  counter++, 3× BLOCKER). `advisory` → finding zaznamenán, uzel **hotov** (join pokračuje),
  ŽÁDNÝ re-flow. Kosmetický nález (sheldon spec-čistota) oddělen od blocking (heimdall
  security) jako VSTUP gate, ne úsudek drive.
- **payload-carry** (E1): `signature` → `return_payload[cíl]`; `drive` ho vytiskne při
  re-dispatchi (`↻ re-flow finding:`). Re-běh dostane CO opravit ZE STAVU, ne z paměti.
  Smaže se po úspěšném re-běhu cíle; `findings` = append-only ledger (l2-review).
- **order-independence** (E2): `completed` je cache; ready-rule počítá největší
  **downward-closed** podmnožinu (uzel platně-completed jen když i jeho aktivní producenti).
  Concurrent re-flow+completion nemůže „resurrektnout" stale uzel.
- **model** (B3): `models: {node: model}` od Tonyho → `model_overrides` ve stavu; `drive`
  overlayuje (`model = override ∨ graf`, `*` = triage). Přežívá re-flow.

## Empirické důkazy (ne jen odvozeno)

- **E2 order-independence:** audit-batch `optimus PASS ∥ heimdall FAIL→ted` ve 2 pořadích →
  **identický ready set `[ted]`** i payload `ted←AUTH_MISSING`, ač raw `completed` list se
  mezi pořadími liší (resurrektnutý optimus je přes valid-fixpoint zneplatněn).
- **B3:** drive `DISPATCH bob` nese `haiku*` (triage), ne grafový `sonnet`.
- (kontext) **E1 motivace:** sandbox #4 ukázal, že bez severity srazí kosmetický
  sheldon→vision **24 uzlů** a pohltí HIGH security — to už nenastane (advisory).

## Stavová pole (current-run.md) — přibyla

`findings: []` (ledger), `return_payload: {}` (actionable carry), `model_overrides: {}`
(triage model). `templates/current-run.md` + `state.sh` srovnané. Live běhy bez těchto polí
jsou kompatibilní (setdefault doplní).

## Klíčové soubory

- `scripts/pipeline/result.sh` — advisory/blocking větve, payload-carry/clear, findings,
  model-override validace+apply, B1 path-existence.
- `scripts/pipeline/run.sh` (`drive`) — tisk re-flow finding + model overlay.
- `scripts/pipeline/next.sh` — valid-fixpoint (E2) ve frontier ready-rule.
- `scripts/pipeline/selftest.sh` — E1 (+5), E2 (+1), B3 (+3), B1 (+2) scénáře.
- `flow.md §drive` + `frontier-scheduler.md §FAIL/return` — return-strana zdokumentována.

## Otevřené (NE engine-determinismus — rozhodnutí, ne díry)

- **B2 — feature-level DB flag.** Dnes `has_db` (projektový) routuje ted→chandler u KAŽDÉ
  feature; chandler u read-only no-opne (deterministicky, ale zbytečný dispatch). Návrh:
  Ted nastaví `touches_db` (feature-level) → frontier prořízne chandlera. **Tradeoff
  (vyžaduje rozhodnutí):** Tedovo „touches_db: false" vs. riziko, že feature DB přece sahá
  → halucinovaná/zapomenutá migrace. + default-sémantika (absent = běží, kvůli zpětné
  kompatibilitě). Není to determinismová díra (chandler je dnes deterministický) → efektivita
  + design. Probrat, ne protlačit.
- **auth na get-user (D1, produktové).** `GET /users/{id}` vrací email+role bez tokenu.
  Buď `security:[bearerAuth]`+`Depends(get_current_user)`, nebo vědomě public s odůvodněním
  (F8). Člověk rozhodne při návratu k feature. Viz `handoffs/2026-06-11-flowfinish-4-realrun/CLOSE.md`.

## Jak navázat

`bash scripts/pipeline/selftest.sh` (37 zelený) = engine zdravý. Pokud B2: edge ted→chandler
gating + `touches_db` atom v `next.sh` (atom()+flag_live()) + Ted contract + selftest
prune-scénář + default-direction rozhodnutí. Jinak engine-determinismus z #4 je uzavřen.
