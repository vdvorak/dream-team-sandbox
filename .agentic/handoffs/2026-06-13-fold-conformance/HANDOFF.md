---
wave: 2026-06-13-fold-conformance
from: orchestrator
to: next-session
type: session-handoff
returns_to: null
timestamp: 2026-06-13T12:00:00+02:00
---

# Session handoff — 2026-06-13 (fold + konformita + structure-validator scoping)

Krátká návazná session na `2026-06-13-session`. Uzavřela **jediný explicitně odložený** bod
(VISION fold) + `.claude/` rozhodnutí, ověřila self-host konformitu naživo a **rozběhla**
(ne dokončila) structure-validator. Resume bod = jeho design níže.

## Co se udělalo (chronologicky)

1. **VISION fold** (`290019c`) — `VISION.md` SLOUČEN do `PROJECT-CONSTITUTION` (git drží historii).
   Rozhodnutí FOLD, ne keep: coverage VISION→PROJECT-CONSTITUTION 10/10, zbytek VISION historický
   (roadmap P1–P7 hotová, status-table zastaralá); dvě vize-docs s 10/10 překryvem = drift
   anti-pattern, který engine sám potírá. Salvage: tabulka „most engine→app" → `backlog/app-platform.md`.
   4 navigační odkazy přesměrovány (README ×2, agents/ARCHITECTURE.md, scripts/pipeline/core/README.md).
   README PRODUCT-tabulka narovnána (dřív neuváděla PROJECT-CONSTITUTION vůbec; přidán + řádek backlog/).
   Provenance „z VISION §X" komentáře ponechány jako historická linie.
2. **`.claude/` rozhodnutí** (`c6e6905`) — `settings.json` (2 read-only allow pravidla pro bránu:
   check.sh + pytest) = sdílený config → **verzován**. `settings.local.json` (osobní, 8 KB) **ignorován
   v repo `.gitignore`** — dřív ho držel jen globální `~/.config/git/ignore` (`**/.claude/settings.local.json`)
   = nepřenosné mezi klony.
3. **Self-host konformita ověřena NAŽIVO** (ne ze zápisu) — odpověď na user otázku „je framework úplně
   stejný jako nový projekt + splňuje pravidla?". Celá brána zelená: check C1–C15 OK · selftest 57/57 ·
   pytest 83 · **mypy clean 16** (POZOR: jen s `--config-file scripts/pipeline/mypy.ini` — ten má
   `ignore_missing_imports` pro `yaml`; bez configu mypy falešně hlásí „types-PyYAML not installed").
   `run.sh status` = idle.

## Závěr konformity (důležité pro mentální model)

Framework **JE** projekt-tvar (PRODUCT vrstva na rootu, P5 to dokázal reálným během), ale **NENÍ
layout-identický** s generovaným projektem — **vědomě**:
- Generovaný projekt (`create-project.sh`): TOOL vrstva v `.agentic/`, PRODUCT na rootu.
- Framework: TOOL vrstva **na rootu** (repo JE zdroj `.agentic/`, nemůže klonovat sám do sebe).
  `project-config.md` má `project_type: self-host` = třetí, vlastní typ. Zdokumentováno.

**Dvě reálné mezery** (ne bug, ale „není hotové"):
- (A) **Watson neumí self-host vyrobit** — převod na projekt byl ruční. → `backlog/watson-self-host-mode.md`.
- (B) **Není structure-validator** — brána ověřuje GRAF a ENGINE, ne „má projekt správný tvar".
  Konformita tvaru = dnes konvence + úspěšný P5 běh, ne kontrolní skript. → user řekl „zkus" → vybrán (B).

## RESUME BOD — structure-validator (rozběhnuto, NULA kódu napsáno)

User delegoval výběr (A vs B), zvoleno **(B) structure-validator** (deterministické, sedí na
„scripts-not-LLM enforcement", přímo zavírá konvenční mezeru z otázky). Hotový jen **průzkum konvencí**:
- shim vzor: `check.sh` = 3řádkový `exec python3 core/check.py "$@"`; logika v `core/`.
- `core/check.py` styl: funkce vrací `list[str]` nálezů; `report()` tiskne + `sys.exit(0|1)`; `2` = chyba.
- reuse z `common.py`: `require_graph`, `sibling`, `load_yaml`, `yaml`; doménový `Graph.load` (node-ids).
- **Není** `templates/project-config.md` → náš `project-config.md` JE kanonický vzor. Sekce:
  `## Projekt · ## Targets · ## Project flags · ## Active roles · ## Fyzické cesty · ## Klíčové invarianty · ## Git`.

### Navržený design (k implementaci)
`scripts/pipeline/structure-check.py` (+ tenký `structure-check.sh` shim). Validuje PRODUCT-layer tvar:
1. **Required sekce** v `project-config.md` (Projekt / Targets / Project flags / Active roles / Fyzické cesty).
2. **Fyzické cesty** — parse YAML blok `## Fyzické cesty`; required subset MUSÍ existovat na disku
   (`project_constitution`, `project_state`, `backlog`, `handoffs`, `graph`, `engine`); lazy cesty
   (`specs/`, `stack/` — v configu komentář „zatím neexistuje") = allowed-absent.
3. **project_type dispatch**: `self-host` → assert TOOL na rootu (`constitution.md`, `agents/`,
   `pipeline/`, `scripts/pipeline/core/`); normal → assert `.agentic/` existuje s TOOL vrstvou.
4. **active_roles** klíče ∈ valid role (křížově proti node-id v `pipeline/delivery.yaml` přes `Graph`).
5. Styl jako check.py: nálezy → `report()` → exit 0/1/2.

### Wiring (po implementaci)
- **Test-driven**: přidat scénáře do `scripts/pipeline/selftest.sh` (pozitivní: framework projde;
  negativní: chybějící required cesta / neznámá role / chybějící sekce → nález).
- Brána: vedle check.sh. CI: `.github/workflows/pipeline-guardrails.yml`.
- Distribuce: `agentic-sync.sh` allowlist (`pipeline/`/`scripts/pipeline/`) + `create-project` klon.
- Pozn.: rozhodnout, zda required/lazy cesty hard-codovat v skriptu, nebo zavést
  `pipeline/project-structure.yaml` (schema required vs optional per project_type) — čistší, ale větší.

## Stav / brána

Working tree čistý, 2 commity této session na `main` (`290019c`, `c6e6905`); repo 30 ahead of origin.
VERSION 0.37.0 (nebumpnuto — housekeeping). Brána zelená (viz výše). `run.sh status` idle.

## Ostatní open items (nezměněno)
`backlog/app-platform.md` (north-star app), `backlog/watson-self-host-mode.md` (mezera A), Watson init =
skript + LLM vize / Monk reframe (nerozhodnuto). STATE.md §Open Items je autorita.
