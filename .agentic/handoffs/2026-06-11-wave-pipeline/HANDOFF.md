---
wave: 2026-06-11-wave-pipeline
from: orchestrator
to: next-session
type: milestone-handoff
returns_to: null
timestamp: 2026-06-11T00:00:00+02:00
---

# Handoff: wave-pipeline (diagnostická) → pipeline-loop-fix

## Stav (jak chápu situaci)

Předchozí vlna (`init-determinism`) uzavřela **APPLY engine** pro founding
(compose.sh, apply-feature.sh) — substrát se tvoří deterministicky. Tato vlna
testuje druhou půlku: **per-issue flow přes `run.sh drive`** (T1→T2→T3) dogfoodem naostro.
Substrát: `dogfood/userflow/` (python-fastapi+auth/jwt, čerstvě foundnutý přes compose.sh,
gitignored). Executor profil B: orchestrátor řídí drive, každý uzel = čerstvý izolovaný
subagent nakrmený rolí `agents/<short>.md`.

Dogfood `POST /users` protáhl flow přes `intake` → `vision` (reálný subagent, spec 49ř +
8 AC). Po prvním `done` smyčka padla — viz F4.

Detailní nález: `FINDINGS.md` (v tomto adresáři) — vstupní bod pro opravu.

## Plán (co dělalo / co tato session udělala)

1. Foundnutý čerstvý substrát `dogfood/userflow/` přes `compose.sh` (gitignored,
   `.gitignore` doplněn).
2. Protažen `POST /users` reálným drive flow: `run.sh start` → `drive` → intake →
   dispatch Vision → Vision subagent (spec + acceptance) → `done` + envelope.
3. Měřen route-determinismus + kde smyčka drhne.
4. Identifikováno 5 nálezů (F1–F5) + zdokumentováno v `FINDINGS.md`.
5. Napsán tento handoff a aktualizován `STATE.md`.

## Výsledek

- `dogfood/userflow/` — vytvořen (gitignored, python-fastapi+auth/jwt)
- `dogfood/userflow/specs/create-user.md` — vytvořen Vision subagent (49ř)
- `dogfood/userflow/acceptance/create-user.md` — vytvořen (8 AC)
- `handoffs/2026-06-11-wave-pipeline/FINDINGS.md` — vytvořen (5 nálezů, klasifikovaných (a)/(b))
- `handoffs/2026-06-11-wave-pipeline/HANDOFF.md` — tento soubor
- `STATE.md §Aktuální fokus` — přepsán
- `STATE.md §Open Items` — doplněn o F1–F5 + substrát
- Per-issue flow end-to-end — FAIL (F4 blocker)
- Vision dispatch — OK (profil B funguje čistě)
- Envelope type-validace (C8/C9), ledger, start/active/done mutace — OK

## Decided (rozhodnutí, která následný agent NEOPAKUJE)

- **Diagnóza je (a), ne (b)** — Vision odvedl práci čistě; root cause je
  chybějící/neintegrovaná engine vrstva (`result.sh`, `drive`, `next.sh` integrace),
  ne drift v agentovi. Stejný tvar jako resolve-vs-apply u foundingu.
- **Pořadí oprav:** F4 → F2 → F5 → F3 → F1. F4 je blocker s malým fixem;
  bez něj nelze ověřit ani ostatní. F1 je kosmetický, jde poslední.
- **Re-run dogfoodu** až po F4 (minimálně) — dříve by odhalil jen tutéž zeď,
  ne nové (b) problémy.
- **`selftest.sh` má slepé místo** — po `done` nikdy nevolá `drive`. Je třeba
  přidat scénář `done → drive` (viz F4 fix direction v FINDINGS.md).

## Slabé místo (POVINNÉ)

F2 fix direction (ingestovat deklarované flag-outputy z Vision envelope do
`current-run.md`) předpokládá, že envelope schéma se ustálí současně s F3
(deterministický handoff→envelope most). Pokud F2 a F3 půjdou odděleně,
je risk, že flag-ingest se zapíše pro mezistav envelopy, který F3 pak
přepíše — dvě místa mutují stejnou věc. Doporučení: F3 nejdřív schémově
zafixovat (i jako prázdný stub), pak F2 na něj navázat.

## Normativní mezera (volitelné)

- **Co chybí**: pravidlo pro `kind: fork` — co je directiva, jak se liší od
  `DISPATCH-ALL`, kdy použít.
- **Kde chybí**: `flow.md §Deterministický dispatch` + `pipeline/delivery.yaml`
  popis hran.
- **Kdo dodá**: orchestrátor při pipeline-loop-fix (F5 oprava).

## === GATE OUTPUT ===
```
agent: orchestrator
phase: gate
diagnostika-complete: OK — 5 nálezů zdokumentováno, klasifikováno, seřazeno dle závažnosti
write-scope: RESPECTED — STATE.md + handoffs/** pouze
returns-to: next-session (pipeline-loop-fix)
weak-spot: F2/F3 pořadí závislosti — viz §Slabé místo
selftest-slepota: F4 odhalen; selftest.sh potřebuje done→drive scénář
```
==================

---

## ADDENDUM — pipeline-loop-fix HOTOVO (tatáž session)

Diagnóza výše už **zacelena ve stejné session**. Per-issue flow **jede deterministicky end-to-end**
(`run.sh drive`). Detaily a důkaz: **FINDINGS.md §Fixes applied**.

- **Fixy:** F4 (loop-closure), F2 (flag APPLY vrstva), F6+F7+F8 (graf edge-conditions), F9 (fan-out
  barrier + join pass-through), F1 (doc). F5 (fork) pro backend vyřešen F2 (skip).
- **Regression guard:** `selftest.sh` nově honí celou drive smyčku (fresh → human-gate) — přesně to,
  co maskovalo F4. **selftest 11/11**, check OK.
- **§Slabé místo (výše) vyřešeno:** F2 a F3 NEšly odděleně — F2 jsem napojil přes samostatné pole
  `flags:` v envelope/current-run (ne přes `outputs`), takže F3 (handoff→envelope most) zůstává
  nezávislý a budoucí. Žádné dvojí mutace.
- **§Normativní mezera (fork):** `flow.md` pravidlo pro `kind: fork` **stále chybí** — backend cestu
  obchází F2 (skip), ale pravá paralelní fork-spawn pro UI featury není. Patří do NEXT.

**NEXT (přepisuje původní):** **flow-finish** — human-gate continuation, T3-post release path,
UI-feature dogfood (fork/edna), re-run profil B. Viz STATE.md §Aktuální fokus.
