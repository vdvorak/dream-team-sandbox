---
wave: 2026-06-21-containment-cage
phase: T3
from: joey-qa
to: orchestrator
type: qa-handoff
timestamp: 2026-06-21T00:00:00+02:00
outcome: PASS
---

# T3 QA Handoff — containment-cage

## Výsledek

outcome: PASS
integration-tests:  27/27 PASS (0 FAIL)
system-tests:       28/28 PASS (0 FAIL) [static overlay]
regression-tests:   15/15 PASS (0 FAIL)
unit-tests-base:    58/58 PASS (0 FAIL) [Bob baseline, beze změn]
total:             128/128 PASS
acceptance-coverage: BLOCKED na 32 live AC bodů (nutno nasadit klec)
regression: OK — žádný NEW_FAIL oproti Bobovu baseline

## Co bylo vytvořeno

### Nové soubory

- `tests/integration/test_cage_deploy_integration.py`
  27 integration testů: happy-path, drift detekce, ingress leak, secret scan,
  git write cred, policy fail-closed, smoke selhání, ACL render.

- `tests/integration/test_overlay_static.py`
  28 statických testů overlay artefaktů (bez živé klece):
  fly.workspace.toml (I7), nftables.cage.conf (I1/I4),
  Dockerfile.workspace (I6), entrypoint.sh (I4/I6 de-root pořadí).

- `tests/acceptance/containment_cage_harness.sh`
  Shell harness pro spuštění ZEVNITŘ workspace PTY po deployi.
  Implementuje všech I1–I11 verifikačních příkazů z acceptance/containment-cage.md.
  Použití: bash tests/acceptance/containment_cage_harness.sh [CF_TEAM=<team>]

- `tests/acceptance/regression_test_plan.py`
  15 regression testů (pytest -m regression):
  P0 mandatorní (I7 re-test, ruleset kompletnost, entrypoint pořadí),
  P1 bezpečnostní invarianty, P2 pre-deploy smoke guardy.

- `pytest.ini` — registrace regression marku

## Acceptance coverage

| AC | tag | stav |
|----|-----|------|
| I1 (1a–1e) | [security][post-deploy-live] | BLOCKED — nutno nasadit klec |
| I2 (2a–2d) | [security][post-deploy-live] | BLOCKED |
| I3 (3a–3c) | [security][post-deploy-live] | BLOCKED |
| I4 (4a–4c) | [security][post-deploy-live] | BLOCKED (statická verifikace entrypoint: PASS) |
| I5 (5a–5c) | [security][post-deploy-live] | BLOCKED |
| I6 (6a–6b) | [security][post-deploy-live] | BLOCKED (statická: Dockerfile/entrypoint: PASS) |
| I7 (7a–7c) | [security][post-deploy-live] | BLOCKED (I7b staticky: PASS; I7a nutno zvenku) |
| I8 (8a–8c) | [integration][post-deploy-live] | BLOCKED |
| I9 (9a–9b) | [security][post-deploy-live] | BLOCKED |
| I10 (10a–10c) | [security][post-deploy-live] | BLOCKED |
| I11 (11a–11c) | [security][post-deploy-live] | BLOCKED |

Staticky pokryté (bez živé klece): I4/strukturální, I6/strukturální, I7b/strukturální,
entrypoint de-root pořadí, overlay fly config, nftables tvar, Dockerfile hardening.

## Regression plán po každém deployi

Povinné (P0, kontraktem mandatorní — zejm. I7c):
1. `python3 -m pytest tests/ -m regression -v`
2. `bash tests/acceptance/containment_cage_harness.sh` (zevnitř workspace PTY)
3. Pro I7a: `curl -m5 https://<workspace-app>.fly.dev` (z externího hosta)

## Blocker na gate PASS

Gate PASS acceptance/containment-cage.md = I1–I11 všechna AC zelená na živém deployi.
Klec ještě není nasazena (alfred T4) → 32 live AC bodů BLOCKED.
Statická vrstva (128 pytestů) je zelená.

Po deployi: spustit harness, vrátit výsledky pro gate uzavření.
