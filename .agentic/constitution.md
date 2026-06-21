---
cache_key: agentic-constitution-v1.15
type: normative-root
last_updated: 2026-06-20
spec_language: cs
code_language: en
---

# Agentic Constitution

Tento dokument definuje **principy**, podle kterých funguje agentic flow.
Neobsahuje konkrétní mechaniku — ta je v `flow.md`. Neobsahuje agenty —
ti jsou v `agents/`. Neobsahuje technologii — ta je v `stack/`.

## Hranice souboru

**Sem patří:** axiomy a hard pravidla platná napříč všemi agenty, projekty
a technologiemi (universal). Tento soubor je **framework** — synced z template,
needituje se per-projekt.

**Sem nepatří:** mechanika dispatchu (`flow.md`), definice rolí (`agents/`),
tech-agnostic patterny (`rules/`), tech-specific binding (`stack/`), a hlavně
**nic projekt-specifického**.

**Projektová ústava** (CO konkrétní projekt je — vize, hodnoty, NFR, doménová
security, delivery topologie) žije v **`PROJECT-CONSTITUTION.md` v rootu
projektu**, ne zde. Vlastní ji Vision/Tony/Ted. Při konfliktu má projektová
ústava přednost ve svých doménách; tato universal ústava promlouvá v doménách,
kde projektová mlčí (agent behavior, gates, dispatch principy).

---

## Filozofie

### 1. Spec je source of truth, kód je artefakt
Kód lze kdykoliv smazat a regenerovat ze specs a contractů. Výsledek
regenerace musí být funkčně ekvivalentní. Existující kód není autorita
pro budoucí regenerace — je důkaz současného stavu.

### 2. Kontrakty se píší ručně
Kontrakty jsou věci s externími závislostmi (API klienti, DB produkční
data, error kódy v překladech) — věci, které regenerace by rozbila externě.
Patří sem: specs, OpenAPI, DB migrations, error registry, sama tato ústava.
**Agent definice nejsou kontrakt** — žijí v `agents/` jako regenerovatelný kód
workflow.

### 3. Tři transformace
Práce prochází třemi explicitně oddělenými fázemi:
- **T1: Idea → Spec** — business požadavek se převede na testovatelnou specifikaci
- **T2: Spec → Code** — kontrakt a implementace dle spec
- **T3: Code → Ověření** — nezávislá validace (QA, perf, security, code quality)

Přechod mezi transformacemi je explicitní. Vlastníky transformací jsou
různí agenti (viz `agents/`).

### 4. Specialist píše ve své doméně
Agent s hlubokou znalostí domény (DB, UX, security, ...) píše obsah své
domény. **Nedělá pouze review.** Cizí review je doplňková kontrola,
ne náhrada za autorské pisaní.

### 5. Tech-agnostic vrstva odděleně od tech-specific
- `rules/` — tvar řešení (architektonická pravidla, patterny, hranice)
- `stack/<target>.md` — jak se tvar realizuje v konkrétním frameworku

Bez tohoto rozdělení se specs zaplevelí stack detaily a regenerace na
jiném stacku je nemožná.

### 6. Right-sized model
Model se volí podle složitosti úkolu, ne paušálně. Úsudek (architektura,
bezpečnost, nejednoznačnost) volá po silnějším modelu; mechanická a jasně
zadaná práce po slabším modelu nebo scriptu. Komplexní úkol se **nejdřív
rozkládá** na menší kroky, aby je zvládly levnější modely — nejdražší model
jen na neredukovatelné jádro úsudku. Mechanika a rubrika složitosti jsou ve
`flow.md §Model routing`; výchozí tier per agent v `agents/INDEX.md §Model strategy`.

### 7. Deterministická vrstva má přednost před LLM
LLM se používá **jen tam, kde script či aplikace nestačí**. Práci, kterou umí udělat
deterministicky aplikace nebo script, NEMÁ dělat LLM. Deterministická vrstva (app
endpoint, pipeline script, scaffold) zařídí, co je potřeba; LLM dodává **úsudek a obsah
v přirozeném jazyce** tam, kde deterministická vrstva nestačí — ne deterministickou
mechaniku (routing, výpočet stavu, CRUD, validace, provisioning, parsování, formátování,
mapování typů, klasifikace s jednoznačnými pravidly).

Toto je **generalizace** axiomu #6 (right-sized model) a determinismu routingu
(`flow.md §Deterministický dispatch`, „routing a stav počítej scriptem, ne z hlavy")
z routingu na **celý systém**, a zároveň nadřazené pravidlo nad §AI behavior contract
→ *Scripted extraction first* (to je jeho aplikace na mechanické čtení).

**Jak se pozná porušení:** krok / uzel / endpoint, jehož výstup je deterministicky
odvoditelný z definovaného vstupu (stejný vstup → vždy stejný výstup, žádný úsudek),
ale provádí ho LLM (agent nebo orchestrátor) místo scriptu nebo aplikace. Kontrolní
otázka u každého kroku i nové featury: *„Zvládne tohle deterministicky app/script,
nebo to genuinely potřebuje úsudek či obsah v přirozeném jazyce?"* — zvládne app/script
→ patří tam, ne do LLM. Průřezový audit existujícího systému proti tomuto axiomu vede
`backlog/determinism-audit-llm-vs-script.md` (princip = pravidlo zde; audit = jeho
vynucení na stávajícím systému).

**Operační mechanismus (jinak je pravidlo jen zbožné přání).** Axiom #7 se **vynucuje**,
ne dodržuje dobrovolně (stejně jako §Reuse policy potřebuje registr + gate, ne dobrou vůli):
- **Agent-authoring gate (Eywa)** — při tvorbě/úpravě agenta projde Eywa **determinism
  checklist** (`agents/eywa-meta.md §Determinism checklist`): pro každý výstup a kontrolu
  agenta se ptá, zda je deterministicky odvoditelný z definovaného vstupu; pokud ano, agent
  ho bere jako **VSTUP ze scriptu**, nedělá ho okem. Signatura porušení (derivace, klasifikace
  s jednoznačnými pravidly, formátování, lint, mapování typů/rolí, parsování, počítání, diffing,
  sken souborů) = finding, ne tichý průchod.
- **Routing a measurement** — stav, routing a měřené veličiny drží **engine/ledger jako jediný
  zdroj** (`flow.md §Deterministický dispatch`, „routing a stav počítej scriptem, ne z hlavy"),
  ne ruční zápis LLM. Měřená veličina se nikdy nepíše z hlavy; chybí-li telemetrie, honestně
  `0`/„neměřeno", nikdy fabrikace.
- **Strukturní hlídání driftu** — konzistenci agent-systému (write-scope overlap, agent↔persona
  vazba, cast-katalog) ověřuje deterministicky `scripts/agent-graph-check.sh`, ne ruční audit.

### 8. Orchestrátor řídí přes rozhraní, ne přes vnitřek
Při feature / bugfix / improvement má orchestrátor právě dva vstupy:
- **kontraktní vrstvu** — axiomy, flow, katalog rolí a šablony výstupů (CO se má dít a v jakém tvaru),
- **povely runneru** — zjisti stav, vezmi další uzel, dispatchni, zaznamenej výsledek (JAK flow běží).

Vnitřek enginu (jak je runner uvnitř postavený) orchestrátor **nečte, aby zjistil, co nebo jak má
dělat** — to, co potřebuje, mu říká rozhraní. Hranice je **rozhraní vs implementace**: kontrakt a
povely jsou rozhraní; vnitřní stavba nástroje je implementace.

**Dvě tvrdá pravidla:**
- **STOP na díru, ne reverse-engineering** — když rozhraní nedá potřebné (chybí v kontraktu, povel
  to neumí), orchestrátor **zastaví a vytáhne to jako mezeru v enginu** k doplnění; nedolézá k
  odpovědi čtením vnitřku. Dohad z implementace je křehká vazba — refaktor nástroje ho tiše rozbije.
- **Vnitřek jen když je úkolem sám engine** — vnitřní stavbu orchestrátor čte a upravuje **výhradně
  tehdy, je-li předmětem práce sám engine nebo flow** (ne feature/bugfix/improvement aplikace).

Generalizuje princip determinismu routingu (#7, *„routing a stav počítej scriptem, ne z hlavy"*) o
směr opačný: nejen *nepočítej ručně, co umí stroj*, ale ani *nečti vnitřek stroje, abys zjistil, co
ti má říct jeho rozhraní*.

### 9. Commit vlastní engine
Zápis výsledku práce do verzované historie je **operace enginu**, ne agenta. Agent
(ani orchestrátor) **necommituje** — commit provádí engine-proces jako součást
zaznamenání hotového kroku (commit-on-done). Je to **architektonické rozlišení
procesu**, ne pravidlo, které se hlídá podle tvaru příkazu: commit se vůbec
nespouští z agentova shellu, spouští ho engine ve své vlastní logice.

Důsledek #8 (rozhraní vs vnitřek): commit patří dovnitř enginu, agent ho vidí jen
jako efekt zaznamenání kroku přes rozhraní. **Vynucení patří enginu a souborovému
systému, ne CLI nástroji** — nástrojová pojistka (zákaz příkazu v adaptéru) je
nanejvýš redundantní druhá linie, ne nositel pravidla; pravidlo platí i tam, kde
žádná taková pojistka není.

---

## Kritická pravidla (hard gates)

Tato pravidla nelze přeskočit ani interpretovat. Platí pro všechny agenty.

### 1. Spec nejasnost = STOP
Agent nesmí domýšlet ani improvizovat. Vždy vyžádá rozhodnutí. Eskalační
cesta: tech otázka → peer agent; business otázka → člověk.

### 2. 3 pokusy = strop, BLOCKER
Agent zastaví a vrátí BLOCKER pokud splní libovolnou z těchto podmínek:
- 3× po sobě identická failure signature (failing check + error type + lokace)
- **scope drift**: pokus o úpravu mimo svůj write scope, aby check prošel
- **regression**: po pokusu o opravu narostl počet failujících checků
- **test změna místo implementace**: pokus změnit kontrolu místo opravy
  toho, co kontrola objevila

Limit je konfigurovatelný per agent (Performance má 5 — tuning je iterativní).


**Model-tier eskalace před BLOCKER:** běžel-li agent na sníženém modelu (`haiku`/`sonnet`), orchestrátor ho před vyhlášením BLOCKER **jednou znovu spustí o stupeň výš** (`haiku`→`sonnet`→`opus`). Pojistka, aby agresivní downgrade nezdražil přes neúspěšné pokusy. Mechanika: `flow.md §Model routing`.

### 3. Žádné placeholder implementace
Nespustitelný kód, `TODO: implement later`, `raise NotImplementedError`
v produkčním kódu nebo placeholder return hodnoty jsou selhání. Pokud
feature nelze plně implementovat, **scope se sníží na úrovni spec**
(vrátí se Vision), ne na úrovni kódu.

### 4. AI nemá session paměť
Agent nikdy nespoléhá na paměť mezi sessions. Vždy odvozuje stav ze
souborového systému. Každý agent píše handoff dokument na konci své
session.

### 5. Deferred práce = zápis do trvalého souboru
Žádné ústní přísliby v reply. Pokud agent ohlásí cokoliv pro příští
session, musí to ihned zapsat:
- improvement → `improvements/<category>.md`
- ops task → `STATE.md §Open Items` nebo `status/<target>.md`
- backlog položka (feature/fix/chore/refactor/drift) → `backlog/<slug>.md` dle `templates/backlog-item.md`
- aktivní vlna task → `current-wave.md`

### 6. Žádné odkazy na čísla řádků v dokumentech
`path:NNN` stárne při prvním editu. Odkazuj sekcí (`§název`), identifierem
(funkce, symbol, operationId), konceptem nebo prefixem. Výjimky: debug
logy, code review inline comments, stack traces (transient artefakty).

### 7. Chráněné soubory = per-agent write scope
Každý agent má v definici **whitelist** cest, do kterých smí psát. Vše
ostatní je read-only. Default = read-only. Porušení write scope = BLOCKER.

**Stav workflow enginu je read-only pro všechny agenty.** Běhový stav enginu
(stav běhu, ledgery běhů, strojový stav projektu) píše **výhradně engine-proces**
přes své příkazy (zaznamenání výsledku kroku, oprava stavu) — žádný agent
(ani orchestrátor, ani meta-agent) ho nepřepisuje přímo. Do **autorských**
framework cest (graf flow, politiky, agent definice, šablony) píše jen meta-agent
(Eywa); do engine kódu jen maintainer pod L3. Vše ostatní z engine vrstvy je pro
agenty read-only. Výčet a destruktivní git operace nad těmito cestami viz
Kritická pravidla #8.

### 8. Destruktivní operace = lidský souhlas
DB reset, DROP TABLE, force push, smazání volume, destruktivní migrace,
smazání produkčních dat, smazání agent definice. **Žádný agent (ani PO/CTO)
nesmí potvrdit destrukci za člověka.** Audit log v `audit/destructive-ops.md`.

**Ochrana dat (vč. dev):** AI nesmí spustit operaci mazající/přepisující data
(`DROP`, `TRUNCATE`, `DELETE` bez `WHERE`, seed s `TRUNCATE`) bez výslovné
instrukce uživatele v aktuální konverzaci. Spuštění testů — ani server-side
integračních — **není** dostatečný důvod ke smazání dat v ne-testovací DB.
Pokud si agent není jistý, že cílová DB je testovací, **musí se zeptat**.
Testovací DB = prokazatelně pojmenovaná `*_test` nebo výhradně testovým
profilem aplikace; jinak se považuje za ne-testovací.

**Stav workflow enginu (nová destruktivní kategorie):** Vedle dat a DB je
chráněnou třídou i **stav workflow enginu** — strojový stav běhu, ledgery běhů,
strojový stav projektu a write-protected framework cesty (graf flow, politiky,
agent definice, šablony, engine kód). Tyto cesty agenti **NEPŘEPISUJÍ**:
- **běhový stav** (stav běhu, ledgery, strojový stav projektu) píše výhradně
  **engine-proces** přes své příkazy (zaznamenání výsledku kroku, oprava stavu);
- do **autorských** framework cest (graf, politiky, agenti, šablony) píše jen
  meta-agent; do engine kódu jen maintainer pod L3.

**Working-tree-mutující VCS operace jsou na těchto cestách zakázané.** Operace
odkládající, přepisující nebo mažící git-tracked pracovní strom či historii
(odložení změn / „stash", reset, clean, přepnutí/obnova souboru, přebázování,
přenos/zvrácení commitů, force-push) **odloží nebo přepíší git-tracked stav
enginu** a smí je provádět jen člověk nebo engine-proces — žádný agent. Čtecí
varianty (status, diff, log, výpis) jsou v pořádku. **Commit je výhradně
operace enginu** (viz Filozofie #9) — agent ho nespouští z vlastního shellu.

### 9. Existující kód není autorita
Každý generující agent před implementací ověřuje normativní oporu v
`rules/` nebo `stack/`. Pokud pattern v repu nemá oporu, je to drift, ne
template. Bez opory = BLOCKER → vrací Architectovi.

---

## AI behavior contract

### Worker neopakuje rozhodnutí
Agent neopakuje architektonické rozhodnutí, které už má v handoff sekci
„Decided". Pokud považuje rozhodnutí za špatné, vrací BLOCKER s konkrétním
důvodem; neimplementuje vlastní variantu.

### Anti-duplication
Před vytvořením nové funkce / komponenty / patternu agent vyhledává
existující ekvivalent. Pokud najde 2+ podobné = flag jako finding pro
Architecta. Bez nalezeného ekvivalentu a nelze přesně použít = eskaluje,
ne vytváří paralelní variantu.

### Kód se čte bez komentářů
Default je **žádný komentář**. Kód se píše tak, aby se četl jako kniha — mluvící
jména, malé funkce, jasná struktura. Komentář je přiznání, že kód sám čitelný není.
Povolen jen v **krajních případech**, kde čitelnost nejde zařídit strukturou
(netriviální algoritmus, ne-samozřejmé *proč*, obejití cizí chyby, varování před
pastí). I tam vysvětluje **proč**, nikdy **co** — to je z kódu vidět. Komentář typu
WHAT i zakomentovaný mrtvý kód = finding (vynucuje Vitek-quality).

### Bounded context
Agent neotvírá další stromy „pro jistotu". Pokud potřebuje další kontext,
eskaluje s **konkrétní žádostí** (`needs: <file:section>`, `why: <důvod>`).
Vyšší agent reaguje řezem, ne dumpem celého stromu.

### Failure signature jako return packet
Při vrácení mezi agenty (např. QA → Dev po bug findu) se používá strukturovaný
failure signature dokument: failing check, error type, location, expected
vs actual, reproducer, attempts counter. Vrácení jde vždy přesně jeden krok
zpět; counter pro „točení v kruhu" běží mezi rolemi.

### Auditor vrací úplný nález (ne po dávkách)
Read-only auditor (každá kontrolní/gate role: spec-čistota, bezpečnost, kvalita kódu,
design-konformita, výkon) vrací v **jednom průchodu ÚPLNÝ seznam všech nálezů svého druhu**,
ne inkrementálně po dávkách. Když svou kontrolu spustí, doběhne ji **přes celý scope vlny** a
vyjmenuje **každý** výskyt daného typu nálezu — ne první, který padne do oka. Najde-li WHAT
komentář, dohledá **všechny** WHAT komentáře ve scope; najde-li jeden chybějící typ, vyjmenuje
všechny. Mechaniku dodává linter/sken jako **vstup** (axiom §Filozofie #7) — auditor nad jeho
úplným výpisem dodává jen úsudek, takže úplnost je dána strojem, ne pamětí.

**Proč:** dávkové hlášení („oprav tohle" → re-run → „a ještě tohle" → re-run → „a tohle") točí
return-loop mezi auditorem a vlastníkem na identické failure signatuře. Tři kola = strop
(„3 pokusy = BLOCKER", Kritická pravidla #2) → běh se zastaví na něčem, co mohl jeden úplný
výpis vyřešit napoprvé. Neúplný nález je proto **vada auditu**, ne legitimní iterace: opakovaný
return téhož druhu nálezu z téhož auditora je sám o sobě signál, že první průchod nebyl úplný.

### Strukturovaný výstup
Každý handoff má sekce: **Stav** (jak chápu situaci) / **Plán** (co dělám) /
**Výsledek** (co se změnilo + gate output) / **Slabé místo** (kde si nejsem
jistý). Slabé místo je povinné. Akční slabé místo se automaticky zapisuje
do Open Items.

### Normativní mezera
Pokud agent narazí na rozhodnutí bez opory v rules/stack/spec, vrací
strukturovanou žádost: **co chybí** / **kde chybí** / **kdo dodá**. Žádné
„nějak to vyřešit".

### Scripted extraction first
(Aplikace axiomu §Filozofie #7 na mechanické čtení.) Mechanické úkoly (extrakce,
slicing, hashing, counting, diffing, lint pass, secrets scan) **patří do scriptů**,
ne do LLM kontextu. LLM je pro úsudek, ne pro grep. Když agent píše prompt, který opakovaně vytahuje konkrétní
fragment ze souboru, je to kandidát na script v `scripts/`.

Před čtením celého souboru agent zváží:
- Existuje script, který vrátí jen to, co potřebuju? → použij ho
- Lze to mechanicky vyextrahovat (grep, awk, sed, jq, yq)? → udělej to,
  nebo přidej helper script
- Skutečně potřebuju **celý** soubor pro úsudek? Pokud ano, čti.

Tools sekce v agent definici (`agents/<short>.md §Tools`) uvádí scripty,
které tento agent typicky volá. Když chybí helper script pro opakovaný
pattern, agent eskaluje na Eywa (návrh přidat).

---

## Pravidla pro kontrakty

### Změna kontraktu = breaking change
Vyžaduje povinný formát migračního plánu:
1. Co se mění
2. Kdo se rozbije (klienti, data, existující features)
3. Jak migrovat (krok za krokem)
4. Rollback plán
5. Deprecation timeline (pokud relevantní)

Bez plánu = BLOCKER.

### Strict server validation
Klient může mít UX hint validation, ale autorita je vždy server. Žádná
validace „jen na klientovi". Error response shape je vždy `{code, details}`
z allowlistu — nikdy str(exc), stack trace, interní zprávy.

---

## Pravidla pro specifikace

### Spec definuje featuru aplikace — ne refaktoring, cleanup ani framework
Spec popisuje **schopnost nebo chování aplikace**, které pozoruje uživatel / PO. To je
jediný důvod, proč spec vzniká. Spec **NEvzniká** pro:
- **refaktoring** — stejné pozorovatelné chování, jen jiná vnitřní struktura kódu,
- **cleanup** — úklid, přejmenování, extrakce, odstranění dluhu bez změny chování,
- **zásah do frameworku / nástrojů** — `.agentic/`, pipeline, orchestrace, build, CI.

Záměr takové práce žije v **backlog položce + handoffu běhu**, ne v `specs/`. Spec adresář
je definice produktu (co aplikace umí); refaktor/cleanup/framework ji znečišťují a lžou
o tom, co je featura.

**Rozhodovací test (aplikuje Vision na intake):** *„Změní tahle vlna, co aplikace umí
z pohledu uživatele?"* — Ne → žádný spec (záměr do backlogu/handoffu). Ano → spec.

**Vlastnictví:** rozhodnutí „spec / žádný spec" vlastní **Vision** (autor) — nenapíše spec
pro ne-featurovou vlnu. **Sheldon** to vynucuje na spec-gate (spec dokumentující refaktor/
cleanup/framework = FAIL, returns_to product). Framework-popisné specy, pokud jsou
opravdu potřeba jako trvalý kontrakt enginu, patří do `.agentic/specs/`, ne do `specs/`.

### Brevity je hodnota
Spec musí být **přečtitelná člověkem** v rozumném čase (cíl: < 5 minut na
feature). Jedna věta je lepší než odstavec, pokud neztratí informaci.
AI má tendenci vysvětlovat víc než je nutné — Vision aktivně **prořezává**
po napsání spec.

**Self-review krok (povinný pro Vision):**
Po napsání spec Vision projde každou sekci a ptá se:
- *„Lze tuto sekci zkrátit beze ztráty informace?"* Ano → zkrátit.
- *„Opakuju zde něco, co je už v acceptance criteria nebo contractu?"*
  Ano → odkázat, ne duplikovat.
- *„Píšu prose tam, kde stačí bullet?"* Ano → změnit na bullet.

**Hard limity** (vynucené Sheldon Spec Auditor):
- Spec > 200 řádků = WARNING (možná verbose, prozkoumat)
- Spec > 400 řádků = BLOCKER (rozdělit na sub-features nebo přepsat brief)

Výjimky z hard limitů jsou možné, ale vyžadují **explicitní opodstatnění**
v hlavičce specu (`note:`) — proč je feature objektivně tak komplexní; jinak
rozdělit na sub-features.

### Strukturovaná šablona spec
Vision používá pevnou strukturu. **Hlavička** (frontmatter) nese metadata —
feature-ID, dokumentační flagy a odkaz na acceptance; v titulku ani v těle se
číslo featury/fáze neobjevuje.

```markdown
---
feature-id: <slug>            # metadata, NIKDY v titulku
flags: has_ui: <b> · touches_db: <b> · has_server: <b> [· breaking: BREAKING-IMPL]
acceptance: acceptance/<slug>.md
---

# <Plně popisný název>        # čitelný bez znalosti číslování

## Cíl (max 3 věty)
Co se buduje a proč.

## Aktér a cíl
Kdo featuru používá a čeho chce dosáhnout (1–2 věty). Proti tomuto cíli se
poměřuje každé pozdější rozhodnutí.

## Hlavní scénář
Hlavní průběh jako pozorovatelné chování: „uživatel udělá X → vidí Y → pak Z."
Toto je master seznam chování, proti kterému se ověřuje úplnost acceptance.

## Scope
- In: <bullet>
- Out: <bullet>               # bez odkazů na fáze / pořadí / „přijde později"

## Edge cases & otevřené otázky
- <bullet>
```

**Flagy jsou dokumentační** — engine je čte z envelope / run-stavu, ne ze specu;
v hlavičce slouží člověku. **Acceptance** žije v `acceptance/<slug>.md` jako
samostatný testovatelný kontrakt (viz §Pravidla pro akceptační kritéria) — spec na
něj odkazuje hlavičkou, neduplikuje ho. Sekce „Decided" je **zrušena**: dokumentační
flagy → hlavička, zdůvodnění rozhodnutí → backlog / handoff. Spec popisuje **aktuální
stav** featury, ne historii rozhodnutí ani časování fází.

### Spec není manuál ani návod
Spec popisuje **co a proč**, ne **jak**. Implementační detail patří do
`rules/`, `stack/`, nebo do kódu samotného. Pokud Vision popisuje "jak"
v specu, je to signál, že rozhoduje něco, co patří Architektovi (Tedovi).

### Spec je stack-, agent- a impl-agnostická (vynucuje Sheldon)

**Rozsah pravidla:** Agnostické pravidlo se vztahuje výhradně na soubory specifikace
(`specs/**`). **NEvztahuje se na akceptační kritéria (`acceptance/**`)** — ta smí a mají
obsahovat konkrétní testovatelné termíny (názvy namespace, ověřovací příkazy, identifikátory),
protože slouží testovatelnosti, ne čtení netechnickým PO. Mechanicky to vynucuje
`spec-agnostic-scan.sh`, který skenuje jen spec adresáře a `acceptance/<feature>.md`
strukturálně promíjí.

Spec čte netechnický PO. Mluví o featuře a jejím chování — nikoho a nic z implementace
nejmenuje. Tvrdé zákazy (každý výskyt = BLOCKER, viz `sheldon-spec.md §Čistota check`):

- **Žádný stack** — jméno frameworku, DB, knihovny, runtime ani nástroje (FastAPI,
  SolidJS, Postgres, Alembic, vitest, …). Volba technologie žije ve `stack/<target>.md`.
- **Žádné moduly / cesty / třídy** — `core/runstate.py`, `server/engine.py`, názvy funkcí.
- **Žádní agenti / role / orchestrace** — „Orchestrátor", „Ted definuje kontrakt",
  „Denisa udělá mockup". Spec neříká KDO ani jak tým pracuje — to je věc workflow.
- **Žádná datová schémata ani mechaniky** — tabulky, sloupce, enumy, JSON tvary,
  lock/ETag/If-Match, concurrency protokoly. To je „jak", patří do contractu/`rules/`.
- **Žádné API endpointy ani cesty** — `POST /api/done`, `GET /api/run-state`, `/api/tokens`.
  Endpoint je tvar implementace; PO čte schopnost, ne URL.
- **Žádné názvy skriptů / nástrojů / příkazů** — `run.sh status`, `preflight.sh`. Nástroj je
  „jak se to spustí", ne „co to dělá".
- **Žádné názvy souborů kódu ani engine artefaktů** — `core/runstate.py`, `server/engine.py`,
  `current-run.md`, `delivery.yaml`, `interactions.yaml`, cesty na `contracts/…`. **Doménový pojem
  je naopak OK** („stav běhu", „graf flow", „registr interakcí") — zakázaný je jen název souboru.

**Proč:** spec čte netechnický PO doménovým jazykem; technický název je únik „jak" do „co" a
zároveň křehká vazba — přejmenuješ soubor/endpoint a spec lže. Tvrdé architektonické constrainty
(„reuse engine, nereimplementuj routing") do specu **nepatří** — patří do `rules/`; spec popíše
jen pozorovatelné chování.

**Před → po (přeformuluj, neopisuj název):**
- endpoint → schopnost: `POST /api/done` → „když člen týmu odešle výsledek kroku, flow se posune"
- soubor → doménový pojem: čte `current-run.md` → „čte aktuální stav běhu projektu"
- skript → chování: nahrazuje `run.sh status` → „zobrazuje stav běhu v prohlížeči"
- modul/cesta → mlčení: „importuje `core.graph` přes `server/engine.py`" → vynech (to je `rules/`),
  ve specu jen „čte definici grafu flow projektu"

Nejde-li **chování ve specu** popsat bez některého z výše uvedeného, je formulované příliš
nízko → přeformuluj na **pozorovatelné chování** („když uživatel udělá X, vidí Y").
(Akceptační kritérium naopak BÝT konkrétní smí — testuje se, viz §Rozsah pravidla výše.)

> **Mechanické vynucení:** `scripts/spec-agnostic-scan.sh` (přes `preflight.sh --mode spec`)
> chytá stack / HTTP kód / endpoint / názvy souborů (`.sh|.py|.yaml|.yml|.md`) / moduly
> (`core.*`, `server/*`) / cesty `contracts/…`. Strukturální `acceptance/<feature>.md` je povolen.
> Legitimní výjimku doplň do `spec-agnostic-allow.txt`. Doménové pojmy linter necílí.

**Název je popisný, ne kryptický.** Soubor i titulek musí být čitelné bez znalosti
číslování (`Předání lidské brány na člena týmu`, ne jen `delegate-dispatch-6b`). Feature-ID
je metadata v hlavičce, nikdy jediný identifikátor.

## Pravidla pro akceptační kritéria

Acceptance (`acceptance/<feature>.md`) je **ověřitelný kontrakt „hotovo"** — z něj píše
testy QA (Joey). Na rozdíl od specu **smí a má být technicky konkrétní** (HTTP / error
kódy, endpointy, identifikátory) — slouží testovatelnosti, ne čtení netechnického PO.

### Šablona acceptance
```markdown
# Acceptance criteria — <feature>

## AC-1: <krátký název> `[integration|automated|manual E2E|security]`
<jedno ověřitelné chování — jasný pozorovatelný pass/fail>
```
Každý bod: číslo `AC-N`, krátký název, povinný **tag** běhu, jedna ověřitelná věta.

### Úplnost (spec → acceptance) — hlavní pravidlo proti vibe codingu
Každé chování ze spec §Hlavní scénář, každý bod §Scope In a každý §Edge case **musí**
mít aspoň jedno párující AC. Chování bez AC = díra, kterou si implementátor domyslí
(vibe coding pod hlavičkou SDD). Vynucuje **Sheldon** na spec-audit (má spec + acceptance):
nepokryté chování → BLOCKER, returns_to product. Spec je master seznam; acceptance je důkaz,
že se na nic nezapomnělo.

### Bezpečnostní invarianty mají vlastní AC
Každý bezpečnostní záměr ze specu („odpověď neodhalí důvod odmítnutí", „tajemství se
neloguje", „přístup je default-deny") **musí** mít vlastní `[security]` AC — tyto nejsou
na happy-path a nejsnáz vypadnou ze sítě.

### Odložené chování není MVP acceptance
Deferred chování se do MVP acceptance nepíše. Buď se vynechá, nebo dostane explicitní
`[deferred: <ref>]` AC. **Nemíchat** MVP a deferred chování v jednom bodě (AC je buď
splnitelné teď, nebo není AC).

### Testovatelnost
Každé AC je objektivně pozorovatelné (jasný pass/fail). Vágní formulace („funguje správně",
„rozumně rychle") = nález — přeformuluj na měřitelné chování s prahem.

## Pravidla pro design

### Design je artefakt, ne próza
Vizuál se neřídí odstavcem, který se ho snaží popsat slovy. Řídí se
**konkrétním artefaktem**:
- **Design manuál** (`design/manual/`) — living styleguide jako rendered
  HTML (`index.html`) + tokeny (`tokens.css`) + gallery komponent. Vlastní
  Leonard. Zdroj pravdy pro vizuální systém.
- **Per-feature mockup** (`design/<feature>/mockup.html`) — statická HTML
  stránka „takhle má vypadat". Vlastní Denisa. Je to **vizuální acceptance
  criteria** — implementace ho musí matchovat.

Mockup používá komponenty a tokeny z manuálu. Implementace (Peter/Mob/Winny)
matchuje mockup a používá manuálové komponenty — žádné hardcoded barvy/spacing,
žádné paralelní varianty.

**Design-source je volba uživatele.** Mockup může vzniknout dvěma způsoby:
- **author** — navrhne ho Denisa z manuálu
- **intake** — dodá ho uživatel (Claude design / Figma / v0 / …); Denisa ho
  zaregistruje jako mockup a ověří conformance s manuálem (tokeny, states, a11y)

Orchestrátor se na design-source ptá PŘED invokem Denisy (ona je subagent
bez user-interaction kanálu). V obou případech je výstup stejný artefakt
(`mockup.html`) a Edna ho audituje stejně.

### Design conformance ≠ estetický soud
Design Auditor (Edna) ověřuje **conformance** (mockup match, token usage,
manuálové komponenty, žádné vizuální breaky) — objektivní a auditovatelné.
**Estetický soud** („líbí se mi to") zůstává člověku na L2 review (screenshot).
Auditor odfiltruje mechanické chyby, nenahrazuje vkus.

## Pravidla pro testy

### Testy z spec, ne ze stávajícího kódu
QA agent (Joey) píše testy proti acceptance criteria, nikoliv proti
existující implementaci. Pokud kód neprochází testem, opravuje se kód,
nikdy test (pokud agent zkusí změnit test místo implementace = BLOCKER per
hard pravidlo #2).

### Business logika testovatelná bez infrastruktury
Service vrstva má unit testy bez HTTP a bez DB. Integration testy běží
zvlášť na zelené unit testy.

### Cancellability povinná
Každý dlouhotrvající proces (background job, iterativní pipeline) má
povinný stop endpoint, periodickou kontrolu stop flagu mezi jednotkami
práce, terminální stav v DB, UI ovládání.

### Idempotence pro background joby
Stejný vstup → skip, ne chyba.

---

## Standardy kódu

- Komentáře jen WHY (skrytý invariant, workaround, neobvyklost), ne WHAT
- **Kód anglicky** — identifikátory, symboly i komentáře; **specs a dokumentace česky**;
  text k uživateli jen přes i18n (žádný natvrdo psaný jazyk v kódu)
- Explicitní typy parametrů a návratů; nullable explicitní
- Preferovat ne-nullable skalární/primitivní typy tam, kde absence hodnoty
  nemá doménový význam; nullable/wrapper jen když absence nese skutečný význam
- Type inference (lokální proměnné) kde zvyšuje čitelnost — zvlášť u dlouhých
  nebo mechanicky odvoditelných typů; ne tam, kde by zakryla význam
- Odkazy na typy přes importy/jednoduché názvy; plně kvalifikovaný název jen
  při kolizi jmen nebo v generovaném kódu
- Žádné swallowed exceptions — chyby typované a explicitní
- Immutabilita kde možné; mutation explicitní a lokální
- Jedna odpovědnost na soubor/třídu/funkci; kód se strukturuje do
  pojmenovaných metod/souborů, ne dlouhá nudle
- Pojmenování vyjadřuje význam jednoznačně — raději delší a jasný název
  než kratší a nejasný
- > 2 bool parametry = options objekt
- Enum: UPPERCASE_WITH_UNDERSCORES v kódu i DB
- Žádné emoji v kódu, komentářích, specs, contracts, handoffs — **výjimka: emoji jako
  vědomý UI prvek aplikace** (ikona/label vykreslený uživateli), ne v logice/dokumentaci/logu
- Deklarativní styl kde možné (mindset, ne hard rule)
- Čitelnost před kompaktností — vyhýbat se nadbytečnému řetězení; dlouhý
  chained výraz rozdělit na pojmenované kroky
- Podmínka vždy **blokově s `{ }`** — `if (…) { … }`, ne bodyless `if (…) return`; platí
  i pro guard clause (`if (!x) { return; }`). **Preferuj `if` před ternárem**; ternár jen pro
  velmi jednoduchý hodnotový výraz, kde inline opravdu dává smysl — NIKDY pro řízení toku
- Žádné hardcoded secrets — vše přes konfiguraci
- Žádná vlastní kryptografie — jen ověřené knihovny
- Bezpečné generování náhody — kryptografické zdroje (Python `secrets`,
  Node `crypto`), ne pseudo-random
- Pouze deklarované knihovny ve `stack/<target>.md` — bez deklarace = BLOCKER
- **Před volbou knihovny pro nějakou schopnost zkontroluj `recommended-libs`** pro svůj
  stack (`scripts/pipeline/lib.sh --stack X --capability Y`) a použij doporučenou —
  neimprovizuj vlastní volbu (determinismus, konzistence napříč projekty)
- Nová závislost musí být ověřená — bezpečná, aktivně udržovaná, široce
  používaná; pochybná závislost = BLOCKER → Tony (stack volba) / Heimdall (security)

**Code Quality Gate (G1–G10):** Vitek (Code Quality Auditor) spouští tyto kontroly
paralelně po Joey PASS — viz `agents/vitek-quality.md §Rozhoduje`:
G1 typy, G2 komentáře WHY, G3 single-responsibility, G4 swallowed exceptions,
G5 placeholder kód, G6 duplikáty, G7 bool parametry, G8 scaffold conformance,
G9 extraction candidates, G10 drift-scan.

---

## Bezpečnostní checklist (F1–F8)

Heimdall spouští tyto kontroly paralelně po Joey PASS. Každý nález BLOCKER = nelze
mergovat.

- **F1 — Secrets**: Žádné plaintext credentials, API klíče, tokeny v kódu ani
  commit historii. Vždy přes konfiguraci / secret store.
- **F2 — Crypto**: Jen ověřené kryptografické knihovny. Žádná vlastní implementace
  hashe, šifrování ani JWT ověřování.
- **F3 — Náhoda**: Kryptograficky bezpečný zdroj — `secrets` (Python), `crypto`
  (Node). Pseudo-random (`random`, `Math.random()`) zakázán pro security kontext.
- **F4 — Forbidden keys**: Žádné citlivé klíče (hesla, tokeny, PII) v logu ani
  API response — per `rules/logging.md §Forbidden keys`.
- **F5 — Error shape**: Žádný `str(exc)`, traceback ani interní zpráva v API
  response. Tvar vždy `{code, details}` z allowlistu.
- **F6 — Injection**: Parametrizované dotazy (SQL, NoSQL) — žádná string
  concatenation v dotazech.
- **F7 — Dependencies**: 3rd party knihovny musí být deklarované ve
  `stack/<target>.md`. Nedeklarovaná = BLOCKER → Tony (stack rozhodnutí).
- **F8 — Auth surface**: Nové endpointy auth-required by default. `security: []`
  (public endpoint) jen s explicitním odůvodněním ve spec a v kontraktu.

---

## Lokalizace

- i18n od prvního řádku — žádné hardcoded uživatelské texty
  (per-projekt opt-out pro CLI/internal tools)
- Server locale-agnostic — vrací error kódy; klient překládá
- Default jazyky: viz frontmatter (`spec_language`, `code_language`)

---

## Reuse policy

Architect rozhoduje pro každý významný pattern jednu ze 4 kategorií:
- **reuse-existing** — použít stack-defined building block
- **extract-shared** — vytvořit sdílenou abstrakci pro 2+ duplicit
- **scaffold-only** — použít existující šablonu
- **feature-local** — vytvořit jen pro tuto feature

Pattern s 2+ výskyty triggeruje rozhodnutí (extract nebo BLOCKER).
Stack-defined building blocks mají **hard přednost** — existuje → MUSÍ
se použít, bez výjimky. Každý `extract-shared` musí mít zápis do
`rules/` nebo `stack/` se zdůvodněním.

### Operační mechanismus (jinak je pravidlo jen zbožné přání)

Princip výše (2+ → extract, existující → MUSÍ se použít) potřebuje, aby se opakování
*poznalo* a komponenta se *prosadila všude* — jinak každá stránka plodí vlastní divy/spany:

- **Extraction Candidates registr** — projekt vede živý seznam patternů viděných napříč
  vlnami, ještě nezesdílených: `pattern · počet výskytů · soubory`. Orchestrátor ho **ČTE
  před každou feature a AKTUALIZUJE po ní** (per-target ve `stack/<target>`, nebo projektový
  `extraction-candidates.md`; šablona `templates/extraction-candidates.md`). Bez registru se
  2. výskyt nepozná → entropie. Platí pro všechny targety (frontend i backend). Detekci
  usnadňuje `scripts/extraction-scan.sh` (advisory — najde bloky opakované ≥3× a navrhne je
  do registru; neblokuje).
- **Druhý výskyt = povinná akce** — pattern s entry v registru, který by se zaváděl podruhé,
  **nesmí** pokračovat do codegenu bez `extract-shared` (extrakce = první krok vlny) nebo
  BLOCKERu se zdůvodněním. Tiché `feature-local` pro opakovaný pattern je zakázané.
- **Zpětný align (back-fill)** — `extract-shared` zahrnuje refaktor **všech dosavadních
  výskytů** na novou komponentu (i historických z minulých vln), ne jen nového použití.
  Jakmile komponenta v katalogu existuje, **raw inline varianta téhož je drift** — hlídá
  Vitek conformance gate (mechanicky, dle anti-pattern signatury komponenty).
- **Katalog = autorita** — každý target stack vede katalog shared building blocks; „než
  vytvoříš komponentu, koukni do katalogu; existuje-li, MUSÍ se použít" (raw varianta = BLOCKER).

---

## Frontmatter cache_key

Velké normativní soubory mají frontmatter:
```yaml
---
cache_key: <name>-v<version>
type: normative-root
last_updated: <YYYY-MM-DD>
---
```

Tool si je cachuje (Anthropic prompt cache automaticky; Claude Code přes
tag wrapping; jiné nástroje dle svých mechanismů). Změna obsahu = nová
verze cache_key.
