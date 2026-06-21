---
cache_key: work-breakdown-v1.0
type: template
last_updated: 2026-05-30
---

# Work breakdown — dekompozice L úkolu

> Vyplní orchestrátor / Tony při triage, když úkol vyjde **L**
> (viz `flow.md §Model routing`). Cíl: rozpadnout na S/M podúkoly, které
> utáhnou levnější modely; `opus` jen na neredukovatelné jádro úsudku.

## Úkol
<1-2 věty, co je celý L úkol>

## Jádro úsudku (opus)
<co MUSÍ rozhodnout silný model — architektura / contract / security;
ideálně 1 položka. Tohle je jediné, co opravdu potřebuje opus.>

## Podúkoly (levnější modely)
| # | Podúkol | Vlastník (agent) | Tier | Model | Závislost |
|---|---|---|---|---|---|
| 1 | <co> | <short> | S/M | sonnet | — |
| 2 | <co> | <short> | XS | haiku | 1 |

## Složení zpět
<jak se výstupy podúkolů spojí v celek; kdo ověří integraci>
