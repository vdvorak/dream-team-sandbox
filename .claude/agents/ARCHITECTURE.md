---
name: ARCHITECTURE
description: Agent ARCHITECTURE. Viz .agentic/agents/ARCHITECTURE.md.
tools: Read, Write, Edit, Glob, Grep, Bash
---

# Architektura agentů — slepý I/O kontrakt

Jak je každý agent postavený a proč. Doplňuje `pipeline-architecture.md` (engine grafu) a
`README.md §Jak to vzniká` (lidský náhled flow).

## Princip v jedné větě

**Agent je slepý vůči flow.** Zná jen sám sebe, své vstupy a své výstupy. Neví, kdo ho volá ani
kdo přijde po něm. Routing (kdo komu předává) žije **jen v grafu** (`pipeline/delivery.yaml`) a
vykonává ho endpoint `/done` (`run.sh done` → `result.sh` zapíše výsledek, `next.sh` spočítá
dalšího). Agent o flow **mlčí** — nezmiňuje graf, endpoint, souseda, ani to, že je „slepý".

```
   vstupy ─►  ┌─────────┐  ─► výstup (verdikt + artefakty)
              │  AGENT  │              │
   (typy)     │ kdo jsem │              ▼
              │ co umím  │       /done endpoint  ──► routing dle grafu ──► další agent
              └─────────┘       (result.sh + next.sh)   (delivery.yaml)
        nezná souseda · nezná graf · nezná „kdo je další"
```

Tohle je **příprava na aplikaci**: file-engine (`result.sh`/`next.sh`) je prototyp `/done`
endpointu; agent = uzel s typovanými porty. Viz `PROJECT-CONSTITUTION.md §Vize a mise`
(most souborový engine → aplikace) a `backlog/app-platform.md` (node-editor vize).

## Tvar agent definice (6 sekcí)

```
1. Kdo jsem        identita + lens (charakter)
2. Co umím         co posuzuju / produkuju (plný detail domény — pravidla, scripty, checky)
3. Co NEumím       hranice (bez „→ kdo to dělá místo mě")
4. Vstupy          typy (z artifacts.yaml) + k čemu = porty dovnitř
5. Výstupy         typy + tvar verdiktu + write-scope = porty ven (envelope do /done)
6. Jak soudím      vnitřní logika → jak vyrobím výstup (severity pravidla, kritéria)
```

**Detail zůstává, flow mizí.** Agent si nechá VŠECHNY svoje doménové detaily (jaká pravidla
hledá, jaké scripty pouští, jaká výstupní pole má). Ven jde jen: „Handoff target" / „Gates"
sekce a jakákoli zmínka jiného agenta. Vzor: `agents/joey-qa.md`.

## Verdikt = kompetence (ne uniformní)

Bohatost výstupu odpovídá tomu, co agent ze své role ví:

- 🧪 **Joey** (zkoušeč naslepo) řekne jen `FAIL + signature` (příznak: „GET → 500"). Příčinu nezná.
- 📐 **Ted** (architekt) přidá `fault` = **doménu** vady (`db-schema | contract | server-logic | spec`).
- 🛡️ **Heimdall** (vidí do kódu) přidá konkrétní nález + `severity`.

Diagnóza se tak **vrství**: `Joey "rozbité" → Ted "rozbité kvůli databázi" → …`. Žádný z nich
nejmenuje kolegu — jen popisuje svůj výsledek.

## Agent nejmenuje agenta — jmenuje doménu

Když je potřeba nasměrovat opravu, agent pojmenuje **doménu / artefakt**, ne uzel:
- Ted: `fault: db-schema` → graf přeloží `fault == db-schema` → `chandler` (return hrana).
- Auditor: `finding` = co + KDE (soubor/endpoint) + `severity` → graf routuje dle artefaktu.

Překlad doména→uzel je v grafu (`delivery.yaml`) a v `/done` (`result.sh` resolve). Tím je i
diagnostik slepý vůči flow.

## Výjimka: meta agenti

`eywa-meta` (továrna na agenty), `monk-ideation`, `watson-interviewer` operují **nad** systémem —
smí o něm vědět. Flow-blind pravidlo platí pro **delivery** agenty (uzly v grafu).

## Pojistka: C13

`scripts/pipeline/check.sh` C13 shodí build, když delivery agent obsahuje routing sekci
(„Handoff target" / „Gates a schvalování") nebo jméno/short jiného delivery agenta. Mechanická
prevence regrese — flow se nemůže vrátit do agentů.

## Kdo flow vlastní

| co | kde |
|---|---|
| identita + kompetence + I/O kontrakt agenta | `agents/<short>.md` |
| routing (kdo komu předává), typy portů | `pipeline/delivery.yaml` + `pipeline/artifacts.yaml` |
| vykonání routingu (`/done`) | `scripts/pipeline/{result,next,run}.sh` |
| lidský náhled flow | `README.md §Jak to vzniká` |
| authoring nových agentů dle tohoto tvaru | `agents/eywa-meta.md` |

**Uzel grafu = ROLE, ne osoba.** `delivery.yaml` má uzly pojmenované rolí (`product`,
`backend`, `db-schema`, …); pole `agent:` je **cast binding** — která persona (short) roli plní.
Tím je flow modifikovatelný vizuálním editorem a výměna agenta na roli je změna bindingu, ne
přepojení grafu. Agent zná jen typy artefaktů (nikdy roli souseda) → výměny se nedotkne. To je
přesně to, co dělá „agent nejmenuje agenta" víc než pravidlo: **strukturální vlastnost grafu.**

