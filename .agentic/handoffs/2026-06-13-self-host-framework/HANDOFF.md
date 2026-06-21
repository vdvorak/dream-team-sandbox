---
wave: 2026-06-13-self-host-framework
from: implementace (orchestrátor, autonomně dle user „postupuj bez zastavování")
to: review (Vitek)
type: wave-close
returns_to: null
timestamp: 2026-06-13T05:00:00+02:00
---

# Self-host: framework → standardní projekt

User: *„pojďme převést framework na standardní projekt, protože jsem chtěl jít cestou že si
nejdřív vyladím flow a pak z toho udělám reálnou aplikaci na tvorbu agentických flow."*

Cíl: dát frameworku **PRODUCT vrstvu**, aby byl projektem stejného tvaru jako každý jiný
(self-hosting). TOOL vrstva (constitution/flow/agents/pipeline/scripts/templates) zůstává na
rootu — repo JE zdroj `.agentic/`. Drženy frameworkové konvence (kanonická šablona +
constitution + I1–I8), **ne** Trabajario (to bylo jen pro pochopení vtodo principu).

## Vytvořeno (PRODUCT vrstva)

| soubor | obsah |
|---|---|
| `PROJECT-CONSTITUTION.md` | §Vize a mise (engine→platforma north-star) + Hodnoty + Cílovka + JE/NENÍ + NFR + security (token-gated) + topologie (python+solidjs) + §Doménové hard rules (I1–I8 + zamčená rozhodnutí) |
| `project-config.md` | stack python+solidjs (web target), `active_roles` (role-keyed; mobile/desktop/perf off), load-bearing invarianty, cesty |
| `current-run.md` | idle engine stav (ze šablony) |
| `backlog/app-platform.md` | node-editor platforma (samostatný budoucí projekt) — north-star |
| `backlog/watson-self-host-mode.md` | flow-improvement: Watson neumí onboardovat sám framework (dogfood gap) |
| `backlog/human-interaction-registry.md` | P5 z VISION — typované interakce pro app |

## Rozhodnutí v této vlně

- **Stack platformy: Python (FastAPI) + SolidJS**, web target, Docker Compose. Engine sám zůstává
  Python3 + tenké sh, file-based.
- **Konverzi udělal orchestrátor, ne flow** — Watson neumí self-reference („kde je `.agentic/`? to jsem já"),
  flow na frameworku zatím neběží (chyběla product vrstva = chicken/egg). Gap zapsán jako backlog issue.
  Reálný self-hosting test přijde POTOM: reálná issue → `run.sh drive` na frameworku.
- **TOOL vs PRODUCT fyzické oddělení** (přesun TOOL pod `.agentic/` i ve frameworku) = odloženo (velký disruptivní krok).

## Zachování vize — coverage VISION.md (NIC se neztratilo)

`VISION.md` **netknuté** (user: „po tvém OK sáhnu na VISION"). Mapování → kam se obsah přenesl:

| VISION.md | zachyceno v |
|---|---|
| §1 Meta-cíl + §4 Most (app north-star) | `PROJECT-CONSTITUTION §Vize a mise` |
| §2 Invarianty I1–I8 | `PROJECT-CONSTITUTION §Doménové hard rules` + `project-config load_bearing` |
| §6 Zamčená rozhodnutí | `PROJECT-CONSTITUTION §Doménové hard rules` |
| §3 Subsystémy / §5 Roadmap (P1–P7, většina hotová) | `backlog/` (app, P5) + `STATE` |
| §7 Otevřené otázky | `STATE §Open Items` |

## PENDING (čeká na tebe)

1. **Review `PROJECT-CONSTITUTION §Vize a mise`** — sedí ti formulace vize z tvých zápisů?
2. **Fold VISION.md** — až potvrdíš, že PROJECT-CONSTITUTION vizi věrně zachytil, VISION.md
   buď smažu (git ji drží) nebo nechám jako detailní north-star + cross-link. Tvoje volba.
3. CLAUDE.md (bootstrap) pro framework-jako-projekt — záměrně vynecháno (tool-specific); doplnit dle potřeby.
