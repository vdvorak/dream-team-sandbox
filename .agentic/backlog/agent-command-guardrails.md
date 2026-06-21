# Backlog: Agent command guardrails — vynucené omezení destruktivních příkazů

**Třída:** improvement (framework / hardening) · **Stav:** SCHVÁLENO ŠIRŠÍ (L3, 2026-06-20) — design-only, čeká rollout · **Priorita:** vysoká (zachycený reálný incident)

> Autor návrhu: Eywa (meta). DESIGN-ONLY — nic živého nezavedeno. Žádná změna `settings.json`,
> wrapperů, `core/run.py` ani FS práv neproběhla. Tento dokument je schválený k posouzení
> rolloutu (L3), protože mění fundament toho, co agenti smí spouštět a kam smí psát
> (dotýká se `constitution.md §7 write-scope` a `§8 destruktivní operace`).

> **REVIZE 2026-06-20 — L3 verdikt: SCHVÁLENO, ale ŠIRŠÍ.** PO (Vitek) posunul těžiště návrhu.
> Původní v1 stála na CLI-tool hooku (PreToolUse) jako primární vynucovací lince. **To je obráceno:**
>
> **JÁDRO (nový princip, ne detail):** Do stavu workflow enginu nesmí sahat **ŽÁDNÝ agent**.
> Vynucení musí být součást **ENGINU a souborového systému**, ne spoléhat na paměť/chování
> Claude Code ani jiného CLI toolu. CLI-tool-level mechanismus (hook) je **nanejvýš redundantní
> pojistka**, ne primární linie. Plyne to z `constitution.md §8` axiomu „orchestrátor řídí přes
> rozhraní, ne přes vnitřek" — když je vynucení v toolu, vynucení JE ten vnitřek toolu; když je
> v enginu/FS, je v rozhraní. Pivot na container-platformu (`backlog/INITIATIVE-container-platform.md`)
> dává tomuto principu reálnou půdu: engine i projektové soubory běží **uvnitř kontejneru**, takže
> write-protection enginových cest lze vynutit **filesystémově** (read-only mount, OS práva), ne
> pattern-matchem nad shell stringem.

---

## 1. Incident (proč to řešíme)

Vlna `remove-db-layer`, 2026-06-19. Subagent `bob-backend` spustil `git stash` při ověřování
test-baseline. Pipeline jede **commit-on-done**, takže celá rozdělaná vlna byla necommitnutá ve
working tree. `git stash` odložil mimo jiné:

- `current-run.md` — **stav workflow enginu** (git-tracked v rootu),
- `contracts/error-codes.md` — kontraktovou sekci, kterou těsně předtím editoval Ted,

a `pop` je nevrátil čistě. Stav enginu spadl zpět na starou vlnu, Tedova sekce zmizela.
Zachytil to až spec-audit; oprava byla ruční replay `done`-envelope z ledgeru.

**Třída chyby = OMYL kooperativního agenta**, ne sabotáž. Bob nechtěl škodit — jen sáhl po
běžném git nástroji v kontextu, kde je toxický (commit-on-done + tracked engine stav).
To je klíčové pro volbu allowlist vs denylist (viz §3).

Dnešní jediná mitigace = ad-hoc prompt-varování → **křehké a nevynucené**. V promptu navíc
zákaz `git stash` dnes ani není; `constitution.md §8` mluví o destrukci dat/DB, agent v omylu
si pod to `git stash` nepodřadí.

---

## 2. Co repo ukazuje (ověřený stav, ne domněnka)

| Zjištění | Důsledek pro návrh |
|---|---|
| `current-run.md` (root) je **git-tracked** (`git ls-files` → TRACKED) | proto ho `git stash` odloží; stav enginu žije ve working tree |
| `runs/` je tracked taky | ledger je ve working tree — stejně zranitelný |
| `.claude/settings.json` má jen `permissions.allow`, žádný `deny`, žádné `hooks` | denylist ani hook dnes neexistuje |
| `.claude/settings.local.json` (gitignored, osobní) má `Bash(git *)` v allow | široký glob — `git stash` projde bez ptaní |
| `tools:` (`Read, Write, Edit, Glob, Grep, Bash`) je **hardcoded v `setup-claude-code.sh`**, NE v `.agentic/agents/*.md` | neutrální zdroj `tools:` nedeklaruje → politika dnes nežije v `.agentic/` |
| `.agentic/agents/*.md` (neutrální zdroj) `tools:` neobsahují vůbec | nutno doplnit, aby zdroj pravdy seděl v `.agentic/` |
| Generátor zapisuje `settings.json` jen `if [[ ! -f ]]` (jinak skip) | dnes by `deny`/`hooks` blok nikdy nedoplnil — generátor je třeba upravit |
| `core/run.py` má subcommandy `start/active/skip/resolve-loop/drive/status/next/done/summary/check/scaffold` — **NE `repair`** | rekonstrukce stavu z ledgeru je dnes ruční (`start` + replay `done`) |
| Existuje memory „Engine writes STATE on terminal" — engine na `done` zapisuje strojový blok do `STATE.md` (FIFO) | ledger + STATE blok jsou existující zdroje pro rekonstrukci |
| `core/run.py` dnes **nedělá `git commit`** — jen `git rev-parse HEAD` (wave_base provenance, fail-soft). „Commit-on-done" dnes fakticky znamená *commit dělá orchestrátorská session ručně po `done`* | „commit ownership → engine" je **NOVÁ engine schopnost**, ne jen denylist toggle — viz §3a, §7 |
| `common.run_root()` ukotvuje engine stav na **umístění skriptu** (rodič `.agentic`), `AGENTIC_RUN_ROOT` env to přebíjí (izolace) | engine cesty jsou path-parametrizované → kandidát na read-only mount / přesun mimo write-zónu agenta |
| Container PoC už zavedl **přesně tenhle vzor** (`backlog/INITIATIVE-container-platform.md` ink. 3): `/etc/claude-code/managed-settings.json` zapečené v obrazu, **nepřebitelné uživatelem ani AI** (deny `.env`/secrets), + PreToolUse hook jako doplněk | precedent: tvrdá hranice = FS/obraz, hook = doplněk. Doslovný poznatek PoC: *„klec zavírá vchod, ale skutečná vnitřní hranice je zeď (managed-settings/FS), ne klec"* |
| FEASIBILITY (`§Abstrakce engine RunState`): cílový provoz = engine + `/done` **uvnitř kontejneru** nad lokálními soubory (`RemoteFileBackend`); DB = jen index | enginové cesty žijí v kontejneru → write-protection lze dát OS/mount vrstvě, ne CLI toolu |

---

## 3. Politika (revize 2026-06-20 — širší scope)

Politika má teď **tři páky, seřazené dle síly vynucení** (nejtvrdší první):

1. **§3c Path-based write-protection** — *kdo smí psát kam* (enginové cesty zamčené, write-owner = Eywa).
   Vynuceno FS/OS, ne pattern-matchem. **Tohle je primární linie.**
2. **§3b Commit ownership** — commit dělá výhradně engine-proces, ne agent-shell. Architektonické
   rozlišení, ne grep nad stringem.
3. **§3d Příkazový denylist** — úzká rodina stavově-destruktivních příkazů. **Sekundární / redundantní**
   pojistka pro to, co FS-ochrana nepokrývá (operace nad tracked soubory, které agent vlastní legitimně).
4. **§3a Tool allowlist** — `tools:` v hlavičce (beze změny scope, mění se jen zdroj definice).

### 3a. Nástroje → allowlist (potvrdit + utáhnout)

`tools:` v hlavičce wrapperu už allowlist je. Auditoři (`sheldon-spec`, `heimdall-security`,
`vitek-quality`, `edna-design`) mají `Read, Glob, Grep, Bash` (žádný Write/Edit) — to je
**správně, ponechat**. Generující agenti mají i `Write, Edit`. Allowlist nástrojů je adekvátní
páka pro to, *jaké třídy nástroje* agent má; `Bash` je ale jeden bit — nerozlišuje `git status`
od `git stash`. Granularitu uvnitř Bash řeší §3d.

**Změna nutná pro architekturu zdroje pravdy:** přesunout `tools:` definici z hardcoded mapy
v generátoru do neutrálního zdroje — buď do frontmatteru `.agentic/agents/<short>.md`
(`tools:` řádek), nebo do centrálního policy souboru (viz §5). Generátor pak `tools:` jen
projektuje, nevymýšlí.

### 3b. Commit ownership → výhradně engine (`/done`)

**PO direktiva (2026-06-20):** `git commit` smí dělat **jen engine** přes `run.sh done`
(commit-on-done). **Žádný agent — ani orchestrátor ručně — necommituje.** Commit přestává být
„povolený příkaz, který nezakazujeme" a stává se **enginovou operací**.

Dnešní stav (viz §2): `core/run.py` zatím `git commit` *nedělá* — provádí ho ručně orchestrátorská
session po `done`. „Commit ownership → engine" je proto **nová engine schopnost** (rollout §7), ne
přepnutí flagu. Cílově: `done` (a/nebo dedikovaný commit-on-done krok) volá `git add` + `git commit`
**uvnitř engine-procesu** se zprávou odvozenou z envelope/vlny.

**Proč to řeší zdánlivý konflikt „denylist by zablokoval i commit-on-done":** rozlišení „kdo
commituje" je **architektonické, ne pattern-match**. Není to „agentovi zakaž `git commit`, ale
enginu povol stejný string" (to by hook nerozeznal — vidí jen string). Je to: *commit se vůbec
nespouští z agent-shellu*; spouští ho engine-proces, který jede mimo odposlech agentových příkazů
(jiný proces, případně i jiný uživatel/mount-kontext v kontejneru). Denylist tedy může `git commit`
**v agent-shellu zakázat tvrdě** bez výjimky — engine commituje jinou cestou. Žádná „díra pro
commit-on-done" v denylistu nevzniká.

### 3c. File/folder blacklist → path-based write-protection (PRIMÁRNÍ)

**PO direktiva (2026-06-20):** enginové cesty jsou pro běžné agenty **WRITE-zakázané**; číst je smí
read-only. **Do enginového stavu smí psát jen engine sám a meta-agent Eywa.**

**Co je „engine stav" (přesný výčet write-protected cest):**

| Cesta | Co to je | Kdo smí psát |
|---|---|---|
| `current-run.md` (root + `.agentic/`) | strojový stav běhu (active_node, run) | engine (`run.sh`) |
| `STATE.md` (root) | FIFO machine blok hotových vln | engine (`on_terminal`) |
| `runs/**` + `.agentic/runs/**` | ledgery (`ledger.yaml`) + `summary.md` per vlna | engine (`done`, `summary`) |
| `.agentic/pipeline/**` | graf (`delivery.yaml`), `artifacts.yaml`, `vocabulary.yaml` — routing autorita | Eywa (graf) |
| `.agentic/scripts/pipeline/core/**` | engine kód (run.py, frontier, common, ledger, …) | engine maintainer (L3) |
| `.agentic/policy/**` | tato politika + budoucí policy yaml | Eywa |
| `.agentic/agents/**`, `.agentic/templates/**` | agent definice + šablony | Eywa (po L3 pro nové/smazané) |

> Pozn.: výčet „engine stav" se přidá i do `constitution.md §8` jako nová destruktivní kategorie
> (rollout §7) — aby norma kryla i tuhle třídu, ne jen DB/data.

**Write-owner = Eywa pro autorské cesty** (`pipeline/**`, `policy/**`, `agents/**`, `templates/**`)
už platí z `agents/eywa-meta.md §Write scope`. Tahle politika to jen povyšuje na **vynucené FS
pravidlo**, ne jen konvenci v definici. **Běhový stav** (`current-run.md`, `STATE.md`, `runs/**`)
nepíše ani Eywa ručně — píše ho **jen engine**; Eywa do něj smí zasáhnout výhradně přes engine
příkaz (`run.sh repair`, §6), ne přímým editem. To je důsledek memory „Agents must not write engine
state" + „Engine writes STATE on terminal" — povýšený z principu na vynucení.

**Jak se vynucuje** — viz §4 (kontrakt) a §5 (kde blacklist žije). Stručně: FS práva / read-only
mount v kontejneru (primárně), neutrální path-check jako reference, a teprve nakonec adaptérový
deny jako redundantní pojistka.

### 3d. Příkazy → denylist (sekundární pojistka, rozšířený)

Allowlist *všech* legitimních shell příkazů je nepraktický (agenti běžně volají pytest, ruff,
npm, git status/diff/log, awk, sed při čtení, python, node…). Proto **denylist úzké rodiny**
stavově-destruktivních příkazů. Hrozba je omyl, ne sabotáž → stačí zavřít cesty, po kterých
kooperativní agent omylem sáhne. **Po posunu na FS-ochranu (§3c) je denylist sekundární** —
chytá to, co FS práva nepokrývají: destruktivní git operace nad soubory, které agent *vlastní*
legitimně (vlastní write-scope), ale které mutují celý working tree / historii.

**Zakázané vzory (revize 2026-06-20 — `rebase`/`cherry-pick`/`revert` povýšeny ze „zvážit" na ZAŘADIT):**

| Vzor | Proč | Co NESMÍ chytit (false-positive guard) |
|---|---|---|
| `git stash` (vč. `push`/`pop`/`apply`/`drop`) | přímý viník incidentu | `git stash list` (read-only) — POVOLIT |
| `git commit` | **commit vlastní jen engine (§3b)** — agent nikdy | engine commituje mimo agent-shell, denylist mu nevadí |
| `git checkout` / `git switch` (s cestou/`-- .`/branch switch měnícím tree) | přepíše tracked soubory (engine stav) | `git checkout -b <new>` bez přepisu? → bezpečné, ale jednoduší je zakázat celé a dovolit přes orchestrátora |
| `git reset` (`--hard`/`--mixed`/`--soft` na tree) | zahodí staged/working stav | — |
| `git restore` | totéž co checkout-cesta | — |
| `git clean` (`-f`/`-d`/`-x`) | smaže untracked (např. nové handoffy) | — |
| `git rebase` | **ZAŘAZENO (PO 2026-06-20)** — přepíše historii i tree, koliduje s commit-on-done | — |
| `git cherry-pick` | **ZAŘAZENO (PO 2026-06-20)** — vytváří/mění commity mimo engine | — |
| `git revert` | **ZAŘAZENO (PO 2026-06-20)** — vytváří commit mimo engine, mění tree | — |
| přepis enginových souborů: `> current-run.md`, `>> current-run.md` | obejde engine, přepíše stav | čtení `cat current-run.md` — POVOLIT |
| `rm` / `mv` cílící na engine cesty (`current-run.md`, `STATE.md`, `runs/**`) | smazání/přesun engine stavu | `rm -rf alltest`, `rm` v `/tmp` — POVOLIT |
| `git push --force` / `-f` | force push (už v `constitution.md §8`, ale nevynucené) | `git push` (běžný) — POVOLIT |

**Musí projít (explicitní allow-through, nikdy neblokovat):**
`git status`, `git diff *`, `git log *`, `git stash list`, `git show`, `git ls-files`,
`pytest *`, `ruff *`, `npm test`, `npm run *`, `node *`, `python3 *`, čtení (`cat`, `grep`,
`awk`, `sed -n`), `run.sh *` (engine vstupní bod — vč. `run.sh done`, který interně commituje).

> Pozn.: `git push` (bez force) zůstává povolen — push není stavově-destruktivní a engine ho
> nevlastní stejně jako commit. `git commit` je **nově tvrdě zakázán pro agenty** (§3b).

---

## 4. Vynucovací kontrakt (revize — těžiště na ENGINE + FS, ne na CLI hooku)

Framework definuje politiku (§3, §5) a **kontrakt** na její vynucení. Revize 2026-06-20 mění,
*kde* vynucení sedí: **primárně engine a souborový systém**, CLI adaptér už jen jako opční
redundantní pojistka. Vynucení rozdělené do tří vrstev podle síly (tvrdá → měkká):

### Vrstva 1 — ENGINE vynutí nativně (povinné, jádro)

Engine MUSÍ vlastnit operace, které nesmí dělat agent:

1. **Commit ownership** — `git add` + `git commit` provádí **engine-proces** (uvnitř `run.sh done` /
   commit-on-done kroku), ne agent-shell. Engine si commit dělá ve své vlastní logice; pro agenta
   `git commit` neexistuje jako legitimní cesta (§3b). *Tohle je architektonické rozlišení procesu,
   ne pattern-match nad stringem.*
2. **Checkpoint stavu** — engine při přechodu na dispatch/handoff **sám** checkpointuje
   `current-run.md` + ledger do runtime cesty, idempotentně (§6). Žádný agent ani orchestrátor to
   nedělá ručně.
3. **Repair** — `run.sh repair` rekonstruuje běhový stav z ledgeru (replay), idempotentně, párově
   s checkpointem (§6). Zotavení je engine příkaz, ne ruční rekonstrukce.

### Vrstva 2 — FILESYSTÉM / OS vynutí write-protection (primární linie pro „kam smí agent psát")

Enginové cesty (§3c výčet) jsou pro agent-proces **fyzicky read-only**:

4. **Read-only na engine stav pro agenta** — vynuceno OS právy / read-only bind-mountem (v
   container-platformě, viz níže), ne pattern-matchem nad `>`/`rm`. Když je cesta read-only na úrovni
   FS, *žádný* příkaz (ani neznámý budoucí, ani jiný tool, ani omyl) ji nepřepíše — `git stash`/`reset`
   nad ní selžou samy, protože zápis neprojde. Tohle je nejtvrdší a nejlevnější vrstva, jakmile
   engine běží v kontejneru.
5. **Write-owner = engine + Eywa** — zápis do engine stavu má jen engine-proces (běhový stav) a
   Eywa (autorské cesty: graf, policy, agenti) — viz §3c, §5. Realizováno odděleným mount-kontextem /
   právy, ne důvěrou v chování toolu.

### Vrstva 3 — CLI adaptér: command-interception (OPČNÍ, redundantní pojistka)

Pro to, co FS-ochrana nepokrývá — destruktivní git operace nad soubory, které agent *vlastní*
legitimně (`git rebase`/`stash`/`reset` mutují celý tree, ne jen agentovy soubory) — smí adaptér
přidat command-interception. **Není to nositel řešení, jen vrstva navíc.** Pokud ji adaptér přidá,
MUSÍ:

6. **Zachytit příkaz PŘED spuštěním** a odmítnout, pokud matchne `deny_commands` (§5), s respektem
   k `allow_through`. Rozhodovat nad celým command stringem (pipe/`&&`/subshell), ne jen nad jménem.
   Fail-safe: při nejistotě raději blokovat.
7. **Vysvětlit odmítnutí** — vrátit agentovi důvod („`git stash` odloží git-tracked stav enginu;
   potřebuješ-li čistý tree, vrať BLOCKER orchestrátorovi"), ne tiché selhání.
8. **Mít jedno evolvovatelné místo** — nový vzor = edit politiky (§5), ne rozsev přes N konfigurací.

> **Klíčové oddělení (PO si to explicitně vyžádal promyslet):** engine **neuvidí živý shell příkaz
> agenta** — `git stash` se spustí mimo engine-proces. Klasický command-interception proto potřebuje
> *buď* (a) tool-hook *nebo* (b) filesystémová práva / read-only mount na úrovni OS. **Vzhledem ke
> container-platformě volíme (b) jako primární** — viz §4.1. Po FS-enforcementu zbývá na CLI adaptér
> už jen úzká redundance (vrstva 3) pro tree-mutující git operace, a i ta je „nice to have", ne nutná.

### 4.1 Filesystémové vynucení v container-platformě (kam princip míří)

`backlog/INITIATIVE-container-platform.md` + `FEASIBILITY` dávají tomuto návrhu fyzickou půdu:

- **Engine + `/done` běží UVNITŘ kontejneru** (`RemoteFileBackend`) nad lokálními soubory; appka
  jen orchestruje přes container-agent. Enginové cesty tedy žijí v kontejneru.
- **Precedent už existuje** (ink. 3): `/etc/claude-code/managed-settings.json` zapečené v obrazu,
  **nepřebitelné uživatelem ani AI**, + PreToolUse hook jako doplněk. Doslovný poznatek PoC:
  *„klec zavírá vchod, ale skutečná vnitřní hranice je zeď (FS/managed-settings), ne klec."*
  Stejný vzor aplikujeme na engine stav: **zeď = FS práva na enginové cesty**, ne klec (hook).
- **Návrh FS-modelu uvnitř kontejneru:**
  - engine stav (`current-run.md`, `STATE.md`, `runs/**`, `core/**`) je **read-only pro shell, do
    kterého má přístup AI/agent**; zapisuje do něj jen engine-proces (jiný uživatel / privilegovaný
    mount-kontext container-agenta).
  - realizace: buď read-only bind-mount enginové podsložky pro AI shell, nebo POSIX vlastnictví
    (engine-uživatel vlastní cesty, AI běží pod ne-vlastníkem) — volba je implementační (rollout).
  - `AGENTIC_RUN_ROOT` (engine už ho čte, viz §2) usnadní oddělit *runtime* zápisovou cestu enginu
    od read-only projekce, kterou vidí agent.

**Důsledek:** v cílovém (kontejnerovém) provozu je command-interception (vrstva 3) téměř zbytná —
FS práva pokryjí zápisy do engine stavu úplně. Zbývá jen úzká rodina tree-wide git operací
(`rebase`/`stash`), kterou agent může spustit nad *vlastními* soubory; tu řeší buď denylist
(vrstva 3), nebo — čistěji — to, že agent commit/rebase vůbec nepotřebuje, když commit vlastní
engine (§3b). Po FS-enforcementu + commit-ownership na enginu **na čistý tool-adaptér nezbývá
žádná nutná vynucovací povinnost** — jen opční pojistka. Viz §A (zredukováno).

---

## 5. Umístění zdroje pravdy v `.agentic/` (politika + path-blacklist + write-owner)

Politika MUSÍ žít neutrálně (framework je tool-agnostický). Revize 2026-06-20 přidává **path-based
blok** (kdo smí psát kam) jako *první* sekci — je to primární páka (§3c, §4 vrstva 2). Příkazový
denylist klesá na sekundární.

**Nový soubor: `.agentic/policy/command-guardrails.yaml`** (tool-agnostický popis politiky)

```yaml
# command-guardrails.yaml — neutrální politika: kam agenti NESMÍ psát + co NESMÍ spouštět.
# Tool-agnostické. Zdroj pravdy je toto; engine/FS to vynucuje, adaptér ho jen volitelně projektuje.
version: 2
rationale: >
  Do stavu workflow enginu nesmí sahat žádný agent. Vynucení je v enginu + FS, ne v CLI toolu.
  Primárně path-based write-protection; commit vlastní engine; příkazový denylist je sekundární.

# ── PRIMÁRNÍ: path-based write-protection (vynuceno FS/OS, viz §4 vrstva 2) ──
# Enginové cesty jsou pro běžné agenty read-only. Zápis = jen engine-proces nebo write-owner.
write_protect:
  # běhový stav — píše JEN engine-proces (run.sh), žádný agent ani Eywa ručně
  engine_runtime:
    paths: [current-run.md, .agentic/current-run.md, STATE.md, runs/**, .agentic/runs/**]
    writer: engine            # výhradně engine-proces (done/summary/checkpoint/repair)
    agents_access: read-only
  # autorské enginové cesty — píše JEN meta-agent Eywa (graf, policy, agenti, šablony)
  engine_authored:
    paths: [.agentic/pipeline/**, .agentic/policy/**, .agentic/agents/**, .agentic/templates/**]
    writer: eywa-meta         # po L3 pro destruktivní změny (nový/smazaný agent, template)
    agents_access: read-only
  # engine kód — mění jen maintainer pod L3, agenti read-only
  engine_code:
    paths: [.agentic/scripts/pipeline/core/**]
    writer: l3-maintainer
    agents_access: read-only

# ── ENGINE-OWNED operace (agent je nedělá vůbec; viz §3b, §4 vrstva 1) ──
engine_owned_ops:
  - id: commit
    desc: "git add + git commit dělá výhradně engine-proces (commit-on-done), ne agent-shell"
  - id: checkpoint
    desc: "engine při dispatch/handoff checkpointuje current-run + ledger (idempotentně)"
  - id: repair
    desc: "run.sh repair = replay z ledgeru; rekonstrukce stavu je engine příkaz, ne ruční edit"

# ── SEKUNDÁRNÍ: příkazový denylist (redundantní pojistka, viz §4 vrstva 3) ──
deny_commands:
  - id: git-stash
    match: '^\s*git\s+stash\b'
    except: '^\s*git\s+stash\s+list\b'   # read-only varianta povolena
    reason: "git stash odloží git-tracked stav enginu (current-run.md, runs/)"
  - id: git-commit
    match: '^\s*git\s+commit\b'
    reason: "commit vlastní engine (commit-on-done); agent nikdy necommituje (§3b)"
  - id: git-reset-tree
    match: '^\s*git\s+reset\b'
    reason: "reset zahodí staged/working stav rozdělané vlny"
  - id: git-clean
    match: '^\s*git\s+clean\b'
    reason: "clean smaže untracked (např. nové handoffy)"
  - id: git-checkout-restore-switch
    match: '^\s*git\s+(checkout|restore|switch)\b'
    reason: "přepíše tracked soubory včetně engine stavu"
  - id: git-rebase
    match: '^\s*git\s+rebase\b'
    reason: "přepíše historii i tree, koliduje s commit-on-done (PO 2026-06-20)"
  - id: git-cherry-pick
    match: '^\s*git\s+cherry-pick\b'
    reason: "vytváří/mění commity mimo engine (PO 2026-06-20)"
  - id: git-revert
    match: '^\s*git\s+revert\b'
    reason: "vytváří commit mimo engine + mění tree (PO 2026-06-20)"
  - id: git-force-push
    match: '^\s*git\s+push\b.*(--force|-f)\b'
    reason: "force push (constitution §8)"
  - id: engine-state-overwrite
    match: '(^|;|&&|\|)\s*>{1,2}\s*(current-run\.md|STATE\.md)'
    reason: "přímý přepis stavu enginu obchází run.sh done"
  - id: engine-state-rm-mv
    match: '^\s*(rm|mv)\b.*\b(current-run\.md|STATE\.md|runs/)'
    reason: "smazání/přesun stavu enginu"

# Allow-through: vždy povolit i kdyby matchlo deny (read-only / vstupní bod enginu).
allow_through:
  - '^\s*git\s+(status|diff|log|show|stash\s+list|ls-files)\b'
  - '^\s*git\s+push\b(?!.*(--force|-f))'   # push bez force OK (push není engine-owned)
  - '^\s*(cat|grep|awk|sed\s+-n)\b'
  - 'run\.sh\b'                             # run.sh done interně commituje = engine cesta

# Tool allowlist (přesun z hardcoded mapy v generátoru → sem).
tool_profiles:
  generating: [Read, Write, Edit, Glob, Grep, Bash]
  readonly:   [Read, Glob, Grep, Bash]
# které agenty jsou readonly (dnes hardcoded v generátoru READONLY = {...})
readonly_agents: [sheldon-spec, heimdall-security, vitek-quality, edna-design]
```

**Dva neutrální reference checkery** (`.agentic/scripts/`), oba čisté a tool-agnostické:

1. **`command-guardrail-pathcheck.<lang>` (PRIMÁRNÍ)** — dostane *(agent-id, cílová write cesta)*,
   přečte `write_protect`, vrátí `allow` / `deny + reason`. Tohle je deterministické jádro
   path-blacklistu. **V kontejnerovém provozu je ale jen reference / lint** — skutečné vynucení
   dělá FS (read-only mount/práva, §4.1). Mimo kontejner (dnešní lokální CLI) slouží jako kontrola
   a podklad pro adaptérovou deny projekci.
2. **`command-guardrail-check.<lang>` (SEKUNDÁRNÍ)** — dostane command string, přečte `deny_commands`/
   `allow_through`, vrátí `allow` / `deny + reason`. Žádné CC-specifikum (nezná hook, settings.json,
   PreToolUse). Redundantní pojistka pro tree-mutující git operace.

Politika i checkery žijí v `.agentic/` (zdroj pravdy). **Primární vynucení je FS/engine, ne checker** —
checkery jsou deterministická reference + případný vstup pro adaptér. *Jak* (a zda vůbec) se checker
napojí do konkrétního nástroje — viz §A (zredukováno). Framework o tom napojení nic nepředepisuje.

---

## 6. Engine-native resilience: checkpoint + repair (revize — oboje v enginu, ne orchestrátor)

**PO direktiva (2026-06-20):** checkpoint MUSÍ být **engine-native**. Ne „orchestrátor si před
dispatchem uloží kopii" (to je spoléhání na chování CLI toolu — přesně to, co tahle revize odmítá).
Engine sám při přechodu na dispatch/handoff checkpointuje stav. Checkpoint + repair tvoří
**párovou dvojici uvnitř enginu**: prevence (snapshot) + zotavení (replay).

### 6.1 `run.sh checkpoint` — engine-native snapshot (PŘIDÁNO direktivou)

Engine při přechodu, který předchází běhu agenta (dispatch / handoff bod), **sám** uloží snapshot
běhového stavu do runtime cesty:

- **Co:** `current-run.md` (stavový blok) + odkaz na aktuální `runs/<run>/ledger.yaml` (ledger je
  append-only, stačí znát HEAD pozici).
- **Kam:** runtime cesta **mimo agentův write-scope** (např. `$AGENTIC_RUN_ROOT/.checkpoint/` nebo
  cesta vlastněná engine-procesem; v kontejneru oddělený mount). Ne git-tracked, ne editovatelná
  agentem.
- **Kdy:** engine ho dělá **automaticky** v rámci `run.sh` při dispatch/handoff přechodu — ne
  orchestrátor, ne agent. Volání může být i implicitní uvnitř `next`/`drive` (rozhodnutí rolloutu).
- **Idempotentní:** opakovaný checkpoint nad stejným stavem je no-op / přepíše posledním; nikdy
  nekoroduje.

### 6.2 `run.sh repair` — replay z ledgeru (párově s checkpointem)

`run.sh repair` rekonstruuje `current-run.md` z `runs/<run>/ledger.yaml` (+ STATE machine blok,
který engine na `done` už zapisuje — viz memory „Engine writes STATE on terminal"). Dnes se to dělá
ručně (`start` + replay `done`); povýšit na `core/run.py repair` subcommand = idempotentní,
testovatelné. Ledger je beztak zdroj pravdy → repair z něj je robustnější než z checkpointu;
checkpoint je rychlá první linie, repair je autoritativní zotavení.

**Vztah checkpoint ↔ repair:**
- *checkpoint* = levný snapshot před rizikovým krokem (rychlý rollback, pokud agent stav rozhodí).
- *repair* = plná rekonstrukce z ledgeru (zdroj pravdy), použije se i bez čerstvého checkpointu.
- Oboje **engine příkaz**, oboje běží mimo agent-shell → agent je nezavolá ani neobejde.

### 6.3 Držet engine stav mimo working tree → v kontejneru NATIVNÍ

V1 to měla jako „větší zásah, zvážit později". **Container-pivot to ale řeší nativně:** engine
běží uvnitř kontejneru nad lokálními soubory (`RemoteFileBackend`), `AGENTIC_RUN_ROOT` odděluje
runtime zápisovou cestu. Engine stav tedy může žít v **runtime cestě read-only pro AI shell**
(§4.1) — `git stash`/`reset` v agentově kontextu se k němu nedostanou vůbec (zápis neprojde na FS).
Tracked-v-gitu zůstává jen *projekce* pro viditelnost; autorita je runtime cesta. Plný dopad na
resume protokol řeší rollout container-platformy, ne tento návrh — ale směr je jasný a konzistentní.

**Doporučení:** engine-native **checkpoint (§6.1) + repair (§6.2)** je minimální robustní dvojice
(prevence + zotavení), obojí uvnitř enginu. FS write-protection (§4.1) je činí ještě robustnějšími —
v kontejneru se stav nedá rozhodit zvenčí vůbec. Žádná resilience páka už nestojí na orchestrátorovi
ani na CLI toolu.

---

## A. Adaptér Claude Code (ZREDUKOVÁNO — hook je už jen opční redundantní pojistka)

> **Revize 2026-06-20:** po posunu těžiště na engine + FS (§3c, §4 vrstvy 1–2) **na CLI adaptéru
> nestojí žádná nutná vynucovací povinnost.** Hook už není nositel řešení — je to *opční* třetí
> vrstva (§4 vrstva 3) pro tree-mutující git operace, a i ta je v kontejnerovém provozu z velké
> části zbytná (FS práva pokryjí zápisy do engine stavu). Tahle sekce proto smrskla na minimum;
> většina otázek z původní §A.3 **padá**, protože jsme přestali stát na hooku.

### A.1 Co adaptér POVINNĚ projektuje (i bez hooku)
Jen `tools:` allowlist — to není o příkazech, ale o třídách nástrojů (auditoři bez Write/Edit):
- z `tool_profiles` + `readonly_agents` (§5) projektovat `tools:` řádek do wrapperů
  (nahradí dnešní hardcoded `DEFAULT_TOOLS`/`READONLY`/`READONLY_TOOLS` v generátoru).

### A.2 Co adaptér VOLITELNĚ přidá jako redundantní pojistku (§4 vrstva 3)
Pre-exec odposlech na `Bash` (v CC dnes „PreToolUse hook") volající sekundární checker (§5) nad
command stringem; případně pár nejtvrdších `deny_commands` jako `permissions.deny` v `settings.json`.
**Není to nutné pro splnění kontraktu** — kontrakt plní engine (vrstva 1) + FS (vrstva 2). Pokud
se adaptérová pojistka přidá, musí být `deny`/`hooks` idempotentně reaplikované (merge, ne overwrite
osobních allow).

### A.3 Co z původních otevřených otázek PADÁ (a co málo zbývá)
**PADÁ** (rozhodnutí o vynucení už nestojí na hooku):
- ~~per-subagent vs globální scope hooku~~ — irelevantní; vynucení je FS/engine, ne hook.
- ~~přesné schéma PreToolUse vstupu~~ — jen pokud někdo vůbec staví opční pojistku.
- ~~jak hook signalizuje blokuj/povol~~ — totéž, jen pro opční vrstvu.
- ~~merge deny vs allow v settings.json~~ — `Bash(git *)` v osobním allow už není „díra v denylistu",
  protože denylist není primární obrana; FS práva platí bez ohledu na CC allow.
- ~~hook vs allow interakce~~ — totéž.

**ZBÝVÁ** (přesunuto výš, do §7 jako rollout-rozhodnutí, ne CC-detail): jak realizovat FS
write-protection v lokálním (ne-kontejnerovém) dev provozu, kde read-only mount není po ruce —
viz §7 + „Co potřebuje rozhodnout".

---

## 7. Rollout (revize — pořadí dle síly vynucení: engine + FS napřed, adaptér naposled a opčně)

Po L3 (schváleno 2026-06-20), tool-agnosticky, **v pořadí podle tvrdosti vrstvy**:

**Fáze R1 — ENGINE schopnosti (vrstva 1, jádro):**
1. **Commit ownership** — přidat commit-on-done do `core/run.py` (`git add` + `git commit`
   v engine-procesu na `done`; zpráva z envelope/vlny) + selftest. **Pozor:** dnes commit dělá
   ručně orchestrátor (§2) — tohle je nová schopnost, ne flag.
2. **`run.sh checkpoint`** — engine-native snapshot při dispatch/handoff přechodu (§6.1),
   idempotentní, do runtime cesty mimo agentův scope + selftest.
3. **`run.sh repair`** — replay z ledgeru (§6.2) + selftest. Párově s checkpointem.

**Fáze R2 — POLITIKA + norma (zdroj pravdy):**
4. přidat `.agentic/policy/command-guardrails.yaml` (write_protect + engine_owned_ops +
   deny_commands, §5);
5. přidat neutrální checkery `command-guardrail-pathcheck.<lang>` (primární) +
   `command-guardrail-check.<lang>` (sekundární), §5;
6. doplnit `constitution.md §8` o kategorii **„stav workflow enginu"** (current-run.md / STATE.md /
   runs/ / pipeline / core / working-tree git operace) — aby norma kryla i tuhle třídu, ne jen
   DB/data. Doplnit `§7 write-scope`, že engine cesty jsou read-only pro všechny agenty mimo
   engine-proces a write-ownera (Eywa pro autorské cesty).

**Fáze R3 — FS write-protection (vrstva 2, primární vynucení):**
7. **V kontejnerovém provozu** (cílový stav): read-only mount / POSIX vlastnictví engine cest pro
   AI shell — navázat na container-platformu (ink. 3 už má precedent managed-settings). Engine stav
   vlastní engine-uživatel / container-agent; AI běží pod ne-vlastníkem. `AGENTIC_RUN_ROOT` oddělí
   runtime zápisovou cestu od read-only projekce.
8. **V lokálním dev provozu** (přechodné, do kontejnerizace): FS read-only mount typicky není po
   ruce → primární obranou dočasně zůstává **path-check + sekundární denylist** (vrstva 3) jako
   *náhrada* za FS vrstvu, dokud běh nepřejde do kontejneru. Tohle je jediné místo, kde dnes ještě
   stojíme na pattern-matchi — a je to explicitně přechodné.

**Fáze R4 — adaptér (OPČNÍ, redundance):**
9. `tools:` projekce do wrapperů (povinné, ne o příkazech — §A.1); volitelně PreToolUse pojistka
   (§A.2) + RESTART session (memory „Wrapper regen after source bump"); selftest `git stash` → blok,
   `git stash list` → projde. **Bez této fáze je kontrakt stále splněn** (engine + FS).

`tools:` granularita se obsahově nemění (auditoři read-only, generující beze změny) — mění se jen
*zdroj* definice (neutrální policy místo hardcode v generátoru).

---

## 7b. Rollout-hardening: commit-on-done je OPT-IN scoped na orchestrátorovu CLI vlnu (2026-06-20)

**Incident (regrese vrstvy R1, commit ac5a3a5/99b75c5):** Při běhu server testů vystřelil
commit-on-done **8×** a zacommitoval celý working tree (haraburdí + cizí rozdělaná práce) se
zprávou `chore(wave:2026-06-13-done-endpoint): backend PASS`. Orchestrátor zotavil resetem.

**Root-cause:** `nodecommit.commit_enabled()` byl **default ON**. Server `/api/done` i done-engine/
done-endpoint testy spouštějí engine `done` (in-process i přes subprocess `core/run.py done`).
Subprocess cesta (`_run_cli_done` v `tests/server/unit/test_done_engine.py` +
`tests/integration/test_done_endpoint_integration.py`) tedy vystřelila `result.main` →
`nodecommit.commit_node` v REÁLNÉM repu. Tyhle done volání **nejdou přes `run.sh start`**, takže
ve stavu chybí `commit_baseline` → baseline-exclusion nic nevyloučilo → `git add -A` zametl vše.

**Fix (implementováno 2026-06-20, vrstva R1 hardening):**
- **`nodecommit.commit_enabled()` → default OFF (opt-in).** True jen když je `AGENTIC_NODE_COMMIT`
  explicitně truthy (`1/true/yes/on`); unset/prázdné/cokoli jiného = False.
- **`run.sh` zapíná flag VÝHRADNĚ pro `done`/`drive`** (`export AGENTIC_NODE_COMMIT="${…:-1}"` —
  respektuje existující hodnotu, takže jde override na 0). Ostatní subcommandy
  (`status/next/check/repair/checkpoint/start/…`) flag nezapínají — commitovat nemají.
- **Conftest defense-in-depth:** `tests/conftest.py` autouse force `AGENTIC_NODE_COMMIT=0` pro
  celou server test suite — done testy NIKDY necommitnou reálné repo, ať je default jakkoli a ať
  se done zavolá in-process nebo přes shell.
- **Pipeline testy commit chování** (`scripts/pipeline/tests/test_commit_on_done.py`) explicitně
  zapínají flag (autouse `=1` + `_CLI_ENV` pro subprocess), protože spoléhaly na default ON.

**Žádoucí koncový stav (splněno):** commit-on-done vystřelí JEN z orchestrátorovy CLI vlny
(`run.sh done`/`drive`). NIKDY ze serverového `/api/done` (in-process `run_done` ani nevolá
`commit_node` — volá jen validate/derive/append_ledger/advance_state) ani z testů.

**Invokační cesty (ověřeno):**
- Server `/api/done` → `server/done.py:run_done` = **in-process import** engine funkcí, BEZ
  `commit_node`. Default OFF stačí (flag unset → no commit).
- done testy AC-1 byte-identity → **subprocess** `python3 core/run.py done` (NE přes `run.sh`).
  Default OFF + conftest force-0 to pokrývá; `run.sh` shell-zapnutí se na přímý `run.py` neaplikuje
  (proto je conftest pojistka nutná, ne jen hezká).

**Otevřená otázka (odložit na container design):** *má serverový `/api/done` v kontejneru
commitovat projektové repo?* Dnes ne (commit vlastní jen CLI vlna). V kontejnerovém provozu, kde
engine + `/done` běží uvnitř kontejneru nad projektovými soubory (§4.1), může dávat smysl, aby
i serverem řízený `done` měl commit-on-done — ale to vyžaduje vlastní baseline-capture na začátku
serverem řízené vlny (jinak znovu `git add -A` problém). **Rozhodnout v container-platform designu**
(`backlog/INITIATIVE-container-platform.md`), ne teď.

## 7c. Known follow-up (NE součást tohoto fixu): done testy nejsou hermetické vůči engine stavu

Separátní pre-existing test-hygiena, **odhalená** (ne způsobená) tímto fixem. NENÍ to commit-on-done
bug ani jeho regrese:

- **Symptom:** `runs/2026-06-13-done-endpoint/ledger.yaml` byl ` M` (modified) už na startu session;
  done-engine/done-endpoint testy mutují working-tree `current-run.md` + ten ledger.
- **Root-cause:** `common.run_root()` ukotvuje engine stav na **umístění skriptu** (rodič `.agentic`),
  NE na cwd. Test helper `_run_cli_done` spouští `python3 core/run.py done` s `cwd=tmp_path`, ale
  `append_ledger`/`advance_state` zapíšou ledger + `current-run.md` do REÁLNÉHO repa (anchored path),
  ne do tmp fixture projektu. AC-1 byte-identity testy pak čtou polluted real-repo soubor.
- **Důsledek:** 5 AC-1 byte-identity testů (`test_*_byte_identical*`, `test_valid_run_segment_still_passes`)
  je dnes ne-hermetických — „procházely" jen dokud real-repo `current-run.md`/ledger náhodou držel
  shodný post-done stav. Ostatní done testy (422/409/428/path-traversal/ETag/in-process happy-path,
  58 testů) jsou hermetické a procházejí.
- **Fix (až bude řešen):** subprocess CLI cesta v testech musí předat `AGENTIC_RUN_ROOT=tmp_path`
  (engine ho čte jako override, viz §2), aby `run_root()` mířil do fixture projektu, ne do repa.
  Pak budou testy hermetické a real-repo `current-run.md`/`runs/**` se nikdy nedotknou.
- **Vlastník:** tester (joey-qa) / engine maintainer. Eywa to jen zaznamenává jako follow-up.

## 8. Co tento návrh NEdělá (hranice — revize)

- **Stále DESIGN-ONLY** — neimplementuje nic živého: žádná změna `core/run.py` (commit-on-done,
  checkpoint, repair), `settings.json`, wrapperů, FS práv/mountů ani `constitution.md`. Vše je
  k rolloutu (§7), ne hotové.
- **Neřeší sabotáž** — threat model je *omyl kooperativního agenta*. FS write-protection (§4.1)
  ale jako vedlejší efekt sabotáž ztěžuje (zápis fyzicky neprojde), takže ochrana je tvrdší než
  jen anti-omyl. Cílenou eskalaci práv / únik z kontejneru tenhle návrh neřeší (to je #27 security-sandbox).
- **Neřeší ToS pro běh cizího předplatného** v komerční platformě — odložená byznys otázka
  container-pivotu, mimo scope.
- **Nepřepisuje resume protokol** kvůli přesunu engine stavu do runtime cesty (§6.3) — to dořeší
  rollout container-platformy; tady jen ukotvujeme směr.
- **Nerozhoduje implementační volbu FS-ochrany v lokálním dev provozu** (read-only mount vs path-check
  jako náhrada) — viz „Co potřebuje rozhodnout" níže.

**VYŘEŠENO touto revizí (už nejsou otevřené otázky):**
- ~~zda subagent smí `git commit`~~ → **NE, commit vlastní jen engine** (§3b, PO direktiva).
- ~~zda zařadit rebase/cherry-pick/revert~~ → **ANO, zařazeno** (§3d, PO direktiva).
- ~~zda checkpoint dělá orchestrátor~~ → **NE, engine-native** (§6.1, PO direktiva).
- ~~kde žije file/folder blacklist~~ → **`policy/command-guardrails.yaml §write_protect`, vynuceno FS** (§3c, §5).

---

## 9. Co potřebuje rozhodnout orchestrátor / Vitek před rolloutem (zbylé volby)

Direktivy PO (commit ownership, rebase/cherry-pick/revert, engine-native checkpoint, FS blacklist
+ write-owner Eywa) jsou **rozhodnuté a zapracované**. Zbývají tyhle implementační/scope volby:

1. **FS write-protection v lokálním dev provozu (přechod).** V kontejneru = read-only mount/práva
   (jasné). Mimo kontejner (dnešní `claude` session lokálně) read-only mount typicky není po ruce.
   Volba: (a) přechodně stát na path-check + denylist (vrstva 3) jako náhradě, dokud se nepřejde do
   kontejneru, NEBO (b) i lokálně zavést OS write-protection (chmod/ACL na engine cesty pod jiným
   vlastníkem) — robustnější, ale tře se s tím, že dnes všechno běží pod jedním uživatelem.
   **Doporučení Eywy:** (a) jako přechodný stav, (b) jako cíl spolu s kontejnerizací. Potvrdit.

2. **Pořadí rolloutu vs container-platforma.** R3 (FS vrstva) přirozeně sedí AŽ na kontejnerový
   běh. Otázka: pustit R1+R2 (engine schopnosti + politika + norma) **hned** jako samostatnou vlnu,
   a R3 navázat na container-iniciativu? NEBO počkat a udělat vše až s kontejnerizací? **Doporučení:**
   R1+R2 hned (commit-on-done + checkpoint + repair mají hodnotu i bez kontejneru a řeší incident),
   R3 s kontejnerem.

3. **Commit-on-done granularita.** Engine dnes commit nedělá vůbec. Commitovat na *každém* `done`
   uzlu (hodně malých commitů), nebo až na uzavření vlny (jeden commit/vlna)? Dotýká se git historie
   a memory „Pipeline done envelope mechanics". **Doporučení:** rozhodnout s tím, kdo vlastní commit
   message konvenci (Vision/Tony?) — Eywa to nevlastní.

4. **Write-owner engine_runtime: opravdu ani Eywa ručně?** Návrh říká běhový stav (`current-run.md`,
   `runs/**`) píše **jen engine**, i Eywa do něj smí jen přes `run.sh repair`. To je přísnější než
   dnešní `agents/eywa-meta.md §Write scope` (Eywa má `handoffs/**`, `agents/**`, ale ne engine
   runtime — takže konzistentní). Potvrdit, že tahle hranice je správná (Eywa = autorské cesty
   ano, běhový stav přes engine příkaz ne přímý edit).

5. **Kde definovat tool_profiles — frontmatter vs policy yaml?** §3a/§5 nabízí obojí. Volba ovlivní,
   jak `setup-claude-code.sh` projektuje `tools:`. **Doporučení:** policy yaml (jedno místo, snadný
   audit), frontmatter jako alternativa pokud chceme per-agent override.

---

## Verdikt Eywy (formát meta-agenta)

```
agent-system-health: FINDINGS — 1 (vynucení write-protection engine stavu chybí; dnes jen prompt + konvence)
role-overlap: NONE
write-scope-conflict: NONE
  návrh ZPŘÍSŇUJE write-scope: engine runtime cesty (current-run.md/STATE.md/runs/**) → read-only
  pro všechny agenty; zápis jen engine-proces. Eywa = write-owner autorských cest (graf/policy/agenti),
  konzistentní s agents/eywa-meta.md. Žádný NOVÝ konflikt nevzniká — naopak se uzavírá díra.
dispatch-graph: INTACT
proposed-changes: 0 applied (DESIGN-ONLY)
  engine (vrstva 1): 3 new schopnosti (commit-on-done, run.sh checkpoint, run.sh repair v core/run.py)
  FS (vrstva 2): write-protection engine cest (read-only mount/práva v kontejneru) — primární vynucení
  framework: 1 new policy yaml (write_protect + engine_owned_ops + deny_commands) + 2 neutrální checkery
             | modified: constitution §7 (write-scope engine cest) + §8 (kategorie „stav workflow enginu")
  adaptér Claude Code (§A, OPČNÍ): jen tools: projekce povinná; PreToolUse hook = redundantní pojistka
template-version: agent template beze změny; NOVÝ neutrální policy artefakt mimo agent template
revision: v1 (hook-centric) → v2 (engine+FS-centric, hook demoted to optional); L3 SCHVÁLENO ŠIRŠÍ 2026-06-20
```
