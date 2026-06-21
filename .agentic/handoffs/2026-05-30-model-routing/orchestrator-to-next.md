---
wave: 2026-05-30-model-routing
from: orchestrator
to: orchestrator
type: wave-completed
returns_to: null
timestamp: 2026-05-30
---

# Handoff: Model routing wave — session summary

## Stav (jak chápu situaci)

Wave `2026-05-30-model-routing` uzavřena. Framework přešel z v0.13.0 na
**v0.15.0** ve dvou commitech. Všech 6 dogfood projektů synchronizováno,
commitnuto a pushnuto.

## Co bylo uděláno

### v0.14.0 — per-agent model tiery (statická osa)
- `agents/*.md` (19×): `model:` ve frontmatteru — `opus` = tony/ted/heimdall/eywa;
  `sonnet` = zbylých 15. Cache_key bumpy.
- `agents/INDEX.md §Model strategy`: přehledová tabulka tierů.
- `constitution.md §Filozofie #6 Right-sized model`: princip.
- `flow.md §Model routing`: rubrika XS/S/M/L, signály složitosti.
- `agents/tony-cto.md`: complexity triage + výstupní řádky.
- `scripts/setup/setup-claude-code.sh`: propaguje `model:` do `.claude/agents/` wrapperů.

### v0.15.0 — dynamická osa + měření + bezpečnost
**Ověřeno:** Claude Code 2.1.158 Task/Agent tool má parametr `model` (přebíjí
frontmatter) → per-úkol override reálně funguje (nedokumentované, ale funkční).

- `flow.md §Model routing`: per-nástroj override mechanismus (Claude Code =
  `Agent(subagent_type=..., model="haiku", ...)`); bezpečná eskalace (fail →
  tier +1 před BLOCKER); haiku use-cases; měření.
- `constitution.md §Kritická pravidla #2`: model-tier eskalace o stupeň před BLOCKER.
- `scripts/model-usage.sh`: agreguje `status/model-routing-log.md`.
- `scripts/complexity-estimate.sh`: levný prior tieru z diffu.
- `templates/work-breakdown.md`: dekompozice L → S/M podúkoly.
- `templates/gate-output.md`: opraven (byl korumpovaný — 4790 ř. separátorů → 18 ř.).
- `scripts/setup/setup-claude-code.sh`: CLAUDE.md šablona dostala sekci
  „Model routing při dispatchu".
- Pozn.: `agentic-sync.sh` se crashuje při `--yes` protože se sám přepisuje
  (self-replacement crash na syntax error line 226). Obsah se přesto správně
  zkopíruje — jen `framework_version` a sync-log se nezapíšou. Workaround:
  po `--yes` syncu ručně spustit `setup-claude-code.sh` a opravit
  `framework_version` sedem. **Bug otevřen jako Open Item.**

### Rollout do 6 projektů
murio, Parker2, UnagyDev, Vdoklad, Trabajario, pneukarnik:
- `agentic-sync.sh --yes` + fix `framework_version` → 0.15.0 + `setup-claude-code.sh`
- `CLAUDE.md` doplněna sekce Model routing při dispatchu
- Commitnuto + pushnuto do všech 6 remote repozitářů

## Decided

- `haiku` není default žádné persony (mechanická práce = skripty); je cíl downgrade.
- Dynamický override: orchestrátor předá `model=` Task toolu; bez `model=` se
  bere frontmatter default.
- `setup-claude-code.sh` existující `CLAUDE.md` nepatchuje automaticky —
  je to per-project owned soubor; nové projekty dostávají sekci z šablony.
  Existující projekty dostaly sekci jednorázově (tato session).

## Slabé místo

`agentic-sync.sh --yes` self-replacement crash — bug. Dokud není opraven,
manuální workaround po každém `--yes` syncu.

## === GATE OUTPUT ===
```
agent: orchestrator
phase: wave-completed
wave-delivered: v0.14.0 + v0.15.0
projects-synced: 6/6 (murio Parker2 UnagyDev Vdoklad Trabajario pneukarnik)
write-scope: RESPECTED
returns-to: orchestrator
weak-spot: agentic-sync.sh self-replacement crash při --yes
```
==================
