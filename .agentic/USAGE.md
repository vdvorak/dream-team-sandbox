---
cache_key: agentic-usage-v1.2
type: documentation
---

# Agentic Flow — Usage Guide

Detailní příručka pro tři scénáře nasazení + běžné operace. Pro
overview a quick start viz [README.md](./README.md).

## Obsah

- [Scénář A — Greenfield (nový projekt)](#scénář-a--greenfield-nový-projekt)
- [Scénář B — Transition (existující projekt)](#scénář-b--transition-existující-projekt)
- [Scénář C — Pickup (projekt už agentic používá)](#scénář-c--pickup-projekt-už-agentic-používá)
- [Daily operations](#daily-operations)
- [Tool migrace (Claude Code → Cursor → ...)](#tool-migrace-claude-code--cursor--)
- [Aktualizace template z dream-team repo](#aktualizace-template-z-dream-team-repo)
- [Přidávání nového agenta](#přidávání-nového-agenta)
- [Sunset starých skills / legacy struktur](#sunset-starých-skills--legacy-struktur)
- [Scripts — kdy je používat](#scripts--kdy-je-používat)

---

## Scénář A — Greenfield (nový projekt)

### Rychlá varianta (jeden příkaz)

```bash
bash ~/dev/AI/dream-team/scripts/setup/create-project.sh <název> --claude
# (alias: alias create-project='bash ~/dev/AI/dream-team/scripts/setup/create-project.sh')
```

Udělá Kroky 1–4 najednou (adresář + git, klon `.agentic/`, detach, IDE adaptér, initial
commit). Pak `cd <název> && claude` → řekni **„Chci založit projekt"** (Watson dokončí obsah).
`--cursor` / `--aider` místo `--claude`; `--into <dir>` zvolí parent adresář. Ruční kroky níže:

### Krok 1: Init projektu

```bash
mkdir ~/dev/my-new-project
cd ~/dev/my-new-project
git init
```

### Krok 2: Naklonuj dream-team template

```bash
git clone https://github.com/<your-user>/dream-team .agentic
```

### Krok 3: Odpoj template historii

```bash
bash .agentic/scripts/setup/detach-template.sh
```

Nyní `.agentic/` patří tomuto projektu (žádný submodule).

### Krok 4: Nastav svůj IDE

Vyber jeden:

```bash
bash .agentic/scripts/setup/setup-claude-code.sh   # vytvoří .claude/settings.json + CLAUDE.md
# nebo
bash .agentic/scripts/setup/setup-cursor.sh         # vytvoří .cursorrules
# nebo
bash .agentic/scripts/setup/setup-aider.sh          # vytvoří .aider.conf.yml
```

### Krok 5: Spusť IDE + zavolej Watson

```bash
claude  # nebo cursor . / aider
```

V session řekni:

> **„Začínám nový projekt, zavolej Watson."**

Watson detekuje stav GREENFIELD a provede 6-fázový interview:

1. **Vize a kontext** — co projekt dělá, pro koho, v jakém stádiu
2. **Tech stack** — server lang, klient, DB, hosting, CI
3. **Jazyky a konvence** — spec_language, code_language
4. **Compliance** — regulační rámec, datová citlivost
5. **Active agents** — kteří z 19 jsou pro tvůj projekt relevantní
6. (Skip — fáze 6 je jen pro transition)

Watson vytvoří:
- `project-config.md` — paths + active agents
- `stack/<target>.md` — skeleton (Tony pak vyplní detail)
- `CLAUDE.md` na rootu — bootstrap loader
- `backlog/setup-seed.md` — první feature seed z vize

Pak handoff → **Vision** pro první feature.

---

## Scénář B — Transition (existující projekt)

### Krok 1: Bezpečnostní branch

```bash
cd ~/dev/existing-project
git checkout -b agentic-setup
```

Pokud něco nepůjde, vrátíš se na main.

### Krok 2: Naklonuj template

```bash
git clone https://github.com/<your-user>/dream-team .agentic
bash .agentic/scripts/setup/detach-template.sh
```

### Krok 3: Setup IDE

```bash
bash .agentic/scripts/setup/setup-claude-code.sh
```

**Pozor**: pokud `CLAUDE.md` už existuje a má **non-agentic** obsah,
setup-claude-code skript ho **nepřepíše** — vypíše doporučení, co tam má
přibýt. Můžeš ho přepsat manuálně, nebo dovolit Watson udělat to (L3
souhlas).

### Krok 4: Spusť Watson

```bash
claude
```

> **„Tento projekt přechází na agentic flow, zavolej Watson."**

Watson detekuje TRANSITION:
- Naskenuje codebase (read-only): jaký jazyk, framework, struktura
- Provede 6-fázový interview s **navrhovanými odpověďmi** podle nálezů
- **Fáze 6 (transition only)**: nabídka extrakce implicitních rules z
  existujícího kódu

### Krok 5: Extrakce rules (volitelně)

Watson per oblast nabídne:
- Error handling pattern v server kódu
- Frontend page komponenty struktura
- Logging konvence
- Migration naming pattern
- ...

Pro každou nabídku **schvaluješ** (L2 informativní): Watson ti ukáže
extracted rules markdown, ty řekneš OK nebo skip.

### Krok 6: Handoff → Eywa → Vision

Po dokončení setupu:
- Eywa: audit fit agentů (kteří v cast jsou relevantní pro tvůj projekt)
- Vision: první feature ve novém flow

**Co se ZACHOVÁ**:
- Tvůj existující kód (žádné automatické přepsání)
- Tvoje existing `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`
- Tvoje existing CI/CD (Alfred ji převezme z místa, kde je)

**Co se PŘIDÁ**:
- `.agentic/` (framework)
- `CLAUDE.md` na rootu (pokud neexistoval; jinak L3 dotaz)
- `project-config.md` (mapování existing paths)
- Volitelně `rules/` extrakty (s tvým souhlasem per soubor)

---

## Scénář C — Pickup (projekt už agentic používá)

### Detekce
- `.agentic/` exists ✓
- `project-config.md` exists (a NEMÁ `status: SKELETON_NEEDS_WATSON`) ✓
- `CLAUDE.md` na rootu exists ✓

### Workflow

```bash
cd ~/dev/agentic-project
claude  # nebo cursor . / aider
```

> ⚠️ Pokud session byla otevřená během `setup-claude-code.sh` nebo
> `agentic-sync.sh`, **restartuj** ji (`exit` + `claude`). Subagenty se
> načítají při startu.

**Session start — vždy zavolej Watson:**

> **„Zavolej Watson."**

Watson detekuje stav COMPLETE a spustí **session-resume ritual**:
1. Přečte `STATE.md` (§Aktuální fokus, §Open Items)
2. Najde a přečte poslední handoff v `handoffs/`
3. Prezentuje status report — co se naposled dělalo, co čeká, navrhuje
   next step

Příklad výstupu:
```
project-state: COMPLETE
state-focus: export PDF — v implementaci
open-items: 2
last-wave: 2026-05-28-export-pdf
last-handoff: bob-backend-to-joey (2026-05-28)
wave-status: IN_PROGRESS — čeká na joey-qa
suggested-next: dispatch joey-qa
```

Pak ty rozhoduješ: potvrdíš dispatch, zadáš nový request, nebo jdeš jinam.
Žádný setup — Watson jen orientuje session a mizí.

---

## Daily operations

### Přidat novou feature
> User: „Přidej feature: export commit log do PDF."

Dispatch:
```
Vision → Tony (L1 feasibility) → Ted (contract) →
Chandler? (pokud DB) → Bob (server impl) → Joey (integration tests) →
[paralelně] Optimus / Sheldon / Heimdall / Vitek →
L2 user review → Alfred → staging (L2) → L3 → production
```

### Opravit bug
> User: „Failing test X v CI."

Joey identifikuje failure signature → vrací vlastníkovi (Bob/Peter pro
kód, Ted pro contract, Vision pro spec) → fix → re-run.

### Změnit acceptance criteria
> User: „Změň acceptance pro feature X — bod 3 je špatně."

Vision updatuje `acceptance/x.md` → Joey re-validates testy → opraví
testy → re-run.

### Audit agent systému
> User: „Eywa, projdi agenty — máme overlap?"

Eywa spustí `scripts/agent-graph-check.sh` + sémantická analýza →
findings report.

### Production deploy
> User: „Deploy aktuální vlnu na produkci."

Alfred:
1. Ověří všechny gates (Joey, Optimus, Sheldon, Heimdall, Vitek = PASS)
2. Vytvoří `handoffs/<wave>/L3-deploy.md` s plánem
3. Čeká na tvůj **L3 souhlas** (musíš explicitně potvrdit)
4. Po schválení: deploy
5. Monitor → if fail → auto rollback → return path k viníkovi

### Přidání agenta
> User: „Eywa, navrhni agenta pro internationalization management."

Eywa navrhne strukturu (template, write scope, handoff target, Tools) →
ukáže ti návrh → **L3 user souhlas** → agent přidán + `INDEX.md` update.

---

## Tool migrace (Claude Code → Cursor → ...)

`.agentic/` zůstává **identický** přes nástroje. Jen tool-specific config
se mění.

### Z Claude Code do Cursor

```bash
cd ~/dev/my-project
bash .agentic/scripts/setup/setup-cursor.sh
# Otevři Cursor
cursor .
```

`.claude/` můžeš nechat (nepoužité config files neuškodí), nebo smaž:
```bash
rm -rf .claude
```

### Z Cursor do Aider

```bash
bash .agentic/scripts/setup/setup-aider.sh
aider
```

### Z libovolného do Claude Code

```bash
bash .agentic/scripts/setup/setup-claude-code.sh
claude
```

Agent definice (`.agentic/agents/`) se nemění. Jen dispatch mechanismus
nástroje (Claude Code subagents vs Cursor rules vs Aider read files).

---

## Aktualizace template z dream-team repo

Použij **`scripts/setup/agentic-sync.sh`** — selektivní sync interaktivním
diff prompt módem.

### V dream-team repu:
```bash
cd ~/dev/dream-team
# Edituj soubory, bumpni VERSION pokud breaking
git add .
git commit -m "feature X"
git push
```

### V existujícím projektu:
```bash
cd ~/dev/my-existing-project
bash .agentic/scripts/setup/agentic-sync.sh
```

Script:
- Detekuje dream-team path (`~/dev/dream-team` nebo `~/dev/AI/dream-team`)
- Volitelně pulluje latest (pokud je git checkout)
- Compare local vs template `framework_version`
- Per template-owned soubor → ukáže diff → ptá se Y/n/q
- Aplikuje schválené
- Aktualizuje `framework_version` v `project-config.md`

### Co se SYNCUJE (template-owned)
- `constitution.md`, `flow.md`, `USAGE.md`, `VERSION`
- `agents/*.md`, `agents/INDEX.md` (všechny)
- `templates/*.md`
- `scripts/*.sh`, `scripts/setup/*.sh`, `scripts/pipeline/*.sh`, `scripts/README.md`
- `pipeline/*` (delivery graf + README; v0.19.0+)

### Co se NIKDY NEPŘEPISUJE (per-project)
- `project-config.md` (per-project mapování + active_agents)
- `CLAUDE.md` (per-project bootstrap)
- `stack/<target>.md` (per-project tech volby)
- `rules/` (project-specific patterns)
- `specs/`, `contracts/`, `backlog/`, `improvements/`, `status/`,
  `handoffs/`, `audit/`, `acceptance/`, `design/`

### Batch mode (auto-accept)
```bash
bash .agentic/scripts/setup/agentic-sync.sh --yes
```
**POZOR**: bez per-file review. Hodí se pro CI nebo když víš, že žádné
lokální customizace v template souborech nemáš.

### Po sync — povinné kroky
```bash
bash .agentic/scripts/setup/setup-claude-code.sh   # regen .claude/agents/
# RESTART claude session (Ctrl-D, pak `claude`)
```

> ⚠️ **Bez restartu** Claude Code neuvidí custom subagenty přes
> `subagent_type` — `.claude/agents/` se načítá při startu session, ne
> dynamicky.

---

## Přidávání nového agenta

### Pro aktuální projekt:

```
User: Eywa, navrhni agenta pro <X>.

Eywa: <navrhuje strukturu — jméno, role, write scope, handoff, Tools>
      <ukáže ti návrh agent souboru>

User: <reviewuje, L3 souhlas>

Eywa: <vytvoří .agentic/agents/<short>.md + update INDEX.md + project-config.md>
```

### Aby agent byl i v template (pro nové projekty):

```bash
# Zkopíruj nový agent soubor do dream-team repu:
cp ~/dev/my-project/.agentic/agents/new-agent.md ~/dev/dream-team/agents/

# Update template INDEX.md:
cp ~/dev/my-project/.agentic/agents/INDEX.md ~/dev/dream-team/agents/

cd ~/dev/dream-team
git add .
git commit -m "agent: add <short> (<role>)"
git push
```

---

## Sunset starých skills / legacy struktur

Pokud projekt přechází z existujícího pre-agentic flow (např. Parker má
historicky `skills/` adresář), postupuj takto:

1. Eywa zkontroluje `project-config.md §Skill-to-agent mapping`
2. Pro každý starý skill, který je plně absorbován do agentů:
   - Verifikuj, že žádný agent na starý skill neodkazuje
   - **L3 lidský souhlas** pro smazání (destruktivní)
3. Po smazání zápis do `audit/destructive-ops.md`

---

## Scripts — kdy je používat

Per `constitution.md §Scripted extraction first`: **mechanické úkoly
patří do scriptů**, ne do LLM kontextu.

| Situace | Použij script |
|---|---|
| Potřebuju jeden endpoint z velkého OpenAPI | `scripts/openapi-slice.sh <op>` |
| Potřebuju jednu sekci z rules/stack souboru | `scripts/rules-section.sh <file> <section>` |
| Zjistit délku spec před handoffem | `scripts/spec-length.sh <feature>` |
| Detekovat zakázané line refs v dokumentu | `scripts/find-line-refs.sh <file>` |
| Hash failure signature pro counter | `scripts/failure-hash.sh <check> <type> <loc>` |
| Audit agent definic | `scripts/agent-graph-check.sh` |

### Kdy nepoužívat
- Když potřebuješ skutečné úsudkové rozhodnutí — pak LLM
- Když script neexistuje a vytváříš ho pro one-off — pak grep ad-hoc, ale
  po **2× použití** eskaluj Eywa: „Navrhni script pro X"

### Když script chybí
Reusable pattern (2+ použití) bez scriptu = kandidát na extract per
`constitution.md §Reuse policy E2`. Vrať Eywa.
