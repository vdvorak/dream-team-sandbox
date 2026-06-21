---
cache_key: init-determinism-v1.0
type: design
last_updated: 2026-06-11
status: DESIGN — diagnóza z 2-agent dogfoodu (2026-06-11); fix NEnaimplementován
---

# Init determinismus — proč stejný vstup nedává stejný výstup (a kudy ven)

> ⚠️ **Diagnóza + plán, ne hotová mechanika.** Vzniklo z 2-agent dogfoodu
> (java-quarkus, feature `auth`, identická jednovětá zadání). Cíl: stejný vstup →
> stejné strukturální výstupy. Doplňuje [`pipeline-architecture.md`](pipeline-architecture.md)
> (ten řeší determinismus **routingu/grafu**; tenhle dokument řeší determinismus
> **compose/apply** fáze, kterou graf engine ani nepokrývá).

## TL;DR — root cause v jedné větě

**Scripty ve frameworku RESOLVNOU (co/kam), ale neAPLIKUJÍ (copy/rename/overlay).**
`scaffold.sh` i `feature.sh` jen vrací cesty. Veškerou fyzickou akci — nakopírovat
kostru, přejmenovat package, overlaynout feature, očíslovat migrace — dělá **LLM**.
Determinismus padá přesně tam, kde je úsudek, a ten úsudek **není zaskriptovaný**.
Framework má **resolver** vrstvu, ale **apply** vrstva chybí.

## Co dogfood ukázal

Dvě reálné `claude` sessions, každá v čistém projektu (`SKELETON_NEEDS_WATSON`),
na vstupu **jediná lidská věta**: *„Hej Watsone, založ mi nový projekt — jednoduchý
task tracker v Javě (Quarkus) s přihlašováním uživatelů."* Žádné „jak na to" v promptu.

| | `ja` | `jb` |
|---|---|---|
| Watson init (founding) | ✅ | ✅ |
| auth rozpoznána jako feature | ✅ | ✅ (seed v backlogu) |
| **předpřipravená impl aplikována** | **✅ JWT overlay + `V2__auth.sql`** | **❌ jen backlog, impl odložena** |
| package | `cz.ja.tasktracker` | `com.example.jb` |
| platformy | + `clients/web/` (sám přidal) | backend-only |
| build-verify | ❌ (gradle chybí, oba poctivě) | ❌ |

Scaffold kostra vyšla u obou **identicky** — ne protože je skriptovaná, ale protože
„zkopíruj celý strom" je akce **bez úsudku**. Feature overlay divergoval, protože je
**plný úsudku** (vyber soubory dle varianty, přepiš package, rozhodni timing).

## Vrstvy (jak to běží dnes)

```
  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────┐   ┌─────────┐
  │  ELICIT (A) │ → │  RESOLVE     │ → │  APPLY (B)   │ → │  SEED   │ → │ HANDOFF │
  │  vstupy     │   │  co/kam      │   │  udělej to   │   │ docs    │   │ →Vision │
  └─────────────┘   └──────────────┘   └──────────────┘   └─────────┘   └─────────┘
   člověk / LLM       SCRIPT ✅          LLM 🔴 ← DÍRA       LLM (text)
   (4 věci+features)  scaffold.sh        copy/rename/
                      feature.sh         overlay/migrace
                      (resolve-only)     ── není script ──
```

RESOLVE je zaskriptovaný. **APPLY chybí jako vrstva.** To je celý root cause.

## Rozhodovací body (oštítkované)

### A — ELICIT (vstupy)
V produktu je odpoví **člověk** (autorita). Autonomně (dogfood) je hádá LLM → nutné defaulty.

| # | rozhoduje | typ | autonomně dnes | cíl |
|---|---|---|---|---|
| A1 | název | control | LLM | vstup → odvozuje base_package |
| A2 | platformy (web?) | control | **LLM hádá** 🔴 | default: nezadáno + „v Javě" → backend-only |
| A3 | stack (be/fe/db/deploy) | control | LLM (z věty) | default per signál |
| A5 | které features | control | LLM (auth ✓) | rozpoznání z popisu + default |
| A9 | profil agentů | control | LLM | deterministicky z complexity signálů |

### B — APPLY (compose)
Doc je popisuje jako *deterministické*, ale dělá je LLM, protože **žádný script je nedělá**
→ **to jsou ty pravé bugy** (tečou i s člověkem v kličce!).

| # | akce | typ | dnes | cíl |
|---|---|---|---|---|
| B1 | copy scaffold kostry | control | **LLM** (spolehlivý) | APPLY engine |
| B2 | rename package `com.example.app→…` | control | **LLM** 🔴 `cz.ja` vs `com.example.jb` | APPLY engine + naming pravidlo |
| B3 | feature overlay (copy impl) | control | **LLM** 🔴 ja ano / jb ne | APPLY engine |
| B4 | migrace na další volné číslo | control | **LLM** 🔴 (latentní) | APPLY engine |
| B6 | rules seed dle tabulky | control | LLM (mech. copy) | APPLY engine (nebo OK) |
| B7 | constitution overlays vlít | content | LLM | zůstává LLM (text) |
| B10 | spec/backlog seed | content | LLM | zůstává LLM (text) |

## Dvě třídy leaků — nepleť je

- **Třída B (apply není script)** = `B1–B4`. **Skutečný bug.** Diverguje **i s člověkem
  v kličce**, protože compose dělá ručně model. Tohle se MUSÍ zaskriptovat.
- **Třída A (chybí default)** = `A2,A3,A9`. Kouše **jen autonomně**. V human-in-loop
  „funguje dle návrhu". Pro autonomní dogfood potřebuje default na každý vstup.

## Rozhodnutí (2026-06-11)

1. **Třída A zůstává human-in-loop v produktu** — stack, platformy, features volí
   člověk přes interview. Determinismus tady neřešíme flow změnou.
2. **Defaulty na třídu A jen jako dogfood fixtura** — aby dva autonomní běhy dostaly
   identické vstupy a izolovala se tím čistě **třída B**. Není to produktová změna flow.
3. **Třída B = produktový fix = APPLY engine.** To je jádro práce.

## Fix architektura

```
  ELICIT ──→ [ resolved-inputs.md ]  ← STROJOVÝ kontrakt (machine-readable)
   (+ defaults)   name, base_package, platforms[], stack{},
                  features[{id,variant,options}], profile, deploy, langs
                              │
                              ▼
                    ┌──────────────────┐
   scaffold.sh ───→ │   compose.sh     │   = APPLY engine (NOVÉ, deterministické)
   feature.sh  ───→ │  (jediné místo)  │   1. copy scaffold per manifest
   (resolvery)      │                  │   2. rewrite base_package (B2)
                    │                  │   3. per feature: select-by-option +
                    │                  │      copy impl + place migrace (B3,B4)
                    │                  │   4. rules seed (B6)
                    └──────────────────┘
                              │
                              ▼
                  server/ contracts/ clients/ rules/  ── byte-deterministicky
```

**Tři pilíře:**
1. **APPLY engine** (`compose.sh` nebo `scaffold.sh --apply`) — jediné deterministické
   místo, co položí scaffold + feature overlays se stejným přepisem package. Resolvery
   zůstanou (co/kam), engine aplikuje (udělej).
2. **Strojový kontrakt A→B** — `resolved-inputs` (rozšířený `project-config.md`). Dnes
   je A→B předáno **prózou** („Watson ví") → proto B teče. Když compose čte strukturovaný
   record, nemá co improvizovat.
3. **Naming pravidlo = čep** — `B2` i `B3` potřebují `base_package`. Definuj
   `base_package = f(název)` deterministicky, zapiš do configu, oba kroky čtou totéž →
   konzistence.

**Co `feature.yaml` potřebuje navíc** (aby apply uměl vybrat soubory dle volby — dnes
je to jen próza v impl README):
```yaml
impl:
  java-quarkus:
    path: …/impl/java-quarkus/
    package_root: com.example.app        # odkud přepsat
    files:
      common:  [auth/model/*, auth/repository/AuthRepository.java, auth/service/*, auth/security/*, V2__auth.sql]
      jwt:     [auth/resource/AuthResourceJwt.java]
      session: [auth/resource/AuthResourceSession.java, auth/repository/SessionRepository.java, V3__sessions.sql]
    wiring: none                         # java self-registruje; python: vlož router do main
```

## Bezpečnostní pojistka (proč to není volitelný úklid)

`feature.yaml` slibuje *audit-once: „projekt kopíruje, neregeneruje."* Dokud overlay
dělá LLM, security kód se může nenápadně přepsat → **Heimdallův audit přestane platit
na to, co reálně leží v projektu.** APPLY engine (byte-věrná kopie + jen deterministický
rename) je **podmínkou** toho, aby audit-once vůbec dával smysl.

## Vedlejší nálezy z dogfoodu (drobné)

- `setup-claude-code.sh` přes git-archive snapshot **ztrácí +x** na scriptech → `ja` musel
  `chmod +x .agentic/.../scaffold.sh`, aby ho spustil (sáhl tím do read-only frameworku).
  Fix: setup chmodne scripty, ať flow nemusí.
- Build-verify java auth (#12) v tomhle prostředí **neproběhl** (chybí gradle/gradlew) —
  oba běhy to poctivě přiznaly, nic nefingovaly.

## Next

- [x] **APPLY engine v1** — `scripts/pipeline/apply-feature.sh` (copy + package rewrite + migrace
      numbering, option-aware). Dokázáno: stejné vstupy → byte-identický výstup (jwt i session),
      jwt≠session. **Tím empiricky potvrzeno, že `ja`/`jb` divergence byla (a) chybějící mechanika,
      ne (b) blbý agent.**
- [x] **`feature.yaml` apply-manifest** (per-option `files`/`migrations` + `package_root` + `wiring`)
      pro `auth` java-quarkus.
- [x] **scaffold package-rename (B2-scaffold)** — `compose.sh` přejmenuje `com.example.app` napříč
      scaffoldem (cesta + obsah + `rootProject.name`). Dokázáno end-to-end: `diff -r` byte-identický,
      **0 zbytků `com.example`**, vše (auth+shared+example) konzistentně pod projektovým package.
- [x] **zadrátováno do foundingu** — `compose.sh` = founding APPLY krok (copy scaffold + rename +
      apply features), zapsáno do `watson-interviewer.md` (v1.9). `scaffold.sh`/`feature.sh` = resolve,
      `compose.sh`/`apply-feature.sh` = apply.
- [x] **naming pravidlo `base_package = f(název)`** — v `compose.sh` (autonomně `com.<slug>`;
      v produktu přebije UI přes `--package`).
- [x] **`apply-manifest` i pro `python-fastapi`** — generic stack (bez package-rename; `apply-feature.sh`
      umí `package_root: null`). Copy+migrace deterministické. `wiring: router-into-main` zatím jen warning.
- [x] **dogfood re-run s enginem (capstone)** — viz níže.
- [ ] **wiring auto-insert** — marker-based vložení `include_router` do python `main.py` (zatím manuální).
- [x] **issuer do compose** — compose teď nastaví `mp.jwt.verify.issuer` + `smallrye.jwt.new-token.issuer`
      z `--name` (deterministicky, ne ad-hoc agentem). Re-run residual #1 zacelen u zdroje.
- [ ] **zúžit agentovi ad-hoc edity** — re-run: `jb` přidal navíc `server/.gitignore`. Po compose by
      agent neměl strukturu ladit ručně (čisté (b)).
- [ ] wave-pipeline (druhá půlka „celého systému") — táž (a)/(b) čočka na per-issue flow

## Výsledek capstone re-runu (2026-06-11, po zadrátování compose)

Dvě headless sessions, **stejná věta** (název+java+jwt pinnuté = class-A fixované), wired compose:

- **oba** přejmenovaly celý scaffold na `com.tasktracker` (0 zbytků `com.example`), **oba** nasadily
  auth (jwt, 8 souborů) — `server/` + `contracts/` **byte-identické až na 2 drobnosti**.
- Zbylé 2 divergence = **čisté (b)** (agent po compose edituje navíc): JWT issuer v
  `application.properties` (`app` vs `tasktracker`) a stray `server/.gitignore` u jb.

**Tím (a)/(b) metoda potvrzena v praxi:** velká divergence z prvního dogfoodu (auth ano/ne, package
naming) byla **(a)** → compose ji zacelil na byte-identický kód. Co zbylo, je drobné **(b)**, teď
zviditelněné a adresně řešitelné (issuer → do compose; ad-hoc edity → zúžit agentovi).

Princip dohromady drží [scripts-not-LLM enforcement] (constitution I4): mechanická
konzistence patří deterministickým nástrojům, ne LLM úsudku. RESOLVE to splnil; APPLY ne.
