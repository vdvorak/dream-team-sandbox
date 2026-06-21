# dream-team

**Agentic development flow** — parta 20 pojmenovaných AI agentů (každý z nějakého
filmu/seriálu), kde každý má **jeden úkol**. Společně vezmou nápad a dotáhnou ho až
k hotové, ověřené funkční věci — **spec je pravda, kód je artefakt**.

Tool-agnostic (Claude Code / Cursor / Aider / Claude API), file-based handoffy,
transparentní gates s lidským souhlasem u destruktivních operací, **brevity-first specs**,
**scripted extraction** místo plýtvání LLM tokeny na mechanické úkoly, a **subagent
isolation** (každý agent běží v izolovaném kontextu — žádná kontaminace mezi agenty).

**Routing dělá kód, ne LLM:** agent dodá jen výsledek a úsudek; *kam to jde dál* je
v grafu (`pipeline/delivery.yaml`), spočítá to deterministický engine — pokaždé stejně.

> 📖 **Ztrácíš se v dokumentech?** → [🗺️ Mapa dokumentů](#-mapa-dokumentů) níže říká, který soubor je co.
> **Aktuální verze**: [VERSION](./VERSION) · **Kam to celé míří**: [PROJECT-CONSTITUTION.md §Vize a mise](./PROJECT-CONSTITUTION.md) (north-star).

---

## Obsah

- [Jak to vzniká](#jak-to-vzniká) — cesta nápadu od myšlenky k hotovu
- [Tým (20 agentů)](#tým-20-agentů) — kdo je kdo, každý jeden úkol
- [Dvě pravidla](#dvě-pravidla-která-drží-tým-pohromadě) · [Co mění cestu](#co-mění-cestu) · [Kde rozhoduješ ty](#kde-rozhoduješ-ty)
- [Quick start](#quick-start) (greenfield / transition / pickup)
- [První session — příklad](#první-session--příklad)
- [Daily workflow](#daily-workflow)
- [🗺️ Mapa dokumentů](#-mapa-dokumentů)
- [Framework vs projekt](#framework-vs-projekt) (dvě vrstvy)
- [Aktualizace template](#aktualizace-template) · [FAQ](#faq) · [Inspirace](#inspirace)

---

## Jak to vzniká

```
                       💡  Nápad / požadavek
                            │
                     ┌──────▼──────┐
                     │   TŘÍDĚNÍ     │   Co to je?
                     └──────┬──────┘    nová věc · oprava · vylepšení
                            │
 ════════════════  1 ·  N Á V R H  ════════════════════════════════
                            │
                     🦸  Vision        napíše, CO se má udělat a PROČ
                            │
                     🔧  Tony          „Jde to vůbec? Jak je to velké?"
                            │                       │
                            │ ano                   └─✗─► zpátky k Visionu
 ════════════════  2 ·  S T A V B A  ══════════════════════════════
                            │
                     📐  Ted           vymyslí, jak to poskládat
                            │           (pravidla, jak spolu části mluví)
              ┌─────────────┼──────────────────┐
        🗄️  Chandler    🧱  Bob          🕸️  Peter / Mob / Winny
        databáze         „mozek"          to, co uživatel vidí
        (když třeba)     (server)         (web / mobil / počítač)
              └─────────────┼──────────────────┘
                            │
 ════════════════  3 ·  K O N T R O L A  ══════════════════════════
                            │
                     🧪  Joey          vyzkouší, jestli to fakt funguje
                            │                       │
                            │ funguje               └─✗─► 📐 Ted určí, kdo to opraví
                            │
        pětice kontrolorů, každý kouká z jednoho úhlu:
        ⚡ rychlost   📋 zadání   🛡️ bezpečnost   ✅ kvalita   👗 vzhled
                            │                       │
                            │ všechno OK            └─✗─► zpátky autorovi
                            │
                     👤  Ty se podíváš na hotovou věc
                            │
 ════════════════  4 ·  N A S A Z E N Í   (jen když se nasazuje)  ══
                            │
            🚀 Alfred připraví  →  👤 ty schválíš  →  spuštěno  🎉
```

Co se pro daný úkol nehodí, se **přeskočí** (viz [Co mění cestu](#co-mění-cestu)) — nikoho to nezdrží.

---

## Tým (20 agentů)

Standardní flow: **T1** (Idea→Spec) · **T2** (Spec→Code) · **T3** (Code→Ověření) · **T3-post** (Deploy).
Každý má jeden úkol a nesahá do cizího.

**Návrh (T1)**
- 🦸 **Vision** (Product Owner) — řekne **co** se má udělat a proč; píše feature specs, acceptance criteria, scope.
- 🔧 **Tony Stark** (CTO) — řekne, **jestli to jde a jak je to velké**; tech strategy, volba stacku.
- 🎨 **Denisa** (UX) — když to má obrazovku, **nakreslí** statické HTML mockupy + user flow (cross-platform).

**Stavba (T2)**
- 📐 **Ted Mosby** (Architect) — rozhodne, **jak to poskládat**: API kontrakty, rules patterny.
- 🗄️ **Chandler Bing** (DB) — když je potřeba, **schema + migrace**.
- 🧱 **Bob the Builder** (Backend) — postaví **server** („mozek") + unit testy.
- 🕸️ **Peter Parker / Mob / Winny** — postaví, **co uživatel vidí**: web / mobil (iOS+Android) / desktop (Win/macOS/Linux) + unit testy.
- 🧰 **Leonard Hofstadter** (UI) — připraví **vzhledové stavební kostky** (design manuál + komponenty) pro tu trojici.

**Kontrola (T3)** — *nic nespraví; když najdou chybu, pošlou zpátky autorovi*
- 🧪 **Joey Tribbiani** (QA) — vyzkouší, že věc dělá, co má podle zadání (integration/system testy).
- ⚡ **Optimus Prime** (Performance) · 📋 **Sheldon Cooper** (Spec) · 🛡️ **Heimdall** (Security, F1–F8) · ✅ **Vitek** (Code Quality) · 👗 **Edna Mode** (Design conformance) — read-only auditoři, paralelně.

**Nasazení (T3-post)**
- 🚀 **Alfred Pennyworth** (DevOps) — CI/CD, deploy, rollback.

**Meta (mimo standardní flow)**
- 🧬 **Eywa** (Agent Architect) — přidává/audituje agenty.
- 🕵️ **John Watson** (Setup Interviewer) — bootstrap nových projektů (vize → setup).
- 🧘 **Monk** (Ideation & Reflection) — na vyžádání („pojďme meditovat"): zpochybní *proč* to stavíš, nebo reflektuje běžící projekt proti původní vizi. Mimo T1/T2/T3.

---

## Dvě pravidla, která drží tým pohromadě

> **1) Každou věc dělá jen jeden člověk.** Ted nesahá na databázi, Bob nepíše pravidla,
> Chandler jediný dělá databázi. Nikdo nelje do cizího (write scope per role).

> **2) Kontroloři a tester nikdy nic neopravují — pošlou to dál.** Kontroloři (rychlost,
> bezpečnost, …) se dívají **přímo do věci**, takže vědí, čí to je, a vrátí to rovnou
> autorovi. 🧪 **Joey** ale zkouší hotový celek **naslepo** — vidí, že něco nefunguje,
> ale ne *proč*. Proto jeho nález jde k 📐 **Tedovi** (architekt se v tom vyzná), a ten
> určí, kdo to opraví. Joey sám nehádá a nic nespraví.

Tahle slepota je záměr: agent zná jen své vstupy/výstupy a jak soudí — **neví, že je ve
flow** (nezmiňuje graf, souseda, endpoint). Routing žije jen v grafu. Vynuceno check C13.

## Co mění cestu

Podle pár otázek se některé části zapnou nebo přeskočí (engine to gatuje přes flagy/targety):

- 🖥️ **Má to obrazovku?** → Denisa, Leonard a kontrola vzhledu (Edna).
- 🗄️ **Sahá to na databázi?** → Chandler.
- 🌐 **Web, mobil, nebo počítač?** → podle toho Peter / Mob / Winny.
- 🚀 **Bude se to nasazovat?** → na konci Alfred + tvoje schválení.

## Kde rozhoduješ ty

Tým jede sám, ale schvalovací úrovně určují, kdy se čeká na člověka:

| Úroveň | Kdo | Kdy |
|---|---|---|
| **L0 — Auto** | žádný | implementační kroky uvnitř scope |
| **L1 — Inter-agent gate** | druhý AI agent | po každé transformaci (Tony schvaluje Vision spec, Joey schvaluje Bob/Peter implementaci, …) |
| **L2 — Informativní** | ty (jen vidíš) | velký commit, finální handoff vlny, staging deploy |
| **L3 — Lidský souhlas (blokuje)** | ty (musíš říct ano) | destruktivní operace, breaking contract changes, production deploy, přidání/smazání agenta |

**L3 nikdy nemůže potvrdit AI agent za tebe.** Prakticky tě tým potřebuje na dvou místech:
po kontrole (mrkneš na hotovou věc — nezdržuje) a před nasazením (nic se nevypustí bez tvého „ano").

---

## Quick start

### Nový projekt (greenfield)

```bash
mkdir ~/dev/my-new-project && cd ~/dev/my-new-project && git init
git clone https://github.com/<your-user>/dream-team .agentic   # framework jako .agentic/
bash .agentic/scripts/setup/detach-template.sh                 # odpoj template historii
bash .agentic/scripts/setup/setup-claude-code.sh               # nebo setup-cursor.sh / setup-aider.sh
claude                                                          # nebo cursor . / aider
```

V session řekni: **„Zavolej Watson — dokončit setup."** Setup script už vytvořil skeleton
`project-config.md` (s TODO markery) + `CLAUDE.md`. Watson v interview refinuje skeleton
(vize / stack / jazyky / compliance / active agents) a vytvoří první seed v `backlog/`.
Pak předá Vision pro první feature.

> ⚠️ **RESTART SESSION**: `.claude/agents/` se načítá při **startu** Claude Code session,
> ne dynamicky. Pokud jsi měl session otevřenou PŘED `setup-claude-code.sh`, **zavři a
> spusť znovu** (`claude`) — jinak Claude Code neuvidí custom subagenty (`vision-po`,
> `watson-interviewer`, …) přes `subagent_type`.

### Existující projekt (transition)

```bash
cd ~/dev/existing-project
git checkout -b agentic-setup                                  # bezpečnost — můžeš se vrátit
git clone https://github.com/<your-user>/dream-team .agentic
bash .agentic/scripts/setup/detach-template.sh
bash .agentic/scripts/setup/setup-claude-code.sh
claude
```

V session: **„Tento projekt přechází na agentic flow, zavolej Watson."** Watson
**proskenuje codebase** (read-only), navrhne mapování existing paths na agentic strukturu,
volitelně extrahuje implicitní rules z kódu. **Žádný existing kód se neztrácí** — Watson
přidává `.agentic/`, mapuje přes `project-config.md`, žádné automatické přepsání.

### Projekt už agentic používá (pickup)

```bash
cd ~/dev/existing-agentic-project && claude
```

`CLAUDE.md` se načte automaticky, agenti jsou připraveni. Žádné setup kroky — rovnou zadávej requesty.

> Plné scénáře krok-za-krokem (vč. tool-migrace, sunset legacy struktur, daily ops) jsou
> v provozním runbooku **[USAGE.md](./USAGE.md)**.

---

## První session — příklad

### Greenfield

```
User: Začínám nový projekt — CLI nástroj pro analýzu Git commit historie. Zavolej Watson.

Watson: Detekoval jsem stav: GREENFIELD. Provedu 6-fázový setup interview.
        FÁZE 1 — Vize:  Co projekt dělá (1–2 věty)? Pro koho? V jakém stádiu?
User:   CLI tool, hledá patterns autorství v commitech. Interní, pro tým. PoC.
Watson: FÁZE 2 — Tech stack:  Server? DB? Hosting?
User:   Python CLI, žádná DB, distribuce přes pip.
Watson: FÁZE 5 — Active agents:  Navrhuji vyřadit Peter/Leonard/Denisa (bez UI),
        Chandler (bez DB). Aktivní: Vision, Tony, Ted, Bob (Python), Joey, Optimus,
        Sheldon, Vitek, Heimdall, Alfred (pip release), Eywa, Watson. OK?
User:   OK.
Watson: Vytvářím project-config.md, stack/python-cli.md, CLAUDE.md, backlog/setup-seed.md.
        Setup hotov. Předávám Vision s prvním seedem.
Vision: Mám seed "CLI pro analýzu commit history". Jaký pattern hledáš? První MVP feature?
        ...
```

### Transition

```
User: Mám Python Flask projekt, chci ho přepojit na agentic. Zavolej Watson.

Watson: Stav: TRANSITION. Skenuji codebase...
        Nalezeno: Python 3.11+Flask (server/), PostgreSQL (alembic), React (web/),
        GitHub Actions, existing README.md + ARCHITECTURE.md.
        Navrhuji mapování v project-config.md (rules/ → Ted vyplní; stack/ skeletony;
        specs/ prázdné). Otázky: existují acceptance criteria? CONTRIBUTING? Extrahovat
        implicitní rules z kódu?
User:   Acceptance ne, CONTRIBUTING mám, extrakci ano — ale zeptej se před každým souborem.
Watson: FÁZE 6 — extrakce rules (transition only): našel jsem 4 oblasti s konvencemi
        (error handling, frontend komponenty, logging, migration naming). Které extrahovat?
User:   1, 2, 3 ano; 4 ne.
Watson: Extrahuji a ukazuji každý generated soubor (L2 review). Setup hotov.
        Předávám Eywa (audit agent fit), pak Vision.
```

---

## Daily workflow

```
Přidat feature:  „Přidej feature: export commit log do PDF."
  → Vision spec → Tony feasibility → Ted contract → Chandler/Bob/Peter impl →
    Joey testy → Sheldon/Heimdall/Vitek/Optimus audit → L2 review → Alfred deploy (L3 produkce)

Opravit bug:     „Failing test test_export_pdf v CI."
  → Joey identifikuje failure signature → vrací vlastníkovi kódu (Bob/Peter) → fix → Joey re-run

Přidat agenta:   „Eywa, navrhni agenta pro i18n management."
  → Eywa navrhne strukturu (role, write scope, handoff, Tools) → L3 souhlas → přidán + INDEX update

Audit agent systému: „Eywa, projdi agenty — máme overlap?"
  → Eywa spustí agent-graph-check + sémantická analýza → findings (žádný write-scope conflict, žádný dead-end)

Production deploy: „Deploy aktuální vlnu na produkci."
  → Alfred ověří gates (Joey/Optimus/Sheldon/Heimdall/Vitek PASS) → L3 souhlas s plánem →
    schválíš → deploy → monitor → if fail: auto rollback + return path
```

---

## 🗺️ Mapa dokumentů

Dokumenty mají **dvě vrstvy** podle funkce. (V *generovaném projektu* TOOL vrstva žije pod
`.agentic/`, PRODUCT vrstva v rootu. Tady v dream-team repu je TOOL vrstva na rootu, protože
**tenhle repo JE zdroj `.agentic/`** — viz [Framework vs projekt](#framework-vs-projekt).)

**🔧 TOOL — framework jako nástroj** (jak to funguje; v projektu pod `.agentic/`)

| dokument | co je |
|---|---|
| [constitution.md](./constitution.md) | **Zákon** — principy + hard gates + standardy kódu, které agenti i engine poslouchají |
| [flow.md](./flow.md) | Mechanika dispatchu a transformací (detailní popis flow) |
| [pipeline-architecture.md](./pipeline-architecture.md) · [frontier-scheduler.md](./frontier-scheduler.md) | Engine jako deklarativní stavový graf / dataflow scheduler |
| [init-determinism.md](./init-determinism.md) | Proč stejný vstup = byte-identický výstup |
| [USAGE.md](./USAGE.md) | **Provozní runbook** — scénáře krok-za-krokem, daily ops, přidání agenta, tool-migrace |
| `agents/` | Definice 20 rolí (slepé I/O kontrakty) + `INDEX.md` |
| `pipeline/` | Registry: `delivery.yaml` (graf), `artifacts.yaml` (typy), `vocabulary.yaml` (slovník), `interactions.yaml` (gaty) |
| `scripts/pipeline/core/` | Engine (Python) — viz `core/README.md` |
| `templates/` | Scaffoldy / features / stacks (materiál pro generování) |

**🎯 PRODUCT — framework jako produkt** (co stavíme a kde teď jsme; v projektu v rootu)

| dokument | co je |
|---|---|
| [PROJECT-CONSTITUTION.md](./PROJECT-CONSTITUTION.md) | **Vize / north-star + ústava** — §Vize a mise, hodnoty, invarianty I1–I8. *„Kam to celé míří."* |
| [STATE.md](./STATE.md) | **Živý stav** — aktuální fokus, open items (co se právě dělá) |
| `backlog/` | Future práce — node-editor platforma, self-host gaps |
| README.md | tenhle front door |
| `handoffs/` | Historie rozhodnutí per vlna |

*(`value-streams.md` = forward-looking design note. Vize žije v `PROJECT-CONSTITUTION.md
§Vize a mise` — kanonický kondenzát; dřívější samostatný `VISION.md` byl do něj sloučen.)*

---

## Framework vs projekt

**Klíčový princip: `.agentic/` obsahuje POUZE framework — nic projekt-specifického.** Vše
projektové žije v **rootu projektu**. Díky tomu je `.agentic/` celé syncovatelné/nahraditelné
bez rizika ztráty projektových dat.

```
dream-team/                    project-root/ (po setupu)
  = obsah .agentic/ po klonu     ├── .agentic/   ← framework (clone, synced, read-only)
  ├── constitution.md            ├── CLAUDE.md               bootstrap loader
  ├── flow.md                    ├── PROJECT-CONSTITUTION.md projektová ústava (vč. §Vize a mise)
  ├── USAGE.md                   ├── project-config.md       cesty, active agents, version
  ├── agents/                    ├── specs/  contracts/  rules/  stack/
  ├── pipeline/                  ├── backlog/  acceptance/  design/  status/
  ├── rules/  (universal)        ├── handoffs/   audit/
  ├── templates/                 └── server/  clients/  ...  (app kód)
  └── scripts/
```

**Dvě ústavy:** `.agentic/constitution.md` (universal, framework, synced) vs
`PROJECT-CONSTITUTION.md` (projekt-specifická, root, vlastní Vision/Tony/Ted — opening je `§Vize a mise`).

**Dvě vrstvy rules:** `.agentic/rules/<file>.md` (universal base: `backend`, `frontend`,
`logging`, `error-responses`) ← agent čte první; pak `rules/<file>.md` (projektový overlay,
přepisuje kde konfliktuje). Kódové standardy (typy, enums, error handling) jsou v
`constitution.md §Standardy kódu`. Pokud projekt nemá odchylky, `rules/` stub jen odkazuje na universal.

**Co Watson vytvoří/seeduje při setupu** (vše root): `PROJECT-CONSTITUTION.md`,
`project-config.md`, `CLAUDE.md`, skeleton `stack/<target>.md`, seed `backlog/setup-seed.md`,
stub `rules/<target>.md`.

---

## Aktualizace template

Když uděláš zlepšení v dream-team (nový agent, scripty, fixes): edituj, bumpni `VERSION`,
commit + push. V existujících projektech pak:

```bash
cd ~/dev/my-existing-project
bash .agentic/scripts/setup/agentic-sync.sh        # selektivní: ukáže diff, ptá se yes/no
# bash .agentic/scripts/setup/agentic-sync.sh --yes  # batch (POZOR: bez review)
```

Script detekuje cestu k dream-team, pro každý template-owned soubor ukáže diff a zeptá se,
**nikdy nepřepíše** `project-config.md` / `CLAUDE.md` / `stack/` / `specs/` / `contracts/`,
a aktualizuje `framework_version`. Po sync: `setup-claude-code.sh` (regen `.claude/agents/`) + **RESTART session**.

---

## FAQ

**Můžu si agenty přejmenovat?** Ano, ale rozhodne to Eywa (L3). Konvence: `<jmeno>-<role>`. Smaž starý alias.

**Můžu některé agenty vypnout?** Ano — `project-config.md §active_roles`. Inactive role se nedispatchují. CLI projekt typicky vypne Peter/Leonard/Denisa.

**Specs v angličtině místo češtiny?** `project-config.md §spec_language: en`. Vision pak píše anglicky.

**Můžu agenta nahradit sebou (user-as-agent)?** Ano. Před každým agent invokem můžeš říct „tuhle roli teď hraju já, tady je výstup". Šetří token, když znáš odpověď.

**Spec je moc dlouhá, Sheldon ji vrací jako BLOCKER (>400 ř).** Tlačí tě k rozdělení — napiš briefší, nebo rozděl feature. Pokud je objektivně komplexní, opodstatni v hlavičce specu (`note:`).

**Můžu Eywa říct, ať přidá agenta, bez schválení?** Ne. Eywa NAVRHNE strukturu, ty musíš explicitně schválit (L3).

**Jak migruju z jednoho nástroje na druhý (Claude Code → Cursor)?** `.agentic/` zůstává stejné. Spusť `setup-cursor.sh` v projektu. `.claude/` můžeš nechat.

**Co když script neexistuje pro pattern, co dělám opakovaně?** Po 2× → eskaluj Eywa: „Navrhni script pro X". Po L3 souhlasu script vznikne.

**Jak vím, kteří handoffy proběhly?** `handoffs/<wave-id>/*.md`.

---

## Inspirace

Cast míchá multi-universe: **Marvel** (Vision, Tony, Peter, Heimdall), **HIMYM** (Ted),
**Friends** (Chandler, Joey), **TBBT** (Sheldon, Leonard), **Bob the Builder** (Bob),
**Transformers** (Optimus), **Avatar** (Eywa), **DC** (Alfred), **Sherlock Holmes** (Watson),
**Incredibles** (Edna), **Kung Fu** (Monk) + **nicknames** (Mob, Winny) + **osobní jména** (Denisa, Vitek).

Každý agent má **Identity prompt** — krátkou sebepojmenovací větu, která mu v session dává
charakter. Smysl: agent přijímá identitu, ne jen funkční specifikaci. Hraje roli.

---

*Technický detail: přesná pravidla flow jsou ve [`flow.md`](./flow.md), role v `agents/`,
a celé to řídí deterministický engine v `scripts/pipeline/` — pokaždé stejně, bez náhody.*
