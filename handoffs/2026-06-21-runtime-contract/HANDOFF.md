# HANDOFF — Wave `2026-06-21-runtime-contract` (re-charter + KONTRAKT)

**Datum:** 2026-06-21 · **Stav:** ✅ design-complete, vsechny gates PASS · **L3:** nic se nepresouvalo mezi repy.

> Vstupni bod pro resume. Strojovy stav: `current-run.md` + `STATE.md`. Plan:
> `~/.claude/plans/logical-churning-shore.md`. Predchozi wave: `handoffs/2026-06-21-containment-cage/`.

## Co se stalo

Repo **povyseno** z „out-of-band klec obalujici dream-team-app" na **samostatnou RUNTIME/SANDBOX
vrstvu (MOTOR + ZEĎ), ktera vystavuje kontrakt** (per North Star: 3 vrstvy framework/runtime/app).

**Krok 0 (L3 re-charter):** Watson prepsal `PROJECT-CONSTITUTION.md` — North Star, identita
RUNTIME, I1-I11 jako spec ZDI, MOTOR nacrt, kontrakt sekce. `project-config.md` vision → runtime.
Commit `bae4948`. Cage framing superseduji, ZEĎ (I1-I11, server/cage/**) zachovana.

**Wave (pres dream-team pipeline, 7 nodes PASS):** intake → product (vision: spec+acceptance) →
spec-gate (sheldon; 1x FAIL agnostika → fix) → feasibility (z minule wave) → **architecture =
KONTRAKT** (ted) → **security** (heimdall) → **spec-audit** (sheldon).

## Deliverables (committed, tento repo)

| Soubor | Obsah |
|---|---|
| `PROJECT-CONSTITUTION.md` | re-charter (North Star + identita + I1-I11 ZEĎ + MOTOR + kontrakt) |
| `specs/runtime-contract.md` | schopnosti runtime (agnosticke) |
| `acceptance/runtime-contract.md` | AC-1..14 (otagovane) |
| **`contracts/runtime-contract.md`** | KONTRAKT — proza, state machine, trust model, app-facing error registr (10 kodu) |
| **`contracts/api/runtime.openapi.yaml`** | OpenAPI 3.1 — 8 ops, `Environment` schema, `x-websocket` PTY |
| `audit/runtime-boundary.md` | hranicni prestupky + standalone mezery + endpoint→kontrakt mapovani + extrakce roadmapa |

## Kontrakt — jadro

Noun `Environment` (1:1 projekt, opaque `project_id`), state machine `none→provisioning→ready→asleep→destroyed`.
8 ops: ensure (clone slozeny dovnitr) / get / sleep / destroy / git / files / terminal(WS) / healthz.
**Opaque `connection` handle** (zadny substrate-noun). Auth: User→App CF-Access (app-interni) ·
App→Runtime mTLS/token · BYOK jen interaktivne v PTY (nikdy control API). **ZEĎ disjunktni**
(`additionalProperties:false` strukturalne; fail-closed „ready jen s aktivni ZDI"). Vlastnictvi:
runtime vlastni, app vendoruje read-only. Verzovani SemVer /v1, breaking = koordinovany L3.

## Gate verdikty

- **heimdall (security) PASS** (advisory): ZEĎ-disjunktnost + fail-closed + no-leak + BYOK + auth OK.
  2 advisory: `phase` a `Error.detail` jsou volne leak kanaly → impl MUSI scrubovat + contract-test.
- **sheldon (spec-audit) PASS**: konzistence + plocha-agnostika + app-facing registr disjunktni + AC-1..14 0 orphanu.

## Pozn. k frameworku

run.sh wave dosahla 7 nodes; T3 audity (security/spec-audit) zaznamenany primym dispatchem +
`done` (graf vyzaduje kod pro T3 retez — docs-only wave ho nema, takze qa/perf/code-quality/devops/
deploy jsou N/A). Wave je `in_progress` (nedosahne `done` terminal — ocekavane pro docs-only).

## Dalsi krok (NEprovedeno — gated L3)

**Motor-extrakce** (viz `audit/runtime-boundary.md §F` + plan): vendor kontraktu → presun
agent/lifecycle/image do runtime → app na tenke contract-klienty → live acceptance → retire dvoji
impl. Kazdy krok = koordinovany L3 ve vice repech, vyzaduje vyslovne potvrzeni provozovatele.
