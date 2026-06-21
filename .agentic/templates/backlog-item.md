---
cache_key: template-backlog-item-v1.0
type: template
---

# Backlog item template

Jeden soubor = jedna jednotka práce čekající ve frontě: `backlog/<slug>.md`.
Kopíruj a vyplň. Hranice vůči ostatním kanálům (Constitution §5):

- **práce, která se má udělat** (feature / fix / chore / refactor / drift) → sem (`backlog/`)
- pouhý **nález / non-blocker poznámka** → `improvements/<category>.md`
- **ops task / stav targetu** → `STATE.md §Open Items` nebo `status/<target>.md`

Po dokončení: `status: done` + odkaz na wave/commit, nebo položku smaž, pokud
stopu nese `STATE.md` / git historie. Žádný ruční index — priorita je ve
frontmatteru (`priority:`), řazení/dedup řeší až `/backlog` skill, pokud vznikne.

```yaml
---
id: <slug>                # = jméno souboru, např. parker-residue-cleanup
type: feature             # feature | fix | chore | refactor | drift
priority: P1              # P0 blocker | P1 vysoká | P2 normální | P3 někdy
status: open              # open | in-progress | done
owner: vision-po          # vstupní agent: feature → vision-po; ostatní → ted/bob/...
source: human             # human | drift-scan | audit | handoff | gate
created: <ISO-8601>
---
```

# <Krátký název položky>

## Problém / cíl
Jeden odstavec: co je špatně nebo co chceme — a **proč** (dopad). Ne řešení.

## Rozsah
Konkrétně co je uvnitř a co ne, ať si to příští session nemusí domýšlet.

**In:**
- <bod>

**Out (vědomě ne teď):**
- <bod>

## Akceptace (DoD)
Ověřitelné body — všechny splněné = položka hotová. Toto čte vstupní agent.

- [ ] <kontrolovatelný výsledek>
- [ ] <…>

## Dotčené oblasti (volitelné)
Soubory / moduly / specs, kterých se to dotkne. Pomáhá odhadu, není závazné.

## Závislosti (volitelné)
- blokuje: `<slug jiné položky>`
- závisí na: `<slug>`

## Poznámky / odkazy (volitelné)
Odkazy na spec, handoff, `improvements/` nález, audit nebo scan report,
ze kterého položka vznikla.
