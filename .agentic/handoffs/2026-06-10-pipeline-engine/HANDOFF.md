---
wave: 2026-06-10-pipeline-engine
from: orchestrator (claude session)
to: next-session
type: milestone-handoff
returns_to: null
---

# Handoff: pipeline engine (VISION + P1–P6 + runner/adopce/CI)

## Stav (kde to je)

Dream-team dostal **deterministický spec-driven engine** převádějící flow z prózy
na strojový stavový graf. Vše v souborech, tool-agnostic, Python3 + tenké POSIX sh,
app-ready. Hotovo a otestováno end-to-end (`scripts/pipeline/selftest.sh` = 9/9), CI-guarded.

Verze: VERSION na v0.30.0. Vstupní bod pro pochopení směru: **`VISION.md`** (North-Star),
pak `pipeline-architecture.md` (substrát), `pipeline/README.md` (detail enginu).

## Výsledek (co bylo postaveno)

- **VISION.md** — North-Star: meta-cíl determinismus+konzistence, invarianty I1–I8,
  subsystémy, most souborový engine→aplikace, roadmap.
- **Graf** `pipeline/delivery.yaml` (dnešní flow 1:1) + `pipeline/README.md`.
- **P1 typované I/O** — `pipeline/artifacts.yaml` (typy artefaktů; abstract `code`).
- **P2 node-result /done** — `templates/node-result.md` + `scripts/pipeline/result.sh`
  → `runs/<run>/ledger.yaml` (append) + posun `current-run.md`.
- **P3 cost+čas** — `scripts/pipeline/ledger.sh` → `runs/<run>/summary.md`; volitelný
  `pipeline/model-prices.yaml`.
- **P4 scaffoldy v2 (foundation)** — `templates/scaffolds/manifest.yaml` (osy
  platform×backend×frontend×deploy×agent), `templates/scaffolds/README.md`,
  `templates/agent-template.md`, `scripts/pipeline/scaffold.sh` (scaffold-passing).
- **P5 human-interakce** — `pipeline/interactions.yaml` (typované body) + check.sh C10.
- **P6 Watson init** — `agents/watson-interviewer.md` v1.8 „Chci založit projekt";
  `setup-claude-code.sh` seedne idle `current-run.md`.
- **Runner** `scripts/pipeline/run.sh` (jednotný executor) + `selftest.sh`.
- **Adopce** — `flow.md §Deterministický dispatch`: routing/stav scriptem, LLM jen úsudek.
- **Guardrail** `scripts/pipeline/check.sh` C1–C10 + `.github/workflows/pipeline-guardrails.yml`.
- **Standardizace knihoven** (v0.30.0) — `templates/stacks/recommended-libs.yaml` (vetted
  libs per stack indexované schopností; core/dev/capabilities + „co to je") +
  `scripts/pipeline/lib.sh` (resolver: „přidej X" → doporučená lib pro stack). Scaffold
  core narovnán dle reality 5 projektů (solidjs +lucide/i18next/msw; python +python-multipart).

## Jak navázat (příští session / „hej Watsone")

1. `STATE.md §Open Items` = živý seznam (hotové i zbývající).
2. Vyzkoušej smyčku: `bash scripts/pipeline/selftest.sh` (musí projít 9/9).
3. Stav běhu kdykoliv: `bash scripts/pipeline/run.sh status`.
4. Determinismus: routing/stav počítej `run.sh` (status/next/done/summary), ne z hlavy.
5. Před volbou knihovny: `bash scripts/pipeline/lib.sh --stack X [--capability Y]`.

## Decided (rozhodnutí — neopakovat)

- Scripty = **Python3 + tenké POSIX sh**.
- **Determinismus + konzistence = akceptační kritérium**; žádný vibe coding.
- **Strict spec-driven** vynuceno strukturálně (check.sh C7: Vision dominuje producenty).
- **SCRUM odložen** (pozdější vrstva nad enginem).
- **Web = SolidJS CSR** (primární, ready). **Mobile = Flutter** (iOS+Android, planned).
  Desktop = electron (planned). Backend ready: python-fastapi, java-quarkus.
- `CLAUDE.md` je generovaný tenký adaptér (`setup-claude-code.sh`), needituje se ručně.
- **Knihovny standardizované 3 vrstvami** (core / vetted-optional dle schopnosti / domain);
  registr `recommended-libs.yaml`, AI se ptá `lib.sh` PŘED volbou (constitution §Standardy).
  DB libs v `_db/` vrstvě (ne v base — python+pg je volba). SQL v jazyce (jOOQ/SQLAlchemy,
  žádné raw stringy — rules/backend). Styling = komponentová knihovna (Kobalte) + CSS/SASS
  Modules; **Tailwind zakázán**.
- **vtodo** = `~/dev/AI/Trabajario` (objeveno: `backend/pyproject name="vtodo"`) — vzor
  budoucí app vrstvy (token-gated, /done). Stack **React+Tailwind = MIMO** SolidJS standard.
  (Cesta `/home/vitek/development/AI/vtodo` z původní zmínky v tomto prostředí neexistuje.)

## Zbývá (next — velké, samostatné)

- **Reálné scaffold kostry**: flutter (mobile) + electron (desktop) `status: planned`;
  Docker dev-run přímo ve scaffoldech (Dockerfile.dev/compose). Build/test ověřit.
- **Node-editor aplikace**: vtodo-style board, token-gated přístup, live view, `/done`
  přes API. Engine je hotový základ (čte/píše tytéž soubory — `run.sh` = backend logika).

## Slabé místo

- Adopce je **dokumentační** (flow.md říká „použij runner") — reálné habituální
  používání orchestrátorem se v praxi teprve usadí; sleduj, jestli se LLM drží `run.sh`
  místo prózy.
- `status: planned` scaffoldy (flutter/electron) nejsou build-ověřené (kostry neexistují).
- `next.sh` predikáty u free-text podmínek vrací `judgment` (záměrně — orchestrátor
  rozhoduje); plně automatický routing jen u strukturovaných podmínek.
