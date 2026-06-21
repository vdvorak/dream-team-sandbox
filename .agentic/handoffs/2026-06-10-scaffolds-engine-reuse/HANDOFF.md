---
wave: 2026-06-10-scaffolds-engine-reuse
from: orchestrator (claude session)
to: next-session
type: milestone-handoff
returns_to: null
---

# Handoff: scaffoldy kompletní + execution loop + UnagyDev patterny + reuse governance

Navazuje na `handoffs/2026-06-10-pipeline-engine/HANDOFF.md` (engine P1–P6). Verze: **v0.32.0**.

## Stav (kde to je)

Engine byl hotový, ale tři věci chyběly: (1) scaffoldy nepokrývaly všechny osy, (2) runner
byl poradní, ne řídící, (3) framework rules byly tenčí než realita v UnagyDev. Tahle wave to
zacelila + přidala **anti-entropy governance** (reuse + mechanický back-align).

Vstupní body pochopení: `VISION.md` → `pipeline-architecture.md` → `flow.md §Deterministický
dispatch` → `constitution.md §Reuse policy`.

## Výsledek (co bylo postaveno)

- **Scaffoldy — všech 8 os `ready`** (`templates/scaffolds/manifest.yaml`):
  - `flutter/` (mobile) — Riverpod + go_router + dio + gen-l10n, plain modely, `ApiError {code,details}`
  - `electron/` (desktop) — electron-vite + electron-builder, SolidJS renderer, security baseline
  - docker dev-run reálně: `python-fastapi`, `solidjs` `Dockerfile.dev` + `docker-compose.dev.yml`
  - `recommended-libs.yaml` flutter+electron sekce
- **Execution loop uzavřen** — `scripts/pipeline/run.sh drive` = řidič: ze stavu vydá JEDNU
  direktivu (DISPATCH / DISPATCH-ALL / DECIDE / HUMAN-GATE / DONE), deterministicky posune
  `active_node`; free-text podmínka → explicitní DECIDE (ne tiché LLM rozhodnutí).
  `next.sh --emit json`. Zadrátováno do `flow.md §Deterministický dispatch` (drive = krok 1).
- **UnagyDev = pattern-donor** → `rules/` + scaffoldy:
  - `rules/backend.md`: `*View/*Data/*ExtData`, write-flow validate-only+commit, kolekce
    `ApiListOf/PageOf/SliceOf`, typy operací, one-table=one-repo
  - `rules/frontend.md`: form-model, write-flow klient, domain-konstanty fail-closed
  - bindingy: solidjs `createFormStore`+`TextField`, flutter `form_model.dart`; **python-fastapi
    dorovnán na java-quarkus** (validate-flow + model role + `ValidationResult` + `ApiListOf`)
  - web baseline: i18n wiring, auth plumbing (`tokenStore` + client middleware), `BackendStatusBanner`
- **Reuse governance (anti-entropy)** — `constitution §Reuse §Operační mechanismus`:
  Extraction Candidates registr, 2.výskyt = povinná akce, explicitní **back-fill**, katalog=autorita;
  `templates/extraction-candidates.md`. Mechanický back-align: `scripts/catalog-conformance.sh`
  (deterministický scan) + per-stack `catalog-conformance.yaml` napříč **všemi 5 stacky** +
  `catalog.md`; wired do **Vitek gate** vedle `drift-scan`.

## Jak navázat (příští session / „hej Watsone")

1. `STATE.md §Aktuální fokus` = živý přehled (wave `2026-06-10-scaffolds+engine-loop`).
2. Smyčka naostro: `run.sh start <issue>` → `run.sh drive` (opakuj) → uzel → `run.sh done <env>`.
3. Reuse hlídá Vitek: `bash scripts/catalog-conformance.sh` (0 = čisto; BLOCKER = back-align).
4. Před scaffold delegací: `run.sh scaffold --frontend flutter` apod.; lib volba: `lib.sh --stack X`.

## Decided (rozhodnutí — neopakovat)

- **Reuse enforcement = B (deterministické blocking conformance)**, ne advisory (A, stojí na
  disciplíně) ani candidate-similarity (C, fuzzy → false-positives podkopávají stabilitu).
- **Catalog-conformance signatury: JEN vysoce přesné** (false-positive = ztráta důvěry).
  Lekce: python `str(exc)` trefil docstring, java `Response.status` self → prune/allow.
- **Flutter/electron modely = plain (bez codegenu)** — turnkey build bez `build_runner`.
- **Web app není monolit scaffold** — skládá se per-osa (solidjs + backend + deploy).
- **Frontend (Kobalte/tokeny/CSS Modules), validate-only+commit, *Data/*ExtData** = z UnagyDev
  (nejpromyšlenější projekt, pattern-donor).

## Zbývá (next)

- **#6 reálný feature-dogfood** — protáhnout opravdovou feature dogfood projektu celým grafem
  přes `run.sh`. Loop je ověřený mechanicky (selftest 9/9 + drive walk), ale nikdy nejel na
  reálné feature. JEDINÝ poctivý test architektury. Nefejkovat — čeká na reálný ticket.
- **C — candidate auto-detekce** (deterministická exact-hash, advisory) — až po vstupu na hloubku.
- **Per-stack katalogy rostou** — signatur je zatím málo (jen vysoce jisté); přidávat při extrakci.

## Slabé místo (POVINNÉ)

- **Frontend scaffoldy nejsou build-ověřené v tomto prostředí** — chybí flutter SDK / npm
  node_modules. Flutter = dart-format clean; solidjs/electron = struktura + JSON/alias OK, ale
  `flutter test` / `vitest` / `tsc` NEPROBĚHLY. Python pytest 4/4 ✓ (jediný reálně buildnutý).
  Riziko: subtilní typové/runtime chyby v unverifikovaném TS/Dart. Zapsáno i v scaffold README.
- **Adopce drivu je dokumentační** — `flow.md` říká „použij drive", reálné habituální používání
  orchestrátorem se teprve usadí (sleduj, jestli se LLM drží `run.sh` místo prózy).
- **Catalog-conformance pokrytí je řídké** — chytne jen deklarované signatury; většina reuse
  driftu zatím proklouzne, dokud katalogy nenarostou.
