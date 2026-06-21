---
wave: 2026-06-11-formatters-feature-library
from: orchestrator (claude session)
to: next-session
type: milestone-handoff
returns_to: null
---

# Handoff: candidate-detekce + formatter enforcement + EN + P7 feature library (auth)

Navazuje na `handoffs/2026-06-10-scaffolds-engine-reuse/HANDOFF.md` (v0.32). Tahle wave: **v0.33 → v0.36**.
Vstupní body: `VISION.md` (§5 roadmap má teď P7) → `constitution.md §Standardy + §Reuse` → `templates/features/`.

## Stav (kde to je)

Engine + scaffoldy + reuse governance byly hotové. Tahle wave přidala: (1) **mechanické vynucení
konzistence scripty** (formattery + lintery v gate, ne LLM ruční práce), (2) **kód anglicky**
(překlad ~60 scaffold zdrojáků), (3) **P7 feature library** — cross-project moduly se spec+impl,
pilot **auth** (jwt | session). Vše buildnutelné ověřeno; java auth strukturální (viz Slabé místo).

## Výsledek (co bylo postaveno)

- **v0.33 — candidate auto-detekce (C, advisory):** `scripts/extraction-scan.sh` — deterministicky
  najde bloky opakované ≥3× (copy-paste) → návrh do Extraction Candidates. Neblokuje (jen report).
- **v0.34 — formatter/style enforcement (scripty, ne LLM = constitution I4):**
  - per-stack: python `ruff` (format+lint, bez SIM), TS `prettier`(semi:false)+`eslint`(curly),
    flutter `dart format`+curly lint, java `spotless`(googleJavaFormat).
  - `scripts/format-check.sh` (unified, detekuje stacky, `--fix`) → **wired do Vitek gate**.
  - pravidla (`constitution §Standardy`): if vždy `{ }` + prefer-if (ternár jen prostý hodnotový),
    emoji zákaz + výjimka UI-ikona, **kód anglicky / specs+docs česky**; ID=UUID default
    (`rules/backend §Identifikátory`). `eslint --fix` srovnal bodyless if (nástroj, ne já).
  - **komentáře CZ→EN** ve všech scaffoldech (~60 souborů; `cs.json`/`app_cs.arb` zůstaly CZ locale).
- **v0.35 — P7 feature library + auth pilot:**
  - `feature` osa scaffoldu: `templates/features/<f>/` = `feature.yaml` (varianty + **options** +
    Watson otázka) + stack-agnostic `spec.md` (vždy) + per-stack `impl/` (jen security-critical →
    **audit-once** Heimdall, regenerate-never). Resolver `scripts/pipeline/feature.sh`.
  - **auth** (`templates/features/auth/`): credentials `base` s volbou **`token_strategy: jwt | session`**.
    python-fastapi impl: common (models/passwords/repository/service) + per-strategy
    (security_*/router_* + sessions/V3). bcrypt(passlib)+pyjwt; no-enumeration; write-flow `?validate`.
    **Ověřeno pytestem: jwt 8/8 + session 8/8** (overlay nad base scaffoldem).
  - Watson init nabízí features (5. věc). `recommended-libs`: jwt-auth (pyjwt).
  - bonus z dogfoodu: base python `conftest` → glob `V*.sql` (feature s migrací bez úprav conftestu).
- **v0.36 — auth java-quarkus (strukturální):** `com.example.app.auth` (model/repository/service/
  security/resource, V2/V3), jwt (`@Authenticated`+smallrye-jwt) + session (cookie+jOOQ+SecureRandom).
  **NEbuildnuto** (viz Slabé místo).

## Jak navázat (příští session / „hej Watsone")

1. `STATE.md §Aktuální fokus` = živý přehled (wave `2026-06-10-scaffolds+engine-loop` + P7 bullet).
2. Konzistence: `bash scripts/format-check.sh` (formát/lint) + `bash scripts/catalog-conformance.sh`
   (reuse back-align) — obojí ve Vitek gate. `extraction-scan.sh` advisory.
3. Feature: `bash scripts/pipeline/feature.sh --list` → `--feature auth --variant base --stack X`.
4. Smyčka: `run.sh start <issue>` → `run.sh drive` (opakuj) → uzel → `run.sh done`.

## Decided (rozhodnutí — neopakovat)

- **Mechanická konzistence = scripty, ne LLM** (I4). Formattery/lintery dělají formát/bracing,
  ne ruční opravy. (Korekce uživatele — viz memory `scripts-not-llm-enforcement`.)
- **Enforcement = B (deterministické blocking)**, ne advisory ani fuzzy-similarity. Jen vysoce přesné
  signatury (false-positive ničí důvěru — lekce: python `str(exc)` docstring, java `Response.status` self).
- **Kód anglicky (identifikátory + komentáře), specs/docs česky**, user-text přes i18n.
- **Feature library: spec vždy, impl selektivně** (jen security-critical/univerzální/stabilní →
  audit-once). Varianty kompozovatelné (base + opt-in modul) + options (jwt/session). Auth = pilot.
- **Session i JWT** jako rovnocenná volba (`token_strategy`), ne jen JWT.
- ID=UUID default; if vždy s blokem; ternár jen prostý hodnotový výraz.

## Zbývá (next)

- **#12 — build-ověřit java auth** (gradle + jOOQ codegen + Docker; QuarkusTest mirror python;
  zkontrolovat `mp.jwt.verify.issuer` == login issuer, `UNPROCESSABLE_ENTITY`, jOOQ názvy) →
  Heimdall audit → `feature.yaml` java = ready. **Security-critical: nenasazovat neověřené.**
- **#6 — reálný graph-drive dogfood** (`run.sh drive` na reálném ticketu v dogfood projektu).
  Loop ověřen mechanicky (selftest 9/9 + drive walk + 2-agent dogfood), ne na reálné feature.
- **Feature library růst:** víc features (payments, file-upload, notifications…); auth `oauth`/`mfa`
  varianty (planned). Auth impl pro další stacky (solidjs klient).
- **Catalog-conformance signatury řídké** — rostou při extrakci; přidávat.

## Slabé místo (POVINNÉ)

- **Java auth NENÍ build-ověřená** — psaná bez gradle/jOOQ/Docker. Security-critical → MUSÍ projít
  `./gradlew build` + QuarkusTest před nasazením. Nejisté idiomy: jOOQ generated názvy (`AppUserRecord`,
  `APP_USER`/`APP_SESSION`), `Response.Status.UNPROCESSABLE_ENTITY` (existence v Jakarta REST 3.1),
  JWT issuer config coupling. Python impl (ověřená) = kontraktní reference → fix bude triviální.
- **Frontend scaffoldy (flutter/electron/solidjs) nejsou tsc/vitest/flutter-test ověřené** v tomhle
  prostředí (chybí node_modules/SDK). Jen strukturálně + format-clean (prettier/eslint/dart ano).
- **format-check není ve frameworkovém CI** — běží v projektu (Vitek gate, po `npm install`/`pip`).
  Frameworkové CI (`pipeline-guardrails`) jede jen `check.sh` + `selftest.sh`. Scaffoldy se v CI
  neformát-checkují (vyžadovalo by per-scaffold install).
- **Adopce `run.sh drive` je dokumentační** — nikdy neběžel na reálné feature (#6).
- **node_modules ve solidjs/electron** (z npm install eslint/prettier) jsou gitignored — OK, ale
  scaffoldy teď předpokládají `npm install` pro lint/format toolchain.
