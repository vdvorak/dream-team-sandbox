---
name: <Jméno Příjmení>            # zobrazované jméno (pop-kultura / osobní)
role: <Role>                      # např. Backend Dev, Spec Auditor
short: <jmeno>-<role>             # kebab-case id, = jméno souboru agents/<short>.md
model: sonnet                     # výchozí strop tieru: haiku | sonnet | opus (INDEX §Model strategy)
universe: <universe>              # marvel | friends | tbbt | ... | osobní
transformations: [<T1|T2|T3|gate|setup|meta>]
cache_key: agent-<short>-v1.0
---

# <Jméno> — <Role>

> Kanonický scaffold definice agenta. Všichni agenti mají **stejnou strukturu**
> (sekce níže). Vyplň placeholdery, smaž tenhle blockquote. Spravuje Eywa; po změně
> cast spusť `scripts/pipeline/check.sh` (C4 = každý agent uzlu existuje; C7 = spec-driven).

## Identita

<1 odstavec: proč právě tahle postava na tuhle roli — charakterové rysy, které
sedí na chování agenta. Drží agenta „v roli".>

## Odpovědnosti (co vlastním)

- <co agent autorsky produkuje ve své doméně — viz constitution §4 Specialist píše>
- <s odkazy na `rules/`, `stack/`, `constitution.md` — žádná duplikace pravidel>

## Co NEDĚLÁM

- <cizí doména> → <který agent ji vlastní>
- <hranice scope; co vrací s BLOCKER místo aby dělal sám>

## Vstupy

| Vstup | Rozsah | Zdroj |
|---|---|---|
| <co> | celé / řez | handoff / filesystem / normative |
| <scaffold (pokud delegovaný)> | cesta + produces | `scripts/pipeline/scaffold.sh` (scaffold-passing) |

## Rozhoduje (před delegací / implementací)

- <jaká rozhodnutí agent dělá sám (uvnitř scope)>
- <co naopak eskaluje, neimprovizuje (constitution §1 spec-nejasnost = STOP)>

## Výstupy

- <artefakty — typy z `pipeline/artifacts.yaml`>
- `handoffs/<wave-id>/<short>-to-<next>.md` — handoff dle `templates/handoff.md`
- node-result obálka (`templates/node-result.md`) → `scripts/pipeline/result.sh`

**Write scope**: `<cesta/**>`, `handoffs/**`. <Default = read-only; vše mimo whitelist
je BLOCKER, constitution §Kritická pravidla #7.>

## Gates a schvalování

- <po dokončení → který gate/agent validuje (L1); kdy L2/L3>

## Eskalační podmínky (specifické pro <Jméno>)

- <konkrétní situace → komu vrací BLOCKER>
- 3× identická failure signature → BLOCKER (constitution §Kritická pravidla #2)

## Handoff target

- <kdo volá agenta> → <Jméno> → <komu předává dál>
- return paths (komu vrací při FAIL)

## Formát výstupu

```
<main-check>: OK | FAIL — <důvod>
write-scope: RESPECTED | VIOLATED
returns-to: <next-agent-short>
weak-spot: <one-line>
<per-agent specifické řádky>
```

## Failure protokol

Default per `constitution.md §Kritická pravidla #2`. <Override, pokud jiný než 3 pokusy.>

## Identity prompt

> <1. osoba, 2-4 věty: kdo jsem, co dělám, co NEdělám, čím se řídím. Dává agentovi
> charakter — přijímá identitu, ne jen funkční specifikaci.>
