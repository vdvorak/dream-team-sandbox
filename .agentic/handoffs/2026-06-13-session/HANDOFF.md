---
wave: 2026-06-13-session
from: orchestrator (dlouhá session)
to: next-session
type: session-handoff
returns_to: null
timestamp: 2026-06-13T07:00:00+02:00
---

# Session handoff — 2026-06-13

Dlouhá session: dokončení OO refactoru → code-quality → docs konsolidace → **self-hosting**
(framework = projekt sám sobě) → **první reálný self-hosted flow běh** → dogfood fixy.
Každá vlna má vlastní handoff (níže); tohle je sváže + řekne, kde navázat.

## Co se v session udělalo (chronologicky, vlna = commit blok)

1. **OO refactor Fáze 3a/3b/4** (`78591fc`→`e697d06`) — dokončen doménový model: result.py outcome
   handlery, run.py `drive_category` partition, check.py C1–C15 nad Graph/Vocabulary/Predicate.
   CLOSE: `handoffs/2026-06-12-engine-oo-refactor/CLOSE.md`.
2. **pytest unit-vrstva** (`786ddb6`) — 75 testů nad predicate/graph/runstate; do CI.
3. **Code-quality vlna** (`0549113`→`532eecf`) — typy napříč `core/` (mypy clean, 16 souborů),
   dekompozice dlouhých `main()`, de-densifikace; CI: +mypy. Rozhodnutí: bash shimy zůstávají,
   komentáře česky (interní nástroj). CLOSE: `handoffs/2026-06-13-code-quality/CLOSE.md`.
4. **Docs konsolidace** (`a460b59`) — README = jeden front door + mapa dokumentů; WORKFLOW vstřebán
   + smazán; REVIEW smazán; USAGE = runbook; VISION netknuté.
5. **Self-host: framework → standardní projekt** (`57d8bf3`) — PRODUCT vrstva: `PROJECT-CONSTITUTION.md`
   (vize z VISION + I1–I8), `project-config.md` (python+solidjs), `current-run.md`, `backlog/`.
   HANDOFF: `handoffs/2026-06-13-self-host-framework/HANDOFF.md`.
6. **P5 Human-interaction registry — první self-hosted flow běh** (`845b7b2`) — issue protažena
   CELÝM flow přes `run.sh drive` (intake→…→done). Produkt: `interactions.yaml` v2 typovaný registr.
   Archiv: `handoffs/2026-06-13-p5-human-interaction/PROGRESS.md`.
7. **Flow-gaps fixy #1–#5** (`7c63f82`, `37a2a39`) — 5 dogfood nálezů z P5 vyřešeno (4 fixy + 1
   vyjasnění hranice). `backlog/flow-self-host-gaps.md`.

## Aktuální stav

- **Framework je self-hostovaný projekt** (PRODUCT + TOOL vrstva na rootu; repo JE zdroj `.agentic/`).
- **Engine kvalita:** mypy clean (16), dekompozice, 2 testovací vrstvy. Brána: **selftest 57/57 ·
  check C1–C15 · pytest 83 · mypy clean · createdat · parity**.
- **Self-hosting ověřen:** flow řídil reálnou dodávku (P5) sám; dogfood smyčka (běh→nálezy→fixy)
  proběhla a P5-like běh by teď byl čistý bez workaroundů.
- **Vize zachycena:** `PROJECT-CONSTITUTION §Vize a mise` (engine teď → node-editor platforma potom;
  AI-callable issues/todos vzor `vtodo`/Trabajario; vstup do flow přes typed interface, ne terminál).

## PENDING — kde navázat

1. **Review `PROJECT-CONSTITUTION §Vize a mise` + osud `VISION.md`** ← jediné explicitně odložené.
   VISION.md je NETKNUTÉ (čeká na user OK). Coverage VISION→PROJECT-CONSTITUTION 10/10. Rozhodnout:
   fold (smazat, git drží) vs nechat jako detailní north-star + cross-link.
2. **Backlog north-star:** `backlog/app-platform.md` — node-editor app (samostatný budoucí projekt
   konzumující engine). Předpoklad: `backlog/human-interaction-registry.md` HOTOVO (P5).
3. **Backlog open:** `backlog/watson-self-host-mode.md` (Watson neumí onboardovat framework — self-reference).
4. **Diskutováno, neuděláno:** Watson init = skript (deterministická config) + LLM jen vize;
   Monk přerámovat na vizní LLM (init + drift-reflexe). Není rozhodnuté.

## Resume pointer

`STATE.md §Aktuální fokus` (živý stav) → per-vlna handoffy výše. Engine: `run.sh status` (idle).
Brána: `bash scripts/pipeline/selftest.sh` + `check.sh` + `pytest scripts/pipeline/tests` + mypy.

## Slabé místo

`.claude/settings.json` (z `/fewer-permission-prompts`) je **untracked** — nezacommitnuto vědomě
(config se commituje až na rozhodnutí usera; `settings.local.json` se obvykle gitignoruje).
Self-hosting na **meta-práci** (agenti/docs/graf) graf nemodeluje — to je vědomá hranice (#3),
ne gap; kdyby přišla potřeba flow i pro agent-authoring, je to samostatný design.
