# Run summary — 2026-06-18-github-projects

uzlů: 37   poslední outcome: PASS

## Čas
- wall-clock: 0m 0s (min started → max ended)
- compute (Σ uzly): 1h 23m 9s
- ⚠ neměřeno: 10/37 uzlů bez naměřeného času (telemetrie chyběla — NEzapočítáno, ne „0 s práce")

## Cost
- kredity (měřené): neměřeno — žádný uzel nenese cost.credits
- kredity (odhad z tokenů, indikativní): 7.11
- ⚠ neměřeno: 10/37 uzlů bez ceny i tokenů (NEzapočítáno jako úspora — telemetrie chyběla)
- tokeny: in 1398947 / out 0

## Per model
| model | uzlů | in | out | kredity |
|---|---|---|---|---|
| - | 10 | 0 | 0 | 0.00 |
| haiku | 2 | 27081 | 0 | 0.00 |
| opus | 3 | 247617 | 0 | 0.00 |
| sonnet | 22 | 1124249 | 0 | 0.00 |

## Per uzel
| uzel | agent | model | outcome | čas | kredity |
|---|---|---|---|---|---|
| intake | None | - | PASS | 0m 0s | 0.00 |
| product | vision-po | sonnet | PASS | 3m 48s | ~0.17 |
| spec-gate | sheldon-spec | sonnet | FAIL | 1m 55s | ~0.10 |
| product | vision-po | sonnet | PASS | 0m 52s | ~0.05 |
| spec-gate | sheldon-spec | sonnet | PASS | 1m 45s | ~0.10 |
| feasibility | tony-cto | opus | FAIL | 2m 19s | ~1.30 |
| product | vision-po | sonnet | PASS | 1m 43s | ~0.06 |
| spec-gate | sheldon-spec | sonnet | FAIL | 1m 3s | ~0.05 |
| product | vision-po | haiku | PASS | 0m 9s | ~0.01 |
| spec-gate | sheldon-spec | haiku | PASS | 0m 23s | ~0.01 |
| feasibility | tony-cto | sonnet | PASS | 0m 22s | ~0.05 |
| architecture | ted-architect | opus | PASS | 7m 39s | ~1.81 |
| ui-system | leonard-ui | sonnet | PASS | 9m 20s | ~0.32 |
| db-schema | chandler-db | sonnet | PASS | 4m 58s | ~0.21 |
| web | peter-web | sonnet | PASS | 9m 57s | ~0.43 |
| backend | bob-backend | sonnet | PASS | 12m 37s | ~0.39 |
| code-lint | vitek-quality | - | PASS | 0m 0s | 0.00 |
| qa | joey-qa | sonnet | FAIL | 5m 2s | ~0.26 |
| architecture | ted-architect | sonnet | FAIL | 0m 40s | ~0.10 |
| architecture | ted-architect | - | PASS | 0m 0s | 0.00 |
| db-schema | chandler-db | - | PASS | 0m 0s | 0.00 |
| web | peter-web | - | PASS | 0m 0s | 0.00 |
| backend | bob-backend | sonnet | PASS | 2m 7s | ~0.09 |
| code-lint | vitek-quality | - | PASS | 0m 0s | 0.00 |
| qa | joey-qa | sonnet | PASS | 2m 34s | ~0.11 |
| security | heimdall-security | opus | PASS | 1m 26s | ~0.61 |
| code-quality | vitek-quality | sonnet | FAIL | 0m 54s | ~0.11 |
| design-audit | edna-design | sonnet | FAIL | 1m 59s | ~0.16 |
| backend | bob-backend | sonnet | PASS | 1m 53s | ~0.13 |
| ui-system | leonard-ui | sonnet | PASS | 2m 41s | ~0.10 |
| spec-audit | sheldon-spec | sonnet | PASS | 1m 7s | ~0.18 |
| web | peter-web | - | PASS | 0m 0s | 0.00 |
| code-lint | vitek-quality | - | PASS | 0m 0s | 0.00 |
| qa | joey-qa | - | PASS | 0m 0s | 0.00 |
| security | heimdall-security | - | PASS | 0m 0s | 0.00 |
| code-quality | vitek-quality | sonnet | PASS | 0m 45s | ~0.09 |
| design-audit | edna-design | sonnet | PASS | 3m 11s | ~0.11 |

## Return loops
- code-quality->backend: 1
- design-audit->ui-system: 1
