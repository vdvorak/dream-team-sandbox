---
cache_key: gate-output-v1.1
type: template
last_updated: 2026-05-30
---

# GATE OUTPUT — base template

# Každý agent přidává své řádky pod base (viz `agents/<short>.md §Formát výstupu`).

## === GATE OUTPUT ===
agent: <agent-short>
phase: <T1|T2|T3|gate>
<main-check>: OK | FAIL — <důvod>
write-scope: RESPECTED | VIOLATED
returns-to: <agent-short>
weak-spot: <one-line>
==================
