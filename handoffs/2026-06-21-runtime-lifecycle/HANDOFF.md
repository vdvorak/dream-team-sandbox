# HANDOFF — Wave `2026-06-21-runtime-lifecycle` (runtime control-plane lifecycle core slice 1)

**Datum:** 2026-06-21 · **Stav:** done, vsechny gates PASS · **L3:** zadna cross-repo operace.

> Vstupni bod pro resume. Strojovy stav: `current-run.md` + `STATE.md` (ENGINE:STATE blok).
> Plan: `~/.claude/plans/logical-churning-shore.md`. Predchozi wave: `handoffs/2026-06-21-runtime-contract/`.

## Co se stalo

Postavena **PATER RUNTIME CONTROL-PLANE** — net-new lifecycle core slice 1, standalone
v tomto repu. **Cil wave**: implementovat 5 operaci stavoveho automatu (ensure/get/sleep/
destroy/healthz), fail-closed EnforcementProvider kontrakt, 3-vrstvou architekturu
(router/service/repository), prochazet 7 T1-T3 gates. **NE** cross-repo motor-extrakce
(ta zustava budouci L3).

**Wave (15 uzlu, vsechny PASS, return_loops: 1):** intake → product (spec+acceptance) →
spec-gate (3 kola audit-defect — Sheldon vracel kategorie agnostika-leaku po davkach;
orchestrator pouzil `resolve-loop spec-gate->product`, counter 3→0, strukturalni lean
prepis specu) → feasibility → architecture → security (heimdall, opus; PASS) →
code-quality → **implementation (bob)** → qa → perf → spec-audit (FAIL: acceptance
nesynchronizovan po contract-bumpu AC-1g/1b/9a → opraveno; re-flow 6 uzlu
orchestrator re-verifikoval tesry+grep misto plneho re-dispatch) → **done**.

**In-flight contract fix:** implementace odhalila mezeru — acceptance vyzadoval 400
+ odmituti extra poli, ale `contracts/runtime-contract.md §8` nemel kod →
**ERR_INVALID_REQUEST pridano, kontrakt bumpnut v1.0.0 → v1.1.0** (non-breaking
per §6; jednosmerne pridani kodu).

**Deploy track vedome preskoce** — uzivatel rozhodl odlozit produkcni deploy na
slice 2 (realny motor/klec + cloud infra). Gate `devops`/`deploy` N/A pro tuto wave.

## Deliverables (committed, tento repo)

| Soubor / adresar | Obsah |
|---|---|
| `server/runtime/**` (13 modulu) | router + service + repository vrstvy; EnforcementProvider Protocol (EnforcementActive | EnforcementFailed uzavreny soucet) |
| `server/runtime/enforcement/` | DevEnforcementProvider (active/fail/down rezimy) + CageEnforcementProvider (STUB, napojeni na slice 2) |
| `server/runtime/main.py` | Spustitelny entry: `uvicorn server.runtime.main:app` |
| `specs/runtime-control-plane.md` | Behavioralni spec, substratum-agnosticky |
| `acceptance/runtime-control-plane.md` | RCP-1..14; in-scope: RCP-1,2,3,4,5,9,10,11,12,13,14; deferred: RCP-6/7/8 (git/files/terminal = slice 2) |
| `rules/runtime-control-plane.md` | RCP-A1..A8 architektonicka pravidla |
| `stack/runtime-control-plane.md` | Stack doc (FastAPI + Pydantic v2 + uvicorn) |
| `contracts/runtime-contract.md` | **Bumpnut v1.0.0 → v1.1.0** (ERR_INVALID_REQUEST pridan) |
| `contracts/api/runtime.openapi.yaml` | Aktualizovano dle v1.1.0 |
| `tests/server/unit/test_runtime_lifecycle.py` | 49 unit testu — PASS |
| `tests/integration/test_runtime_lifecycle_integration.py` | 74 integration testu — PASS |
| `tests/perf/` | 7 perf testu — PASS |

**Celkova suite: 243/243 PASS.**

## Gate verdikty

| Gate | Agent | Vysledek | Poznamka |
|---|---|---|---|
| spec-gate | sheldon | PASS (po 3 kolech) | resolve-loop spec-gate→product; strukturalni prepis specu |
| feasibility | ted | PASS | z minule wave |
| architecture | ted | PASS | 3-vrstva; EnforcementProvider uzavreny typ |
| security | heimdall (opus) | PASS | advisory: dev-token fail-fast guard, constant-time compare |
| code-quality | vitek | PASS | advisory: type anotace, test-helper dedup, healthz 503 v OpenAPI (W3) |
| qa | joey | PASS | 243/243 testu |
| perf | optimus | PASS | advisory: lock-dict GC, destroyed GC, perf acceptance targets |
| spec-audit | sheldon | PASS (po oprave) | AC-1g/1b/9a nesync po contract-bumpu → opraveno |

Deploy track (devops/deploy): **vedome preskocen** — odlozeno na slice 2.

## Stav implementace po wave

| Vrstva | Stav |
|---|---|
| Router (5 ops: ensure/get/sleep/destroy/healthz) | HOTOVO |
| Service (stavovy automat none→provisioning→ready→asleep/destroyed; fail-closed) | HOTOVO |
| Repository (InMemoryRuntimeRepository) | HOTOVO |
| EnforcementProvider Protocol + uzavreny soucet | HOTOVO |
| DevEnforcementProvider | HOTOVO |
| CageEnforcementProvider | STUB — napojeni na server/cage = slice 2 |
| PTY/terminal (AC-8), git status (AC-6), file-read (AC-7) | Deferred — slice 2 |
| Produkcni deploy (Fly infra, secrets, image, staging→prod) | Deferred — slice 2 |

## Live demo verifikace (2026-06-21, po uzavreni wave)

Slice 1 empiricky overen za behu (uvicorn lokalne, dev provider), ne jen unit/integration testy:

- **Normalni lifecycle** (provider `active`): healthz `200 ok` · ensure bez tokenu `401 ERR_UNAUTHORIZED`
  · ensure s tokenem `200 ready` + neprůhledny handle (`https://rt.<opaque>.example/control/...`,
  `wss://.../terminal/...`, zadny substrat-noun) · get `ready` · ensure-znovu idempotent · jine repo
  `409 ERR_REPO_MISMATCH` · bypass pole `firewall:off` → `400 ERR_INVALID_REQUEST` (ZED nelze oslabit)
  · sleep `asleep` (connection→null) · destroy `destroyed`.
- **Fail-closed** (provider `down`): healthz `503 degraded` · ensure `ERR_RUNTIME_UNAVAILABLE`
  (nikdy ready) · get zustava `provisioning` (connection null). **Potvrzeno: bez aktivni ZDI se
  prostredi NIKDY nestane ready.**

Spusteni: `ENFORCEMENT_PROVIDER=dev DEV_PROVIDER_MODE=active|fail|down SERVICE_TOKEN=... uvicorn server.runtime.main:app`.

## Pouceni z wave (logy pro dalsi iterace)

1. **Spec-gate depth-first:** Sheldon vracel kategorie agnostika-leaku po davkach (ne
   v jednom pruchodu). Reseni: `resolve-loop spec-gate->product` s counter (max 3)
   + `--deep` vlajka na finalni audit = nutnost. Pridat do `rules/runtime-control-plane.md`
   nebo `improvements/` jako pattern pro budouci spec-heavy waves.
2. **In-flight contract bump:** Acceptance gate muze odhalit contract-mezeru az pri
   implementaci (ne pri design-wave). Vzor: bump je non-breaking (pridani kodu),
   koordinace = update acceptance + OpenAPI + kontrakt atomicky v jednom commitu
   pred re-spec-auditem.
3. **Re-flow bez plneho re-dispatch:** Po spec-audit FAIL (lokalni AC oprava) staci
   orchestrator re-verifikoval testy+grep pro 6 uzlu misto plneho re-dispatch —
   usetri cas, ale jen kdyz zmenene soubory jsou jasne ohranicene.

## Advisory hardening (improvements/, neblokujici)

Ulozeno v `improvements/` (vytvori bob/security/optimus pri slice 2):

- **security.md:** dev-token fail-fast guard (startup check), constant-time compare
  pro token validaci.
- **code-quality.md:** type anotace (mypy strict), test-helper dedup, healthz 503
  v OpenAPI (W3 z code-quality gate).
- **performance.md:** lock-dict GC pro destroyed/asleep Environments, perf acceptance
  targets formalizovat v `acceptance/runtime-control-plane.md`.

## Open Items pro slice 2 (gated, budouci)

1. **Realny MOTOR (slice 2):** CageEnforcementProvider → realna integrace na
   `server/cage/**`; realne klonovani repa; realne spusteni agenta v kontejneru;
   PTY/terminal (AC-8); git status (AC-6); file-read (AC-7).
2. **Produkcni deploy:** Fly infra + secrets, build image (vlastni verzovany), staging
   → produkce. Vedome odlozeno z teto wave.
3. **Advisory hardening** (viz sekce vyse): security + code-quality + perf improvements.
4. **Motor-extrakce (z minule wave, koordinovany L3):** vendoring kontraktu do
   dream-team-app + presun motoru. Kazdy krok = L3 ve vice repech, vyzaduje vyslovne
   potvrzeni provozovatele.
