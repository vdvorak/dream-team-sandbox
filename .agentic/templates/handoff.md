---
cache_key: template-handoff-v1.0
type: template
---

# Handoff template

Šablona pro standardní handoff dokument mezi agenty. Kopíruj a vyplň.

> Po zápisu handoffu přepiš pointer `handoffs/LATEST` na relativní cestu
> tohoto souboru — session-resume z něj deterministicky čte poslední handoff
> (nikdy podle mtime/názvu složky). Viz `agents/watson-interviewer.md`.

```yaml
---
wave: <wave-id>           # např. 2026-05-27-export-pdf
from: <agent-short>       # např. vision-po
to: <agent-short>         # např. tony-cto
type: spec-completed      # spec-completed | tech-feasibility-ok | contract-completed
                          # | impl-completed | tests-completed | audit-completed
returns_to: null          # nebo agent-short pokud vracíš BLOCKER nazpět
timestamp: <ISO-8601>
---
```

# Handoff: <From name> → <To name>

## Stav (jak chápu situaci)
Jeden odstavec: co je vstup, jaký je kontext, co jsem dostal od předchozího
agenta. Tady neopakuj rozhodnutí výše — jen popis situace.

## Plán (co dělám / udělal jsem)
Konkrétní seznam kroků, které jsi provedl. Stručně.

## Výsledek
Co se změnilo (soubory + sekce). Co prošlo gate. Co stále čeká.

- `<file/path.md>` — (vytvořen | upraven | smazán)
- `<check name>` — OK | FAIL
- ...

## Decided (rozhodnutí, která následný agent NEOPAKUJE)
Explicitní výpis architektonických / business rozhodnutí, která jsi udělal
a která následný agent nesmí přehlasovat (jen implementuje nebo eskaluje
BLOCKER s konkrétním důvodem):

- `<rozhodnutí 1>` — důvod / opora v rules/stack/spec
- `<rozhodnutí 2>` — důvod
- ...

## Slabé místo (POVINNÉ)
Kde si nejsi jistý. Pokud žádné, napiš "bez slabin (zkontrolováno X, Y)" —
prázdné Slabé místo je signál overconfidence. Akční slabé místo se musí
zapsat do `STATE.md §Open Items` nebo `improvements/`.

## Normativní mezera (volitelné)
Pokud jsi narazil na rozhodnutí bez opory v rules/stack/spec:
- **Co chybí**: <konkrétní pravidlo>
- **Kde chybí**: <file:section>
- **Kdo dodá**: <agent-name>

## === GATE OUTPUT === (strojový envelope pro `run.sh done`; schéma: `templates/node-result.md`)
Most handoff→envelope je deterministický (F3): graf doplní `agent` / `phase` / output typy.
Tady dodáš jen **JUDGMENT** — outcome + co se změnilo + slabé místo. **NEjmenuj souseda**
(routing žije v grafu; zůstáváš slepý vůči flow). `returns_to` odvodí engine (`fault`→uzel /
single-return).
```
outcome: PASS | FAIL          # OK→PASS, vada→FAIL
changed: [<typy>] | none      # co se reálně změnilo (re-flow scoping); vynech = všechny outputy
write-scope: RESPECTED | VIOLATED
weak-spot: <one-line z výše>  # u FAIL → signature (co konkrétně opravit)
# jen když relevantní pro roli (judgment):
severity: blocking | advisory # gate FAIL: blokuje re-flow vs jen zaznamenej pro člověka
fault: db-schema|contract|server-logic|spec   # diagnostik (Ted): doména vady
flags: { has_ui: false, touches_db: false }   # spec/feature flagy (Vision / Ted)
```
==================
