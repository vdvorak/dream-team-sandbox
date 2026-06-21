---
cache_key: agents-overview-v1.2
type: overview
last_updated: 2026-06-16
maintained_by: eywa-meta
---

# Agents Overview

Lidsky čitelný přehled všech agentů a workflow.
Normativní zdroj je `agents/INDEX.md` + `flow.md` — tento soubor je odvozenina.
Udržuje **Eywa** při každé změně cast (přidání / odebrání / úprava agenta).
Cast tabulka v `<!-- GENERATED: cast-overview -->` se **negeneruje ručně** — regeneruj
`scripts/gen-cast-tables.py` (projekce `delivery.yaml` + frontmatterů); workflow graf a
schvalovací úrovně jsou autorské.

---

## Cast (20 agentů)

### Standardní flow

> Tabulka níže (`short | jméno | role | fáze | model`) je strojová projekce `delivery.yaml`
> + frontmatterů — needituj ručně, regeneruj `scripts/gen-cast-tables.py`. Role je z frontmatteru,
> fáze (`phase`) a model jsou z grafových uzlů agenta.

<!-- GENERATED: cast-overview — needituj ručně, spusť scripts/gen-cast-tables.py -->
| Agent | Jméno | Role | Fáze | Default model |
|---|---|---|---|---|
| `vision-po` | Vision | Product Owner | T1 | sonnet |
| `sheldon-spec` | Sheldon Cooper | Spec Auditor | T1, T3 | sonnet |
| `tony-cto` | Tony Stark | CTO / Tech strategy | T1 | opus |
| `denisa-ux` | Denisa | UX | T1 | sonnet |
| `ted-architect` | Ted Mosby | Architect | T2 | opus |
| `chandler-db` | Chandler Bing | DB specialist | T2 | sonnet |
| `leonard-ui` | Leonard Hofstadter | UI | T2 | sonnet |
| `bob-backend` | Bob the Builder | Backend Dev | T2 | sonnet |
| `peter-web` | Peter Parker | Web Dev | T2 | sonnet |
| `mob-mobile` | Mob | Mobile Dev | T2 | sonnet |
| `winny-desktop` | Winny | Desktop Dev | T2 | sonnet |
| `vitek-quality` | Vitek | Code Quality Auditor | T2, T3 | sonnet |
| `joey-qa` | Joey Tribbiani | QA | T3 | sonnet |
| `optimus-perf` | Optimus Prime | Performance | T3 | sonnet |
| `heimdall-security` | Heimdall | Security Auditor | T3 | opus |
| `edna-design` | Edna Mode | Design Auditor | T3 | sonnet |
| `alfred-devops` | Alfred Pennyworth | DevOps / Release Engineer | T3-post | sonnet |
<!-- /GENERATED: cast-overview -->

### Meta-agenti (mimo standardní flow)

| Agent | Jméno | Role | Trigger |
|---|---|---|---|
| `eywa-meta` | Eywa | Agent Architect — správa agent systému | `přidej/audit agenta`, write scope konflikty |
| `watson-interviewer` | John Watson | Project Setup Interviewer | nový projekt, `zavolej Watson` |
| `monk-ideation` | Monk | Ideation & Reflection Guide | `Pojďme meditovat` |

---

## Workflow graf

> Diagram používá **persony** (zapamatovatelné). Uzly grafu jsou ve skutečnosti **role**
> (`product`/`architecture`/`backend`/…) — mapování persona ↔ role v `INDEX.md §Cast`,
> strojová podoba v `pipeline/delivery.yaml`. „Vision" = role `product` atd.

```
USER REQUEST
     │
     ▼
ORCHESTRÁTOR (main session)
     │
     ├─ nový feature ──────────────────────────────────────────────┐
     ├─ bugfix s failure signature → vlastník artefaktu            │
     ├─ improvement → Tony / Ted                                   │
     └─ keyword trigger → Watson / Eywa / Monk                     │
                                                                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  T1: IDEA → SPEC                                                 ║
║                                                                  ║
║   Vision (spec, acceptance criteria)                            ║
║        │                                                         ║
║        ▼                                                         ║
║   Tony (tech-feasibility L1) ──PASS──►  Denisa (mockup.html)    ║
║        │ FAIL                               │ jen pokud UI       ║
║        └──── zpět Vision                    │ (visí na Tony PASS)║
║                                             ▼                   ║
║         specs/ + acceptance/ + design/<feature>/mockup.html     ║
╚══════════════════════════════════════════════════════════════════╝
     │
     ▼
╔══════════════════════════════════════════════════════════════════╗
║  T2: SPEC → CODE                                                 ║
║                                                                  ║
║   Ted (API contracts) ◄──── Chandler (DB schema)                ║
║        │                    paralelně pokud DB hraje roli        ║
║        ▼                                                         ║
║   Leonard (shared UI komponenty)                                 ║
║        │                                                         ║
║        ▼                                                         ║
║   Bob (server)  ║  Peter (web)    ← paralelně, write scope       ║
║                 ║  Mob (mobile)     se nepřekrývá                ║
║                 ║  Winny (desktop)  jen pokud aktivní            ║
║                                                                  ║
║   → unit testy zelené → L1 gate (Joey integration test)          ║
╚══════════════════════════════════════════════════════════════════╝
     │
     ▼
╔══════════════════════════════════════════════════════════════════╗
║  T3: CODE → OVĚŘENÍ  (auditoři běží paralelně, všichni RO)       ║
║                                                                  ║
║   Joey (funkční testy)                                           ║
║        │ PASS                                                    ║
║        ▼                                                         ║
║   ┌──────────┬──────────┬────────┬──────────┬──────────┐        ║
║   │ Sheldon  │ Heimdall │  Vitek │  Optimus │  Edna    │        ║
║   │ (spec)   │ (sec)    │ (qual) │  (perf)  │ (UI) *   │        ║
║   └──────────┴──────────┴────────┴──────────┴──────────┘        ║
║        │ všichni PASS                * jen pokud feature má UI  ║
║        ▼                                                         ║
║   L2 user view (screenshot + shrnutí)                            ║
╚══════════════════════════════════════════════════════════════════╝
     │
     ▼
╔══════════════════════════════════════════╗
║  T3-POST: RELEASE & DEPLOY               ║
║                                          ║
║   Alfred                                 ║
║   → staging  (L2 user view)              ║
║   → L3 user souhlas                      ║
║   → production                           ║
║   → monitor                              ║
║       │ fail                             ║
║       └──► rollback → viník             ║
╚══════════════════════════════════════════╝


RETURN PATHS (agent dodá VERDIKT; routing dělá GRAF — agent nejmenuje kolegu):

  Joey FAIL  → Ted (diagnostik)   — zkoušeč naslepo: jen příznak, neurčuje vlastníka
  Ted (diag) → fault: db-schema → Chandler | server-logic → Bob
                    | spec → Vision | contract → opraví sám
  Sheldon    → Vision / Ted                 (spec/contract nekonzistence)
  Heimdall   → Bob / Peter / Mob / Winny   (security finding v kódu)
  Vitek      → Bob / Peter / Mob / Winny   (code quality finding)
  Optimus    → Bob / Peter / Mob / Winny   (perf issue)
  Edna       → Peter / Mob / Winny / Denisa / Leonard  (design / mockup / manuál)
  Alfred     → Bob / Peter / Mob / Winny / Tony / Chandler / Joey

  Agenti = slepé I/O kontrakty: výstup je verdikt (finding / fault: doména),
  routing (který uzel) žije jen v grafu. Viz agents/ARCHITECTURE.md.
```

---

## Schvalovací úrovně

| Úroveň | Kdo | Co | Zdržuje? |
|---|---|---|---|
| **L0 auto** | nikdo | implementační kroky uvnitř scope | ne |
| **L1 AI gate** | druhý agent (Tony, Joey, auditoři) | T1/T2/T3 checkpoint | ne (AI→AI) |
| **L2 info** | user vidí, neblokuje | velký commit, feature done, finální handoff | ne |
| **L3 blokuje** | user musí schválit | destruktivní op, breaking change, BLOCKER | ano |

---

## Activation profily

| Profil | Aktivní agenti (před target-gatingem) | Pro koho |
|---|---|---|
| **solo** (~8) | Vision, Ted, Bob, Peter, Joey, Heimdall, Vitek + Watson | solo dev, jednoduchý projekt |
| **standard** (~13) | solo + Tony, Chandler, Sheldon, Leonard, Alfred | většina reálných projektů |
| **full** (20) | celý cast + Optimus, Denisa, Edna, Eywa, Mob, Winny | komplexní: multi-tenant SaaS, multi-target, design-heavy |

Target-gating: no web → Peter off; no mobile → Mob off; no desktop → Winny off;
no DB → Chandler off; no deploy → Alfred off.
