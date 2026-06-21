# Backlog: Session-agent-dispatch-bypass — vynucení, že routing dělá engine, ne orchestrátor

**Třída:** tech-debt (framework / hardening) · **Stav:** DESIGN-ONLY — čeká L3 · **Priorita:** střední (latentní, ne zachycený incident jako guardrails — ale stejná třída tiché korupce stavu)

> Autor návrhu: Eywa (meta). DESIGN-ONLY — nic živého nezavedeno. Žádná změna `core/run.py`,
> `result.py`, wrapperů, `settings.json` ani `constitution.md` neproběhla. Tento dokument je
> k posouzení rolloutu (L3), protože acceptance #1 („orchestrátor nespustí agenta bez předchozího
> engine volání") **mění chování orchestrátora a dotýká se `constitution.md §Filozofie #8**
> (řídí přes rozhraní, ne přes vnitřek). Detekční vrstva (acceptance #3) je non-L3 a samostatně
> rolloutovatelná.

> **VZTAH KE GUARDRAILS (`agent-command-guardrails.md`, vrstva 1 nasazena ac5a3a5+99b75c5).**
> Sourozenec, ale **jiná hrozba**. Guardrails chrání *obsah* engine stavu před korupcí
> (`git stash`/`reset` odloží `current-run.md` → stav se rozejde s realitou). **Tenhle item chrání
> *cestu*, jakou stav vzniká:** že posun flow VŽDY proběhne přes engine rozhraní (`drive`/`done`),
> ne LLM-inferencí orchestrátora. Guardrails říká „nepřepiš stav cizí rukou"; tohle říká „neposouvej
> stav vlastní úvahou — nech routing na enginu". Oba stojí na témže axiomu (#8: rozhraní vs vnitřek)
> a využívají touž infrastrukturu, kterou guardrails R1 přinesl (commit-on-done, checkpoint, ledger).

---

## 1. Problém + proč teď

Orchestrátor (Claude Code main session) je v dodávkovém flow **executor nad grafem**, ne
rozhodčí routingu. Engine (`run.sh drive`/`done` nad `pipeline/delivery.yaml` + `current-run.md`)
drží frontier, branching, ready-rule, gate logiku a re-flow/staleness. Orchestrátorova role:
dodat *úsudek a obsah uzlu*, ne *který uzel je další* (`constitution.md §Filozofie #7`,
`flow.md §Deterministický dispatch`).

**Riziko:** orchestrátor je LLM a může „z hlavy" usoudit, kterého agenta spustit a v jakém
pořadí — místo aby vzal ready množinu z `run.sh drive`. Když to udělá:

- **ledger se rozejde s realitou** — spustil se agent, jehož uzel engine za ready neoznačil;
  `completed`/`outcomes`/`frontier` neodpovídají tomu, co se reálně stalo;
- **branching se nevykoná** — graf má větvení (fork/router/judgment hrany); LLM-inference je
  obejde a flow „skočí" jinam, než graf předepisuje;
- **gate se přeskočí** — L2 review / blocking HALT (L3, deploy-approve) jsou uzly grafu; když
  orchestrátor dispatchne „další logický krok" sám, brána se nevyhodnotí (přeskočená L3 = přesně
  to, co `flow.md §Stop body` zakazuje);
- **re-flow/staleness se neaplikuje** — incremental rebuild a return-counter žijí v enginu;
  ruční dispatch je neaktivuje → regrese po opravě proklouzne.

Výsledek = **tichá divergence od kontraktu**, která se projeví až jako korupce stavu nebo
přeskočená brána — ne hned, ne hlučně. To je horší než guardrails incident: tam `git stash`
spadl viditelně a zachytil ho audit; tady flow „jakoby jede", jen na špatné koleji.

**Proč teď:** guardrails R1 (commit-on-done, checkpoint, repair) právě zavedl infrastrukturu,
o kterou se detekce bypassu může opřít — engine teď drží `frontier`/inflight jako strojový
záznam „co bylo nabídnuto k dispatchi". Dřív nebylo s čím porovnávat; teď je. A `constitution.md`
po guardrails rolloutu už ukotvuje §Filozofie #8 (rozhraní vs vnitřek), na který acceptance #1
přímo navazuje — chybí jen vynucovací mechanismus, stejně jako guardrails chyběl před R1.

---

## 2. Co repo ukazuje (ověřený stav, ne domněnka)

| Zjištění | Důsledek pro návrh |
|---|---|
| `run.sh drive` (`core/run.py:drive` + `print_dispatch`) spočítá frontier a vytiskne `DISPATCH <node> → agent:<short> model:<m>`; **při dispatchi přidá uzel do `frontier` (inflight)** (`run.py:339,350` → `runstate.add_inflight`) | engine UŽ DRŽÍ strojový záznam „co bylo nabídnuto k dispatchi" (inflight) — je s čím porovnávat realitu |
| `run.sh done <envelope>` (`result.py`) validuje `node in graph` (`result.py:155-156`), `outcome in RESULT_OUTCOMES`, severity/fault/model slovníky — ale **NEvaliduje, že node byl v inflight** (že ho `drive` reálně nabídl) | **jádro mezery:** `done` na uzel, který engine nikdy nedispatchnul, projde tiše. Detekce má kam sednout (existing inflight set), jen se dnes neptá |
| `print_dispatch` vytiskne `agent:` short jako **cast binding**, který engine vyřešil z grafu; orchestrátor ho jen opíše do `Agent(subagent_type=…)` (`flow.md §Deterministický dispatch` krok 2) | „kdo se má spustit" je deterministicky odvozený enginem — odchylka orchestrátora od `agent:` řádku je měřitelná |
| `flow.md §Orchestrator vs Subagent split` + §Auto-dispatch: orchestrátor „dispatchuje konkrétního subagenta", „čte handoff `to:`/`returns_to:`" | dvě cesty rozhodnutí o dalším kroku koexistují — graf (drive) a handoff-pole/úvaha; bez vynucení může orchestrátor sklouznout k druhé |
| **Legitimní přímý dispatch existuje a NESMÍ být zakázán** — `flow.md §Konverzační meta-agenti`: Watson session-resume, **Eywa** (`přidej agenta`/`audit agentů`), Monk ideace se dispatchují **mimo `delivery.yaml` graf**. Tyhle Eywa dispatche (meta práce) NEJSOU bypass | návrh musí ostře odlišit *delivery uzel* (musí jít přes engine) od *framework/meta dispatch* (přímý je správný) |
| `flow.md §Keyword triggery`: `přidej agenta`/`audit agentů`/`Eywa` → přímý `Agent(subagent_type=eywa-meta)`; session start → přímý Watson | trigger-based přímý dispatch = mimo graf = legitimní; hranice „delivery vs maintenance" je dnes implicitní v keyword tabulce, ne strojově deklarovaná |
| `core/run.py` má (po guardrails R1) `done` (+ commit-on-done), `checkpoint`, `repair`, `drive`, `status`, `next` — **NE žádný „dispatch-token" / „expected-next" mechanismus** | acceptance #3 (detekce) potřebuje NOVOU drobnou engine schopnost — vydat očekávanou ready množinu a porovnat s realitou |
| `runs/<run>/ledger.yaml` je append-only zdroj pravdy o tom, co se stalo; `current-run.md` drží `frontier`/`completed`/`outcomes` | detekce „done na ne-inflight uzel" je čistě deterministická nad existujícím stavem — kandidát na engine warn/log, ne LLM úsudek |
| `constitution.md §Filozofie #8` (rozhraní vs vnitřek) + §Filozofie #7 (routing/stav počítej scriptem) jsou už zakotvené (guardrails rollout) | norma pro acceptance #1 už existuje — chybí jen operační vynucení; acceptance #3 je čistě engine-native a non-L3 |
| `audit/` adresář v rootu existuje (prázdný); `constitution.md §8` odkazuje na audit log destruktivních operací | bypass-log má kam psát — existující konvence, ne nový artefakt |

**Klíčové oddělení (analogie guardrails):** engine **neuvidí Agent tool invocation orchestrátora**
— `Agent(subagent_type=…)` se spustí mimo engine-proces. Engine tedy nemůže *zabránit* spuštění
agenta tak, jak nemohl zabránit `git stash`. Co engine UMÍ: (a) vydat strojově „tohle je ready
množina" (`drive`), (b) při `done` zkontrolovat, že přicházející uzel byl v inflight (= byl
nabídnut), a nesoulad **zalogovat/varovat**. *Zabránit* spuštění (acceptance #1) leží na chování
orchestrátora / adaptéru — proto je L3, stejně jako u guardrails byla tvrdá vrstva odlišena od
detekční.

---

## 3. Žádoucí stav + vynucovací mechanismus (rozděleno dle síly vrstvy)

Žádoucí stav: **v dodávkovém flow je `run.sh drive` jediný zdroj „kdo je další".** Orchestrátor
opíše `agent:` z jeho výstupu, dispatchne, vrátí výsledek přes `run.sh done`. Framework/meta
dispatch (Eywa, Watson-resume, Monk) jede mimo graf přímo — a zůstává legitimní.

Mechanismus je seřazený dle **síly/vrstvy** (jako guardrails), od měkčí detekce po tvrdé vynucení:

### 3a. ENGINE detekuje + loguje bypass (acceptance #3 — non-L3, primárně rolloutovatelné)

Engine MUSÍ umět **strojově poznat**, že `done` přišel na uzel, který nikdy nebyl dispatchnut, a
že realita se rozešla s frontierem. Žádný LLM úsudek — čistá deterministická kontrola nad existujícím
stavem (`frontier`/inflight + ledger). Tři dílky:

1. **`done`-time inflight guard (WARN/log, fail-soft).** Když `run.sh done <envelope>` dostane uzel,
   který **není v `frontier` (inflight)** ani v legitimním ne-inflight stavu (terminal/join auto-advance,
   HUMAN-GATE continuation, re-flow target), engine **zaloguje varování** do ledgeru i do
   `audit/dispatch-bypass.md`: *„done na '<node>', který drive nikdy nedispatchnul — možný
   LLM-routing bypass."* Default fail-soft (neshazuje běh — jen značí), aby legitimní hraniční
   případy (resume, ruční `active`) nezablokovaly. *Tohle je deterministické jádro detekce a sedí
   přesně na mezeru z §2 (`result.py` dnes inflight nekontroluje).*

2. **Drift-check `status` vs realita.** `run.sh status` (už dnes přepočítává živý frontier ze stavu,
   `status.py:83-99`) rozšířit o explicitní řádek `dispatch-integrity: OK | DRIFT — <node> completed mimo frontier`.
   Orchestrátor (i app cockpit) tak vidí nesoulad **jako vlastnost stavu**, ne jako něco, co musí
   uhádnout. Deterministická projekce ledger↔frontier, ne úsudek.

3. **(Volitelně, silnější) dispatch-token / expected-next.** `drive` může při tisku `DISPATCH`
   řádku vydat krátký **dispatch-token** (hash ready množiny + node). `done` envelope token přiloží;
   engine ověří, že `done` patří k poslední vydané ready množině. Nesoulad token = tvrdší signál
   bypassu než pouhý inflight-check (chytí i „done na uzel, který byl ready dávno, ne v aktuálním
   kole"). **Volitelné** — inflight-guard (#1) pokrývá většinu; token je nice-to-have pro přísnější
   účetnictví. Token NESMÍ být povinný pro framework/meta dispatch (ten `done` neemituje vůbec).

> Vrstva 3a **nemění chování orchestrátora ani constitution** — jen dává enginu oči. Je
> implementovatelná samostatně a hned (R1 níže). Splní acceptance #3 doslova („přeskočení je
> detekovatelné a logované").

### 3b. ORCHESTRÁTOR/ADAPTÉR vynutí „nejdřív engine, pak dispatch" (acceptance #1 — L3)

Tvrdé vynucení („orchestrátor nespustí agenta bez předchozího engine volání") **mění chování
orchestrátora** a je tudíž L3 + dotek `constitution.md §Filozofie #8`. Dvě komplementární páky:

4. **Norma (tool-agnostická, do constitution/flow).** Doplnit `flow.md §Deterministický dispatch`
   (a případně `constitution.md §Filozofie #8`) o explicitní pravidlo: *„V dodávkovém flow orchestrátor
   spouští subagenta uzlu VÝHRADNĚ z aktuálního výstupu `run.sh drive` (ready množina + `agent:` binding).
   Dispatch dodávkového uzlu bez předchozího `drive`/`next` je porušení §Filozofie #8 (řídí přes rozhraní)."*
   Plus explicitní **carve-out** pro framework/meta dispatch (viz §4). Tohle je „pravidlo jako norma" —
   analogie commit-ownership v §Filozofie #9.

5. **Adaptérová pojistka (opční, redundantní — věc adaptéru, ne frameworku).** V Claude Code lze
   přidat pre-dispatch kontrolu (např. PreToolUse hook na `Agent` tool): pokud cílový `subagent_type`
   je **delivery-role agent** (ne na meta-allowlistu) a od posledního `run.sh drive`/`next` neexistuje
   čerstvý dispatch záznam pro tenhle uzel → varuj/zablokuj. **Není nositel řešení** — je to redundantní
   třetí linie; norma (#4) + engine detekce (#1–3) drží i bez ní. *Jak* se to v konkrétním nástroji
   realizuje (hook? wrapper? cockpit dispatch?) je věc adaptéru, ne tohoto návrhu.

### 3c. APP cockpit jako tvrdá hranice (kam princip míří, navazuje na container-platformu)

V cílovém provozu (`INITIATIVE-container-platform.md`) dispatch nedělá volná LLM session, ale
**app/cockpit nad engine rozhraním** (`POST /api/drive` → ready uzly → app spustí jen ty →
`POST /api/done`). Tam je „nejdřív engine, pak dispatch" **architektonicky vynuceno** — orchestrátor
fyzicky nemá jak dispatchnout uzel, který mu `drive` nevydal, protože dispatch jde přes API, ne přes
přímý Agent tool. To je tvrdá zeď analogická FS write-protection v guardrails §4.1 (paralela:
„klec zavírá vchod, ale skutečná hranice je zeď"). Tady je zeď = **API jako jediná dispatch cesta**,
ne důvěra v chování LLM session. Plný dopad řeší rollout container-platformy; tady jen ukotvujeme směr.

---

## 4. Hranice legitimní vs nelegitimní dispatch (kritické — návrh NESMÍ zakázat správný přímý dispatch)

Ne každý přímý `Agent()` je bypass. Existují **dvě třídy dispatche** a vynucení se týká jen jedné:

| Třída | Příklad | Jde přes engine? | Verdikt |
|---|---|---|---|
| **Delivery flow** (dodávka aplikace) | Vision spec → Ted contract → Bob/Peter → Joey → audity → merge | **ANO** — `run.sh drive`/`done` nad `delivery.yaml` | dispatch bez předchozího `drive`/`next` = **bypass** (§3 vynucení míří SEM) |
| **Framework / maintenance / meta** | **Eywa** (`přidej agenta`, `audit agentů`), Watson session-resume, Monk ideace, ruční debug enginu | **NE** — mimo `delivery.yaml`, trigger/keyword-driven (`flow.md §Keyword triggery`, §Konverzační meta-agenti) | přímý dispatch je **správný a žádoucí** — NENÍ bypass, vynucení se ho NEDOTÝKÁ |

**Jak se hranice deklaruje strojově** (aby ji detekce/pojistka uměla rozlišit, ne hádat):

- **Delivery-role agent** = agent navázaný (`agent:`) na uzel v `pipeline/delivery.yaml`. Tihle podléhají
  engine-routingu. (Strojově odvoditelné z grafu — žádný ruční seznam.)
- **Meta/maintenance agent** = agent, který NEMÁ uzel v `delivery.yaml` (Eywa, Watson, Monk) → na
  **meta-dispatch allowlistu**. Přímý dispatch těchto je legitimní vždy.
- Detekce (§3a #1) i opční pojistka (§3b #5) konzultují tenhle rozdíl: *je cílový agent navázán na
  delivery uzel?* ANO → vyžaduj předchozí engine volání; NE → propusť přímý dispatch bez výhrad.

> Klíč: **„tyhle Eywa dispatche NEJSOU bypass"** je strukturálně garantováno tím, že Eywa nemá uzel
> v `delivery.yaml` — ne výjimkou v kódu detektoru. Stejně Watson-resume a Monk. Hranice tedy plyne
> z grafu (zdroj pravdy), ne z hardcoded carve-outu.

---

## 5. Neutralita (tool-agnostický kontrakt)

Framework definuje **CO musí platit**, ne JAK to konkrétní nástroj zařídí:

- **Norma** (§3b #4) žije v `constitution.md`/`flow.md` (neutrální zdroj pravdy) — platí pro Claude
  Code, Cursor, Aider, API stejně.
- **Engine detekce** (§3a) žije v `core/run.py`/`result.py`/`status.py` — engine je tool-agnostický
  executor (`flow.md §Deterministický dispatch`: „LLM orchestrátor / runner / app = vyměnitelné
  executory nad stejným grafem+stavem").
- **Hranice delivery vs meta** (§4) plyne z `delivery.yaml` — společná pro všechny nástroje.
- **Adaptérová pojistka** (§3b #5) je **výslovně věc adaptéru** — Claude Code PreToolUse hook,
  Cursor mode-guard, app API gateway. Framework o napojení nic nepředepisuje, jen poskytuje
  rozhodovací vstup (je cílový agent delivery-role?).

Žádné CC-specifikum (hook, `settings.json`, `Agent` tool) v neutrálním zdroji pravdy. Stejná
disciplína jako guardrails: politika neutrální, vynucení v enginu/normě, adaptér jen projikuje.

---

## 6. Co tento návrh NEdělá (hranice)

- **Stále DESIGN-ONLY** — neimplementuje nic živého: žádná změna `core/run.py`, `result.py`,
  `status.py`, `flow.md`, `constitution.md`, wrapperů ani hooku. Vše k rolloutu (§7).
- **Nezakazuje legitimní přímý dispatch** — framework/meta dispatch (Eywa, Watson-resume, Monk)
  zůstává správný a nedotčený (§4). Návrh, který by je zakázal, je vadný.
- **Nezabraňuje fyzicky spuštění agenta enginem** — engine nevidí Agent tool invocation (§2);
  tvrdé „zabránění" leží na orchestrátoru/adaptéru (§3b) nebo app-API (§3c), ne na enginu. Engine
  umí detekovat + logovat, ne blokovat dispatch.
- **Neřeší sabotáž** — threat model je *LLM-drift orchestrátora* (usoudí routing z hlavy), ne
  zlovolný operátor. App-API hranice (§3c) jako vedlejší efekt drift znemožní úplně.
- **Nepřepisuje auto-dispatch prózu** v `flow.md §Auto-dispatch` (`to:`/`returns_to:` čtení) — jen
  ji podřizuje primátu `drive` (handoff pole jsou *obsah*, ne *routing autorita*; routing je graf).
- **Neřeší, jestli `run.sh next`/`drive` má vracet token** za hranici §3a #3 — token je opční;
  rozhodnutí o jeho povinnosti je ve „Co potřebuje rozhodnout".

---

## 7. Rollout (po L3, dle síly vrstvy — engine detekce napřed, vynucení a app později)

**Fáze R1 — ENGINE detekce (acceptance #3, non-L3, hodnota hned):**
1. `done`-time inflight guard (§3a #1) v `result.py` — fail-soft WARN + zápis do ledgeru a
   `audit/dispatch-bypass.md`; respektuje legitimní ne-inflight (terminal/join/gate/re-flow). + selftest
   (done na ne-inflight uzel → WARN; legitimní auto-advance → ticho).
2. `dispatch-integrity` řádek do `run.sh status` (§3a #2) — deterministická projekce ledger↔frontier.
3. Meta-dispatch hranice (§4) odvozená z `delivery.yaml` — helper, který řekne „je `<short>` delivery-role?".

**Fáze R2 — NORMA (zdroj pravdy, L3):**
4. doplnit `flow.md §Deterministický dispatch` o pravidlo „delivery dispatch jen z `drive`" +
   explicitní meta carve-out (§4);
5. (zvážit) doplnit `constitution.md §Filozofie #8` o větu, že LLM-routing dodávkového uzlu mimo
   `drive` je porušení „řídí přes rozhraní".

**Fáze R3 — dispatch-token (opční, silnější detekce):**
6. token v `drive`/`done` (§3a #3) + selftest — jen pokud R1 detekce v praxi nestačí.

**Fáze R4 — APP hranice (navazuje na container-platformu):**
7. `POST /api/drive` → ready uzly → app spustí jen ty (§3c) — tvrdé vynucení, řeší rollout
   container-iniciativy.

**Fáze R5 — adaptér (OPČNÍ, redundance):**
8. Claude Code PreToolUse pojistka na `Agent` (§3b #5) + RESTART session. **Bez této fáze je
   kontrakt splněn** (norma R2 + engine detekce R1).

---

## 8. Co potřebuje rozhodnout Vitek / orchestrátor před rolloutem

1. **Inflight guard: WARN vs BLOCK.** §3a #1 navrhuje fail-soft WARN (nezdrží legitimní hraniční
   případy — resume, ruční `active`). Alternativa: tvrdý BLOCK na `done` mimo inflight (přísnější,
   ale riziko zablokování legitimního ručního zásahu do enginu). **Doporučení Eywy:** WARN+log v R1
   (splní acceptance #3 bez rizika), BLOCK zvážit až po datech z logu, co reálně padá do warnu.

2. **Dispatch-token: zařadit, nebo stačí inflight guard?** §3a #3 je nice-to-have. Inflight guard
   (#1) chytí „done na nedispatchnutý uzel"; token navíc chytí „done na uzel ready z minulého kola".
   Stojí to za přidanou složitost envelope? **Doporučení:** nezařazovat do R1; rozhodnout dle toho,
   zda inflight guard v praxi propustí falešně-OK případy.

3. **Acceptance #1 (tvrdé „nespustí bez engine volání") — jak daleko teď?** Plné vynucení sedí
   přirozeně AŽ na app-API hranici (§3c, container-platforma). Do té doby stojíme na **normě
   (R2) + opční adaptér-pojistce (R5)**. Otázka: pustit R1+R2 hned (detekce + norma mají hodnotu
   a řeší acceptance #3 i #2 dnes), a #1 dotvrdit s app-API? **Doporučení:** ano — R1+R2 hned, tvrdé
   #1 s containerem (stejné pořadí jako guardrails: engine+norma napřed, tvrdá zeď s kontejnerem).

4. **Norma do `constitution.md §Filozofie #8`, nebo stačí `flow.md`?** §Filozofie #8 už pokrývá
   „řídí přes rozhraní" — LLM-routing je jeho porušení implicitně. Otázka: explicitní věta do
   constitution (silnější, ale mění ústavu = L3), nebo jen operační rozpis do `flow.md §Deterministický
   dispatch`? **Doporučení:** operační pravidlo do `flow.md` (kde už dispatch mechanika žije);
   constitution doplnit jen pokud chceme axiomatickou váhu — Vitek rozhodne.

5. **Kde žije „je `<short>` delivery-role?" hranice (§4).** Návrh ji odvozuje z `delivery.yaml`
   (agent navázán na uzel = delivery; jinak meta). Alternativa: explicitní `meta_agents:` seznam
   v policy. **Doporučení:** odvodit z grafu (zdroj pravdy, žádný ruční drift) — Eywa to vlastní
   konzistentně s cast-registrem; explicitní seznam jen pokud by hranice měla výjimky, které z grafu
   neplynou.

---

## Verdikt Eywy (formát meta-agenta)

```
agent-system-health: FINDINGS — 1 (engine nevynucuje, že delivery routing jde přes drive; done dnes
  nevaliduje inflight membership — result.py:155 kontroluje jen node∈graf, ne node∈inflight)
role-overlap: NONE
  pozn.: ostře oddělen LEGITIMNÍ přímý dispatch (Eywa/Watson-resume/Monk = mimo delivery.yaml graf,
  NENÍ bypass) od NELEGITIMNÍHO (delivery uzel dispatchnutý bez run.sh drive). Hranice plyne z grafu,
  ne z hardcoded carve-outu → žádné riziko zákazu správného přímého dispatche.
write-scope-conflict: NONE
  návrh nepřidává write do sdílených cest; detekce zapisuje do ledgeru (engine-owned) +
  audit/dispatch-bypass.md (engine/maintenance). Konzistentní s constitution §8 (běhový stav píše engine).
dispatch-graph: INTACT
  návrh naopak ZPEVŇUJE primát grafu jako routing autority (drive = jediný zdroj „kdo je další"
  v delivery flow); handoff to:/returns_to: degradováno z routing-autority na obsah.
proposed-changes: 0 applied (DESIGN-ONLY)
  engine (vrstva 3a, non-L3): done-time inflight guard (result.py) + dispatch-integrity řádek (status.py)
                              + delivery-role helper z grafu | volitelně dispatch-token (drive/done)
  norma (vrstva 3b, L3): flow.md §Deterministický dispatch pravidlo + meta carve-out
                         | zvážit constitution §Filozofie #8 explicitní větu
  app (vrstva 3c): POST /api/drive jako jediná dispatch cesta — navazuje na container-platformu
  adaptér Claude Code (§3b #5, OPČNÍ): PreToolUse pojistka na Agent — redundantní třetí linie
template-version: agent template beze změny; využívá infrastrukturu guardrails R1 (commit-on-done,
  checkpoint, frontier/inflight), žádný nový policy artefakt nutný (norma do flow.md/constitution)
relation: sourozenec agent-command-guardrails.md (oba stojí na §Filozofie #8); guardrails chrání
  OBSAH engine stavu před korupcí, tento chrání CESTU, kterou stav vzniká (routing = engine, ne LLM)
```
