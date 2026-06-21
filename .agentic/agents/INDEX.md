---
cache_key: agents-index-v1.3
type: index
---

# Agents Index

Načti tento soubor při init. Plnou definici konkrétního agenta načti až
při jeho volání (`agents/<short>.md`).

## Cast (20 agentů)

### Standardní flow (T1 / T2 / T3 / T3-post / gate)

**Uzel grafu = ROLE** (`delivery.yaml`), `agent:` (short) = **cast binding** (persona, která roli plní).
Hrany drátují role, ne persony → výměna agenta na roli je změna bindingu, ne grafu. Persony si drží
charakter (Marvel/Friends/…), ale flow je o rolích.

<!-- GENERATED: cast-index — needituj ručně, spusť scripts/gen-cast-tables.py -->
| Short (persona) | Jméno | Uzel grafu (role) | Funkce | Universe |
|---|---|---|---|---|
| `vision-po` | Vision | `product` | Product Owner | marvel |
| `sheldon-spec` | Sheldon Cooper | `spec-gate` (+ `spec-audit`) | Spec Auditor | tbbt |
| `tony-cto` | Tony Stark | `feasibility` | CTO / Tech strategy | marvel |
| `denisa-ux` | Denisa | `ux-design` | UX | osobní |
| `ted-architect` | Ted Mosby | `architecture` | Architect | himym |
| `chandler-db` | Chandler Bing | `db-schema` | DB specialist | friends |
| `leonard-ui` | Leonard Hofstadter | `ui-system` | UI | tbbt |
| `bob-backend` | Bob the Builder | `backend` | Backend Dev | bob-the-builder |
| `peter-web` | Peter Parker | `web` | Web Dev | marvel |
| `mob-mobile` | Mob | `mobile` | Mobile Dev | nickname |
| `winny-desktop` | Winny | `desktop` | Desktop Dev | nickname |
| `vitek-quality` | Vitek | `code-lint` (+ `code-quality`) | Code Quality Auditor | osobní |
| `joey-qa` | Joey Tribbiani | `qa` | QA | friends |
| `optimus-perf` | Optimus Prime | `performance` | Performance | transformers |
| `heimdall-security` | Heimdall | `security` | Security Auditor | marvel |
| `edna-design` | Edna Mode | `design-audit` | Design Auditor | incredibles |
| `alfred-devops` | Alfred Pennyworth | `devops` (+ `production`/`monitor`) | DevOps / Release Engineer | dc |
<!-- /GENERATED: cast-index -->

### Meta-agenti (mimo standardní flow)

| Short | Jméno | Role | Trigger | Universe |
|---|---|---|---|---|
| `eywa-meta` | Eywa | Meta-agent / Agent Architect | user request: add/modify/audit agent | Avatar |
| `watson-interviewer` | John Watson | Project Setup Interviewer | nový projekt / přechod na agentic / chybí project-config | Sherlock Holmes |
| `monk-ideation` | Monk | Project Ideation & Reflection Guide | user: „Pojďme meditovat" / „Pojďme nad tím meditovat" | Kung Fu |

## Dispatch matrix — kdo volá koho

Uzly = role (delivery.yaml). V závorkách persona, která roli typicky plní.

```
T1 (Idea → Spec):
  User request → product → spec-gate → feasibility (L1 tech-feasibility)
                                     ──PASS──► architecture
                                     ──PASS──► ux-design / ui-system (pokud má UI — dle design_source)

  design-track (ux-design/ui-system/design-intake) VISÍ na feasibility PASS, ne paralelně z product
  (Vitek 2026-06-16, nejpřísnější varianta): fail rané brány nezahodí už rozjetou UI práci.

T1 design-source = PROJEKTOVÁ POLITIKA design_source (nastavená 1× při initu, NE per-feature prompt):
  spec.has_ui → engine routuje dle flagu, člověk nedostává „kdo dodá mockup?" otázku:
    author (default) → ux-design kreslí mockup.html z manuálu
    intake           → design-intake gate (user nahraje Figma/v0/Claude design) → ux-design ověří
    derive (solo)    → ui-system staví UI rovnou ze specu (žádný mockup, žádná ux-design)
  ux-design → ui-system, pokud mockup potřebuje komponentu, co v design/manual/ chybí

T2 (Spec → Code):
  architecture → db-schema (pokud DB & touches_db) → backend (server)
              ui-system (design/manual/ + komponenty) ↘ web     (matchuje mockup, je-li)
                                                       ↘ mobile  (pokud aktivní)
                                                       ↘ desktop (pokud aktivní)
                            ↓
                           qa (po unit testech zelených)

T3 (Code → Ověření):
  qa (funkční) → [paralelně] performance, spec-audit, security, code-quality, design-audit
       → všichni PASS → l2-review (vč. estetického soudu nad screenshotem)

T3-post (Release & Deploy):
  All gates PASS → devops → staging (l2-review)
                         → deploy-approve (L3 souhlas) → production
                         → monitor; if fail → rollback → return viníkovi

Return paths (agent dodá VERDIKT; routing k vlastníkovi dělá GRAF, agent nejmenuje kolegu):
  qa FAIL → architecture (diagnostik)  — qa je zkoušeč naslepo (vidí příznak, ne příčinu);
                                         neurčuje vlastníka, jen předá failure signature
  architecture (diagnostik) → fault: db-schema → db-schema | server-logic → backend
                                  | spec → product | contract → opraví sama (re-emit)
  spec-audit   → product | architecture            (spec/contract nekonzistence)
  security     → backend | web | mobile | desktop  (security finding v kódu)
  code-quality → backend | web | mobile | desktop  (code quality finding)
  performance  → backend | web | mobile | desktop  (perf issue)
  design-audit → web | mobile | desktop | ux-design | ui-system  (design conformance)
  devops       → backend | web | mobile | desktop | feasibility | db-schema | qa  (build/deploy/migration fail)

  POZN.: agenti jsou slepé I/O kontrakty — výstup je verdikt (finding / fault: doména),
  routing (který uzel) žije jen v grafu (delivery.yaml). Viz agents/ARCHITECTURE.md.
```

## Auditoři (read-only)

Pět specializovaných auditorů běží **paralelně** po Joey PASS (write scope
nepřekrývá, všichni read-only); každý dodá verdikt + `severity` (blocking/advisory):

- **Optimus** — performance (p50/p95/p99, bottleneck, memory)
- **Sheldon** — konzistence specs/contracts, formátu, normativních pravidel
- **Heimdall** — security (F1–F8 z constitution)
- **Vitek** — code quality (typování, comments WHY, struktura, swallowed except)
- **Edna** — design conformance (mockup match, token usage, manuál, vizuální breaky)

Bez všech PASS = feature není DONE. (Edna jen pokud feature má UI.)

## Per-agent write scope (whitelist)

Kompletní výpis v jednotlivých agent souborech. Default = read-only.
Porušení write scope = BLOCKER.

| Agent | Write scope |
|---|---|
| Vision | `specs/**`, `backlog/**`, `acceptance/**`, `STATE.md §Open Items` |
| Tony | `stack/<target>.md §tech volba`, `IMPLEMENTATION.md`, `status/**` |
| Ted | `rules/**`, `contracts/api/**`, `contracts/error-codes.md` |
| Chandler | `contracts/db/**` |
| Bob | `server/**`, `tests/server/unit/**` |
| Peter | `clients/web/src/**` (kromě `src/ui/`), `tests/web/unit/**`, i18n soubory webu |
| Mob | `clients/mobile/**`, `tests/mobile/unit/**`, mobile i18n soubory |
| Winny | `clients/desktop/**`, `tests/desktop/unit/**`, desktop i18n, native asset metadata |
| Joey | `tests/integration/**`, `tests/e2e/**`, `tests/system/**` |
| Optimus | `tests/perf/**`, `improvements/performance.md` |
| Denisa | `design/**` (kromě `design/manual/`), `improvements/ux.md` |
| Leonard | `design/manual/**`, `clients/<platform>/src/ui/**`, `clients/<platform>/src/ui/**/*.module.css` — **NOTE:** page-level `*.module.css` mimo `src/ui/` vlastní Peter/Mob/Winny (jejich page scope); Leonard vlastní jen `src/ui/` styly |
| Sheldon | žádný — read-only, vrací findings |
| Heimdall | žádný — read-only, vrací findings (audit log `audit/destructive-ops.md` jen pro destruktivní L3) |
| Vitek | žádný — read-only, vrací findings |
| Edna | žádný — read-only, vrací design findings (WARNING → `improvements/design.md`) |
| Alfred | `.github/workflows/**`, `Dockerfile*`, `docker-compose*.yml`, `docker-entrypoint.sh`, `fly.toml`, `fly-db.toml`, `scripts/` (deploy/release), `CHANGELOG.md` |
| Eywa | `.agentic/agents/**` (po L3 pro nový/smazaný; L1 pro úpravu), `.agentic/templates/agent-template.md` po L3, INDEX.md, project-config.md §write-scope-table |
| Watson | `project-config.md`, `PROJECT-CONSTITUTION.md` (seed z templatu + overlays), `stack/**` (kompozice z `templates/stacks/`), `rules/**` (greenfield: seed z `templates/rules/`; transition: extrakce s user schválením), `CLAUDE.md` (root), `backlog/setup-seed.md`, bootstrap-only scaffold copy do `server/**` / `clients/**` + `contracts/db/migrations/**` (L2, jednorázově). Po setupu stop write. |

## Failure protokol per agent

Default: 3 pokusy + augmented triggers (scope drift, regression, test-changed).
Override:
- **Optimus**: 5 pokusů (perf tuning je iterativní)
- **Auditoři (Sheldon, Heimdall, Vitek, Edna)**: N/A — read-only, jen reportují
- **Eywa**: N/A — meta-agent, nepoužívá failure loop (operuje na user request,
  ne v automatickém dispatch)

## Meta-agenti — kdy je volat

| Trigger | Agent |
|---|---|
| Nový projekt / přechod na agentic / chybí project-config | Watson |
| „Pojďme meditovat" / „Pojďme nad tím meditovat" | Monk |
| „Přidej agenta X" | Eywa |
| „Smaž agenta X" | Eywa → L3 |
| „Zkontroluj role overlap / write scope conflicts / dispatch graph" | Eywa |
| „Aktualizuj agent template" | Eywa → L3 |
| „Sunset skill X" | Eywa (updatuje project-config §Skill-to-agent mapping) |

## Activation profily

Cast (19) je menu, ne mandát. **Cíl: nejet 19 agentů na jednoduchý projekt.**
Profil = startovní set aktivních agentů dle složitosti (`project-config.md
§profile`). Vypnutý agent NEní smazaný — zůstává v castu (učení), jen se
nedispatchuje; zapne se, až ho projekt potřebuje.

Navrch se aplikuje **target-gating** (no web → Peter off; no mobile → Mob off;
no desktop → Winny off; no DB → Chandler off; no deploy → Alfred off).

| Profil | Aktivní (před target-gatingem) | Pro koho |
|---|---|---|
| **solo** (~8) | Vision, Ted, Bob, Peter, Joey, Heimdall, Vitek (+ Watson setup) | solo dev, jednoduchý projekt; user hraje Tony/PO, ostatní zapíná dle potřeby |
| **standard** (~13) | solo + Tony, Chandler, Sheldon, Leonard, Alfred | většina reálných projektů |
| **full** (19) | celý cast (+ Optimus, Denisa, Edna, Eywa, Mob, Winny) | komplexní: multi-tenant SaaS, compliance, víc targetů, design-heavy |

Watson doporučí profil v setup interview (fáze 5) dle složitosti; user potvrdí
nebo upraví. Jednotlivé agenty lze kdykoli zapnout/vypnout v `project-config.md`
nezávisle na profilu (profil je jen výchozí bod, ne zámek).

## Model strategy

Druhá osa vedle activation profilů: profil určuje, *kteří* agenti jsou aktivní;
**model tier** určuje, na *jakém modelu* úkol běží. Hodnota `model:` ve
frontmatteru každého agenta je **výchozí strop**; orchestrátor ji dle
`flow.md §Model routing` (rubrika složitosti) smí **snížit** (triviální instance
→ `haiku`) nebo **zvýšit** (záludná → `opus`). `haiku` není default žádné role —
mechanická práce patří do scriptů (`constitution.md §Scripted extraction first`),
`haiku` je cíl downgrade. Pro Claude Code se default propaguje do
`.claude/agents/<short>.md` (`scripts/setup/setup-claude-code.sh` čte pole `model:`).

Strop per agent (mechanická projekce frontmatterů, bez sloupce „Proč" — ten je autorský):

<!-- GENERATED: model-strategy — needituj ručně, spusť scripts/gen-cast-tables.py -->
| Default model | Agenti |
|---|---|
| `opus` | `tony-cto`, `ted-architect`, `heimdall-security` |
| `sonnet` | `vision-po`, `sheldon-spec`, `denisa-ux`, `chandler-db`, `leonard-ui`, `bob-backend`, `peter-web`, `mob-mobile`, `winny-desktop`, `vitek-quality`, `joey-qa`, `optimus-perf`, `edna-design`, `alfred-devops` |
<!-- /GENERATED: model-strategy -->

**Proč ten strop** (autorský úsudek, nederivuje se z grafu): `opus` u rolí s velkým blast
radiem / drahými false-negatives — tech strategie a cross-target koordinace (Tony), API kontrakty
a breaking changes (Ted), security úsudek F1–F8 (Heimdall). `eywa-meta` (mimo flow, není v tabulce
nad) běží také na `opus` — architektura agent-systému. `vision-po` má `sonnet` strop, ale orchestrátor
ho smí zvýšit na `opus` u produktově nejednoznačných feature. Zbytek (implementátoři dle blueprintu +
read-only auditoři) na `sonnet`. `haiku` není default žádné role — je to cíl downgrade u triviálních
instancí (mechanická práce patří do scriptů, `constitution.md §Scripted extraction first`).

Tabulka je laděná, ne dogma — tier per agent uprav ve frontmatteru
`agents/<short>.md`, pak regeneruj (`scripts/gen-cast-tables.py`) +
`scripts/setup/setup-claude-code.sh` + restart session.

## Auto-detection při init

Při startu Claude Code session orchestrátor zkontroluje:
- Existuje `CLAUDE.md` s agentic bootstrapem? Existuje `project-config.md`?
  - Ano → načti, použij, jeď
  - Ne → **invokuj Watson** ("vidím, že projekt nemá agentic setup; chceš ho založit?")
- `project-config.md §profile` + `§active_agents` určuje, kteří agenti jsou
  pro tento projekt relevantní (zbytek dispatch přeskočí)
