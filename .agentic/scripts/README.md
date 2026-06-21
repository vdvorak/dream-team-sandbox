---
cache_key: scripts-readme-v1.0
type: documentation
---

# `.agentic/scripts/` — Agent Helper Scripts

Tento adresář obsahuje **scripty, které agenti volají místo čtení celých
souborů** (per `constitution.md` §Scripted extraction first).

LLM tokeny jsou drahé; mechanické úkoly (extrakce sekce, hash, count,
diff) patří do scriptů, ne do kontextu modelu.

## Domain helpers — volané za běhu

| Script | Účel | Kdo to volá |
|---|---|---|
| `spec-length.sh <feature>` | Počet řádků spec (exit 1=WARN >200, exit 2=BLOCKER >400) | Vision (self-review), Sheldon (gate) |
| `rules-section.sh <file> <section>` | Extrakce §sekce z rules/stack souboru | Všichni — místo čtení celého rules souboru |
| `failure-hash.sh <check> <type> <location>` | Deterministický hash failure signature pro counter | Joey, auditoři, dispatch engine |
| `find-line-refs.sh <file-or-dir>` | Detekce zakázaných `path:NNN` / „řádek NNN" odkazů (Constitution §6) | Sheldon (auto při spec review) |
| `agent-graph-check.sh` | Audit agent definic (duplicate shorts, missing fields, write-scope overlap N3, agent↔persona N1, cast drift N6) | Eywa |
| `gen-cast-tables.py [--check]` | Generuje derivovatelné cast tabulky (cast / model-strategy / OVERVIEW cast) z `delivery.yaml` + frontmatterů do `<!-- GENERATED -->` bloků v INDEX.md/OVERVIEW.md; `--check` = exit≠0 při driftu (N6) | Eywa (po změně cast) |
| `openapi-slice.sh <operationId>` | Extrakce konkrétního endpointu z OpenAPI místo celého souboru | Ted, Bob, Peter, Joey |
| `drift-scan.sh` | Detekce cross-project kontaminace (cizí otisky sourozeneckých projektů) + tvary live secrets; exit 1 = nález k posouzení | Vitek (gate + drift-align) |

## Setup bootstrappers — jednorázové při klonování

V `scripts/setup/`:

| Script | Účel |
|---|---|
| `detach-template.sh` | `rm -rf .agentic/.git` po klonu z dream-team (jednoduchý DX helper) |
| `setup-claude-code.sh` | Vytvoří `.claude/settings.json` + reference na CLAUDE.md |
| `setup-cursor.sh` | Vytvoří `.cursorrules` s `@.agentic/...` references |
| `setup-aider.sh` | Vytvoří `.aider.conf.yml` |

## Konvence

- Všechny scripty jsou **POSIX bash** nebo **Python 3** (žádné node, ruby
  pro nezávislost na stacku projektu)
- Každý script má v hlavičce: usage, příklad, exit codes
- Exit code 0 = OK, 1 = WARNING/finding, 2+ = chyba (závisí na scriptu)
- Scripty nemodifikují source content (rules, specs, contracts, kód) —
  jen čtou a reportují. Výjimka: setup bootstrappers, které zakládají
  novou konfiguraci

## Když script chybí

Pokud agent narazí na opakovaný extraction pattern a script pro něj chybí:
1. **Neeskaluj okamžitě** — zkus to vyřešit ad-hoc grep/awk
2. **Po 2× použití** (Constitution §Reuse policy: 2+ = extract candidate)
   → eskaluj na **Eywa** s návrhem nový script
3. Eywa rozhodne (L1 pro malý helper; L3 pro významný nový tool)

## Jak přidat nový script

1. Napiš script v `scripts/` (nebo `scripts/setup/` pro bootstrappery)
2. `chmod +x` script
3. Aktualizuj tento README.md (tabulky výše)
4. Aktualizuj agent definici, který ho bude volat (sekce „Tools (scripty)")
5. Commit do template repo (pokud jde do dream-team)

## Model routing (v0.15.0)
- `model-usage.sh [<run-id>|--ledger <cesta>]` — skladba modelů + tier rozpad + odhad úspory vs. vše-opus, **derivováno z ledgeru** (`runs/<run>/ledger.yaml`, jediný zdroj pravdy; engine ho plní z `done`). `tier` nese envelope; ruční `model-routing-log.md` zrušen (N5).
- `complexity-estimate.sh [soubor ...]` — levný deterministický prior tieru složitosti z diffu/souborů (XS/S/M/L).

## Pipeline (forward-looking — runner zatím nevykonává live flow)

Strojová obsluha grafu `pipeline/delivery.yaml` (viz `pipeline-architecture.md`).
Additivní — dnešní LLM orchestrace běží beze změny, dokud se runner neadoptuje.

| Script | Účel | Kdo to volá |
|---|---|---|
| `pipeline/state.sh [current-run.md]` | Report strojového stavu běhu (active/pending/completed/counters); 3× counter = BLOCKER hint | Orchestrátor / Watson (session-resume) |
| `pipeline/next.sh --from <node> --outcome <PASS\|FAIL\|...>` | Deterministicky spočítá další uzel(y) z grafu + project flagů + výsledku; LLM dodá jen outcome, ne routing | Orchestrátor (dispatch) |
| `pipeline/check.sh [delivery.yaml]` | Validátor integrity grafu (C1–C9: parse, dangling refs, join.requires, neznámý agent, dead-end, orphan, **spec-driven invariant**, typované I/O slovník + existence producenta); exit 1 = nález | Eywa (audit) + CI |
| `pipeline/result.sh <envelope> [--check-only]` | Zpracuje node-result obálku („/done"): ověří + připíše do `runs/<run>/ledger.yaml` + posune `current-run.md` (completed/last_outcome/counters) | Orchestrátor po dokončení uzlu |
| `pipeline/ledger.sh [<run-id>] [--no-write]` | Agreguje `runs/<run>/ledger.yaml` → cost + čas per issue (wall-clock, compute, kredity, tokeny, per model/uzel, loops); zapíše `runs/<run>/summary.md`. Odhad kreditů z tokenů přes volitelný `pipeline/model-prices.yaml` | Orchestrátor na konci runu |
| `pipeline/scaffold.sh [--backend X\|--frontend Y\|--platform Z\|--deploy W\|--agent\|--all]` | Resolvne scaffold(y) z `templates/scaffolds/manifest.yaml` (path + produces + docker_dev) pro scaffold-passing při delegaci | Hlavní agent před delegací subagentovi |
| `pipeline/run.sh <start\|active\|status\|next\|done\|summary\|check\|scaffold>` | **Jednotný vstup runneru** (executor nad grafem); deleguje na výše + convenience start/active. App volá tutéž logiku | Orchestrátor / runner / app |
| `pipeline/selftest.sh` | End-to-end smoke test smyčky (start→done→next→summary→check) v mktemp; regression guard | CI / po změně pipeline scriptů |
| `pipeline/lib.sh --stack X [--capability Y]` | Doporučená knihovna pro schopnost+stack z `templates/stacks/recommended-libs.yaml` (vetted); mimo list = nová závislost → Tony/Heimdall | Ted/Bob/Peter před volbou knihovny |
