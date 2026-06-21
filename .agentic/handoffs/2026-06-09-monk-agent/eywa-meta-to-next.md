---
wave: 2026-06-09-monk-agent
from: eywa-meta
to: orchestrator
type: wave-completed
returns_to: null
timestamp: 2026-06-09
---

# Handoff: Eywa → Orchestrator — nový agent Monk

## Stav (jak chápu situaci)

Uživatel požádal o přidání nového meta-agenta **Monk** (Project Ideation &
Reflection Guide). Role overlap check proběhl — žádný z 19 stávajících agentů
neřeší pre-projektovou ideaci a filozofickou reflexi. Watson je nejbližší, ale
je strukturovaný a task-focused (sbírá fakta pro `project-config.md`); Monk
dělá opak — otevřená meditace dřív než se vůbec rozhodne, co buildovat.

## Co bylo uděláno

- Eywa provedla role overlap audit: nulový overlap se všemi 19 agenty
- Navržena persona: **Kwai Chang Caine** (TV série Kung Fu, 1972) — šaolinský
  mnich, klade otázky místo odpovědí; Adrian Monk zamítnut (OCD/struktura ≠ reflexe)
- `agents/monk-ideation.md` vytvořen (L3 souhlas uživatele)
- `agents/INDEX.md` aktualizován: cast 19→20, řádek v meta-agenti tabulce,
  trigger řádek v "Meta-agenti — kdy je volat"
- Commitnuto jako `v0.16.0`, pushnuto na main

## Výsledek

- `agents/monk-ideation.md` — vytvořen
- `agents/INDEX.md` — upraven (cast count, 2× nový řádek)
- `commit e38adfa` — v0.16.0 na main

## Decided

- **Persona: Kwai Chang Caine** (Kung Fu universe), ne Adrian Monk — důvod:
  Adrian Monk je detektiv s OCD fixací, Caine je archetyp filozofické reflexe
  a zastavení se
- **Model: `sonnet`** — meditace nepotřebuje opus-level reasoning; žádné
  breaking changes, security úsudek ani architektura; sonnet má dostatečnou
  hloubku
- **Transformations: `[meta]`** — mimo T1/T2/T3, stejně jako Eywa a Watson;
  není potřeba nový typ pro framework
- **Write scope: `ideas/**` pouze na explicitní žádost** — Monk je primárně
  konverzační; write scope existuje aby insights nešly pryč, ne aby Monk
  automaticky produkoval dokumenty
- **Trigger frází**: "Pojďme meditovat" / "Pojďme nad tím meditovat" —
  zaregistrovány jako user-triggered vstupní body v Handoff target sekci

## Slabé místo

`ideas/` složka neexistuje v žádném dogfood projektu — Monk ji nesmí
vytvářet sám (L2 souhlas). Pokud uživatel první meditaci chce zapsat,
bude potřeba explicitní potvrzení. Bez rolloutu do dogfood projektů Monk
v nich zatím nemá write scope ani složku.

## Normativní mezera

- **Co chybí**: žádný dogfood projekt nemá `ideas/` v write scope Monka
  (agent tam zatím neexistuje)
- **Kde chybí**: per-project `project-config.md §active_agents`
- **Kdo dodá**: Watson / uživatel při příštím projektu setup nebo on-demand
  aktivaci Monka v daném projektu

## === GATE OUTPUT ===
```
agent: eywa-meta
phase: wave-completed
role-overlap: NONE
write-scope: RESPECTED
monk-added: OK — agents/monk-ideation.md + INDEX.md
index-updated: OK — cast 19→20, meta-agenti tabulka, trigger tabulka
version: v0.16.0 (commit e38adfa, pushed main)
returns-to: orchestrator
weak-spot: ideas/ složka neexistuje v dogfood projektech; aktivace Monka per-projekt čeká
```
==================
