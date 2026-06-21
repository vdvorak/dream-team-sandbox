# dream-team — Project Constitution

Projektová ústava. Doplňuje universal `constitution.md` (= agentic zákon, JAK agenti
fungují) o to, **CO tento projekt je**. Při konfliktu má v doménách níže přednost.

Tento projekt je **self-hostovaný**: dream-team je zároveň framework (nástroj) i projekt
budovaný tímhle frameworkem. Tahle ústava je **kanonický north-star** (§Vize a mise dole);
node-editor app-vize žije v `backlog/app-platform.md`.

Změna tohoto dokumentu = **L3** (fundament projektu).

---

## Vize a mise   <!-- vlastní Vision -->

**Deterministický agentní engine, který z issue vyrobí stabilní, předvídatelný výsledek** —
spec → plán → todos → delegace → implementace → test → ověření. Jasné vstupy → jasné výstupy,
minimální diverzita. Dvě aplikace na stejném stacku mají díky scaffoldům strukturálně shodný
zdroják. Spec je pravda, kód je artefakt.

Dlouhodobý cíl je **platforma pro tvorbu agentních flow** (samostatná app konzumující tenhle
engine — „stejný engine, dvě UI"):
- **Node editor** — řetězení agentů jako uzlů; spojí se jen kompatibilní I/O (typované porty).
- **AI-callable issue systém à la Jira** — board issues přes API, ale callable agenty.
- **AI-callable todos** — token-gated přechody (`/done` posílá výstupy → vstupy dalšího uzlu);
  vzor `vtodo` (scoped token, optimistic concurrency přes verzi/If-Match → konkurence bez kolizí).
- **Live view + in-app human-interakce + bez terminálu** — vidíš co flow dělá; do běhu jde **vstoupit**,
  ale vždy přes **specializovaný typed interface dle typu interakce, ne terminál** (např. rozhodnutí
  o designu: *upload vlastního HTML návrhu* XOR *spustit Denisu*). Každý typ interakce je deterministicky
  definovaný (human-interaction registry). Live session agenta jen jako emergency escape hatch.

Engine, co se staví teď (soubory + graf), je **základ** té appky, ne přechodné řešení: app jen
renderuje a řídí to, co engine zapisuje do souborů. Proto „vše v souborech + typované I/O +
strukturované přechody" = app-ready.

## Hodnoty   <!-- Vision + Tony -->

- **Determinismus + konzistence = akceptační kritérium**, ne feature. Ověřuje se scaffold-
  conformance, standardizovanou strukturou a typovaným I/O — ne dojmem.
- **Žádný vibe coding** — každý artefakt má oporu ve spec a v pravidlech; diverzita se aktivně minimalizuje.
- **Script/scaffold-first** — mechanická práce scriptem/scaffoldem; LLM jen tam, kde je úsudek.
- **Člověk dělá klíčová rozhodnutí** — cílem není odstranit člověka, ale dát mu deterministický
  stroj, kde rozhoduje tam, kde to dává smysl (gates, human-interakce).
- **Tool-agnostic, stav v souborech** — nic nespoléhá na paměť konkrétního nástroje; každá
  session naváže ze souborů i po výpadku/přerušení.

## Cílová skupina   <!-- Vision -->

**Primárně**: solo developer (Vitek), který staví software přes agentní flow — hází issues, dostává
konzistentní výsledky. **Výstup flow**: software projekty (každý sám o sobě standardní projekt
stejného tvaru jako tenhle). **Budoucně**: uživatelé node-editor platformy, kteří si skládají
vlastní agentní flows. **Interní nástroj** vyvíjející se v platformu — zatím ne SaaS, ne B2C.

## Co projekt JE / NENÍ   <!-- Vision -->

**Je:**
- Deterministický agentní flow engine (graf rolí + stav v souborech) — spec-driven delivery pipeline.
- Základ budoucí node-editor platformy (engine, který app konzumuje).
- Self-hostovaný: framework je svým prvním projektem (cílem je, aby flow pracovalo samo na sobě).

**Není:**
- Chat-driven „vibe" asistent — nic se neimprovizuje.
- Tool-locked nástroj — nic nesmí spoléhat na paměť/feature konkrétního toolu (Claude Code je jen jeden adaptér).
- SCRUM / sprint manager — seskupení issues do sprintů je pozdější vrstva nad hotovým jádrem (odloženo).
- **Ta aplikace samotná** — node-editor app je *samostatný budoucí projekt* konzumující tenhle engine.

## Nefunkční požadavky (NFR)   <!-- Tony + Ted -->

- **Bezpečnost**: budoucí app = **token-gated přístup** (vzor `vtodo`): každý actor sahá jen na to,
  k čemu má scoped token; žádný cross-scope přístup. Engine je lokální soubory (žádné secrets v kódu).
- **Performance**: determinismus je důležitější než rychlost; **cost + čas se účtuje per issue** (run ledger).
- **Dostupnost**: vývojový nástroj, není life-critical.
- **Compliance**: žádná (interní dev nástroj).
- **Lokalizace**: **specs/dokumentace česky, kód (identifikátory) anglicky**; CLI hlášky enginu česky
  (interní nástroj — opt-out z i18n). Doloženo `scripts/pipeline/core/README.md`.

## Doménová security pravidla   <!-- Tony, Heimdall input -->

- **Token scope (app vrstva)** — bearer token vázaný na jeden zdroj (issue/sekce/flow); agent nemůže
  sahat mimo svůj scope. Vzor `vtodo`: AI je first-class writer, ale jen v rámci svého tokenu.
- **Optimistic concurrency** — každý write nese verzi (`If-Match`); mismatch = 409. Tím se vyřeší
  paralelní agenti/issues bez tvrdého file-lockingu (file-locking jen kde to nestačí).
- **Engine**: stav běhu v souborech; runtime soubory (issue data, db) se necommitují (`.gitignore`).

## Delivery topologie   <!-- Tony + Ted -->

- **Engine (jádro, hotové)**: Python3 + tenké POSIX sh shimy, file-based (graf + stav v md/yaml),
  bez DB, bez deploye. CLI/knihovna. Viz `scripts/pipeline/core/`.
- **Platforma (cíl)**: jeden `web` target — **backend Python (FastAPI)** + **frontend SolidJS** +
  DB + **Docker Compose** deploy. App konzumuje engine přes `/done`-style přechody nad souborovým stavem.
- **Docker dev-run** vždy, kde to platforma dovolí (nezávislost na hostu = determinismus prostředí).
- **Newest-stack** — scaffoldy drží nejnovější stabilní verze.

## Doménové hard rules   <!-- load-bearing invarianty (z VISION §2/§6) -->

Neporušitelné invarianty systému (vynuceno enginem/check/gates):

- **I1 — Strict spec-driven**: každý artefakt vychází ze spec; kód je odvozenina. (`constitution §1`, `check C7`)
- **I2 — Stav a handoffy v souborech**: žádná tool-paměť; session naváže i po výpadku. (`STATE.md`, `current-run.md`, `handoffs/`)
- **I3 — Tool-agnostic**: per-tool jen generovaný tenký adaptér.
- **I4 — Script/scaffold-first**: LLM jen kde je úsudek. (`constitution §Scripted extraction first`)
- **I5 — Standardizovaná struktura projektu**: scaffoldy + `project-config` cesty.
- **I6 — Vždy programátorská pravidla**: `constitution §Standardy kódu` + `rules/`; Vitek gate G1–G10.
- **I7 — Typované I/O**: uzly spojí jen kompatibilní výstup→vstup. (`pipeline/artifacts.yaml`)
- **I8 — Cost + čas per issue**: run ledger (`scripts/pipeline/core/ledger.py`).

Zamčená rozhodnutí:
- **Scripty: Python3 + tenké POSIX sh** — netriviální logika v Pythonu, sh jen glue.
- **Determinismus + konzistence = akceptační kritérium** celého systému.
- **`vtodo` = vzor app vrstvy** (token-gated, `/done` přechody, optimistic concurrency).
- **SCRUM odložen** — až pozdější vrstva nad hotovým enginem.
- **App = samostatný budoucí projekt** konzumující engine (ne součást tohoto repa).
- **Delivery hranice (self-host):** delivery graf dodává **PRODUKT** frameworku (engine teď, app
  potom) — engine kód / registry / schémata tečou standardními rolemi (product→architecture→backend→
  qa→audit; ověřeno P5). **Agent-authoring** = Eywa (meta-agent, mimo delivery graf); **governance**
  (constitution/flow/grafu) = deliberate změny, ne issue-flow. Meta mimo graf = správná hranice, ne gap.
- **Flag scope:** project flagy (has_server/db/deploy/targets/design_source) = schopnost projektu;
  feature flagy (has_ui/touches_db/has_signature) = co feature touchne. Routing = project && feature
  (viz `vocabulary.yaml`).
- **spec_language: cs · code_language: en**.
