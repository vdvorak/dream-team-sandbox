---
wave: 2026-06-11-init-determinism
from: orchestrator (claude session)
to: next-session
type: milestone-handoff
returns_to: null
---

# Handoff: init determinismus — APPLY engine (resolve→apply gap zacelen)

Navazuje na `handoffs/2026-06-11-formatters-feature-library/HANDOFF.md` (v0.36). Vstupní bod
diagnózy i plánu: **`init-determinism.md`** (root) — kompletní blueprint.

## Proč (dogfood)

2-agent dogfood (java-quarkus, feature `auth`, **jedna lidská věta** přes headless `claude -p`):
ze stejného vstupu `ja` předpřipravenou auth nasadil, `jb` ji minul. Diagnóza: **scaffold.sh i
feature.sh jen RESOLVNOU (co/kam), neAPLIKUJÍ** — copy/rename/overlay dělal LLM → divergence.
Framework měl resolver vrstvu, **apply vrstva chyběla**. Root cause = **(a) chybějící mechanika**,
ne (b) blbý agent.

## Výsledek (co bylo postaveno)

- **`scripts/pipeline/apply-feature.sh`** — deterministický feature overlay: copy dle `feature.yaml`
  `apply:` manifestu + přepis `base_package` (cesta+obsah) + číslování migrací na další volné `V`,
  option-aware (jwt/session). Generic stacky (`package_root: null` → python/solidjs, bez rename).
- **`scripts/pipeline/compose.sh`** — founding APPLY engine: copy scaffold + package-rename
  (cesta+obsah+`rootProject.name`) + JWT issuer z `--name` + apply features (reuse apply-feature).
  Naming pravidlo `base_package = f(název)` (autonomně `com.<slug>`, v produktu UI přes `--package`).
- **`feature.yaml`** — strojový `apply:` manifest pro auth: java-quarkus + python-fastapi
  (per-option `files`/`migrations`, `package_root`, `wiring`).
- **`watson-interviewer.md` (v1.9)** — founding compose krok = `compose.sh` (ne ruční overlay).
  RESOLVE = scaffold.sh/feature.sh; APPLY = compose.sh/apply-feature.sh.
- **`init-determinism.md`** — blueprint (resolve vs apply, A/B leak třídy, fix architektura, capstone).

## Důkaz

- Standalone: stejné vstupy → **byte-identický** projekt (jwt i session, java i python), 0 zbytků
  `com.example`, jwt≠session vybírá správné soubory.
- **Capstone re-run** (dvě headless sessions, stejná věta, wired compose): oba vyrobily
  **byte-identický `server/`+`contracts/` až na 2 drobnosti** = čisté (b) (agent po compose edituje
  navíc). Velká (a) divergence z 1. dogfoodu **zacelena**. Issuer residual zacelen v compose;
  zbývá stray `.gitignore` (agent-disciplína).
- Guardraily nedotčeny: `selftest.sh` 9/9, `check.sh` OK.

## Decided (rozhodnutí — neopakovat)

- **(a)/(b) diskriminátor:** „kdyby krok dělal dokonalý člověk se stejnými docs+tools, vyšlo by to
  deterministicky?" NE → (a) chybí mechanika (postav script/scaffold). ANO ale agent se rozešel →
  (b) agent/chaining. **(a) díry maskují (b)** — zacel (a), re-run zviditelní (b). Drží I4
  ([[scripts-not-llm-enforcement]]).
- **Třída A (stack/platforma/features) zůstává human-in-loop v produktu** (budoucí app = klikání v UI →
  strukturované vstupy). Defaulty jen jako autonomní dogfood fixtura.
- **compose = applier, feature.sh/scaffold.sh = resolvery.** APPLY je nová deterministická vrstva.
- **Audit-once vyžaduje byte-věrnou kopii** — LLM overlay rozbíjí Heimdallův audit security kódu.

## Zbývá (next)

- **Wave-pipeline (a)/(b) diagnóza** — druhá půlka „celého systému". Founding je hotový; per-issue
  flow (T1→T2→T3, `run.sh drive`/`next.sh`) zatím dogfoodem netestován (oba běhy stojí na foundingu).
  Routing je (a)-pokrytý (next.sh); otázka je per-node apply + agent chaining. **Tohle je hlavní next.**
- **wiring auto-insert** — marker-based `include_router` do python `main.py` (zatím jen warning).
- **agent ad-hoc edit disciplína** — po compose agent nemá ladit strukturu ručně (stray `.gitignore`).
- **build-verify java auth (#12)** — pořád pending (gradle/gradlew chybí v prostředí).
- compose: resolvovat scaffold přes manifest (`produces`/`docker_dev`/`newest`), ne jen path; klienti.
- auth `oauth`/`mfa` varianty (planned).

## Slabé místo (POVINNÉ)

- **Compose není build-ověřený** — generuje konzistentní package, ale `./gradlew build` neproběhl
  (no gradle). Strukturální determinismus ano; kompilace neověřena. Security-critical → před nasazením
  build + QuarkusTest.
- **Wave-pipeline determinismus je NEZNÁMÝ** — vše výše řeší jen founding. Per-issue flow může mít
  vlastní (a) díry (per-node apply) i (b) (chaining). Netestováno.
- **wiring auto není** — python feature potřebuje ruční router registraci (compose ji nevloží).
- **Re-run residual (b)** — agent stále občas edituje navíc (`.gitignore`); compose to neřeší
  (není to jeho scope), patří do agent-disciplíny.
