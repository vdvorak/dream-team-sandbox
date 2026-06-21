---
wave: 2026-06-12-engine-oo-refactor
from: implementace (session 2026-06-12)
to: archiv (HOTOVO)
type: close
returns_to: null
timestamp: 2026-06-12T17:30:00+02:00
---

# CLOSE: OO refactor enginu — všechny 4 fáze HOTOVÉ

Procedurální if/regex/`eval()` slepenec v `scripts/pipeline/core/` nahrazen doménovým
modelem. Engine iteruje nad objekty (Node/Edge/Graph/Predicate/RunState), ne nad dicty.
**Čistý refactor, nula změny chování** — brána zelená po KAŽDÉ fázi.

## Fáze (commity)

| fáze | commit | obsah |
|---|---|---|
| 1 | `611b0a5` | Predicate AST (Verdict + atomy + And/Or/Not + parser). `eval()` z enginu PRYČ. `frontier.Ctx.atom/classify/flag_live` smazány. Parity 19208/0. |
| 2 | `c388605` | `graph.py` (Node+podtřídy/Edge/Graph) + `runstate.py` (RunState). `Frontier` třída. result.py na Graph/Vocabulary/RunState. |
| 3a | `78591fc` | result.py outcome if/elif → polymorfní handlery: AdvisoryFail · ReturnFail · BareFail · Rejected · Completion. |
| 3b | `960f012` | run.py drive() string-žebřík → `node.drive_category` partition (JOIN/TERMINAL/BLOCKING_GATE/FREE_GATE/WORKER/ROUTER); těla větví na RunState. |
| 4 | *(tato session)* | check.py C1–C15 nad Graph/Vocabulary/`Predicate.problems()` (poslední duplicitní when-parser `check_when` pryč); status.py node-id validace přes Graph.load; docs (core/README.md, STATE.md). |

## Výsledek (cíle handoffu/plánu splněny)

- **`eval()` v enginu = 0** (jen 1 komentář v predicate.py). Cíl handoffu splněn.
- **`when` evaluace na JEDNOM místě** (`Predicate.evaluate`) místo 3× duplikace; C14 slovníková
  validace padá zadarmo z parsovaného AST (`Predicate.problems`).
- **Skládání = puzzle:** Frontier/result/drive/check iterují nad doménovými objekty.
  App-ready (node-editor konzumuje Node/Edge/Predicate, ne YAML stringy) — VISION §Most.
- **Doménový model je čistě unit-testovatelný** (predicate/graph/runstate bez I/O) — pytest follow-up.

## Brána (zelená po každé fázi i finálně)

```
selftest.sh                                   57/57  „VŠE PROŠLO"
check.sh                                       C1–C15 RESULT: OK
accept-createdat.py                            exit 0
parity-predicate.py                            PARITY OK  (AST == stará atom/classify/flag_live)
```

Navíc Fáze 4: výstup check.py **byte-identický** s baseline na reálném i rozbitém grafu
(diff = prázdný), takže C-nálezy zůstaly na znak shodné.

## Follow-up

- pytest unit-vrstva nad doménovým modelem (predicate/graph/runstate) — **HOTOVO** (`786ddb6`,
  75 testů v `scripts/pipeline/tests/`, DEV-only, zapojeno do CI).
- ledger.py / scaffold.py / compose.py / feature.py / lib.py: mimo rozsah (nejsou if-slepenec,
  predikáty nevyhodnocují).

Reference: plán `~/.claude/plans/ancient-singing-pnueli.md`; zadání `HANDOFF.md`; mezistav `PROGRESS.md`.
