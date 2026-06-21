---
wave: 2026-06-11-flow-finish-4
from: orchestrator (Watson session)
to: archive
type: wave-close
returns_to: null
timestamp: 2026-06-11T21:20:00+02:00
---

# Uzávěrka: flow-finish #4 — track dotažen přes audit-vrstvu, reálné nálezy sklizeny

Navazuje na `HANDOFF.md` (volba A — dorážení tracku). Track `2026-06-11-get-user`
protažen z `joey` přes **paralelní audit-frontier** (optimus ∥ sheldon ∥ heimdall ∥ vitek).
Účel #4 splněn: engine validován na reálných agentech (a-drift), drift zmapován (b-drift),
**+ 1 nový engine nález** (frontier re-flow). Live běh ponechán v čistém pauznutém bodě
(4 auditoři inflight) — NEcommitnut do kaskády (viz E1).

## Co session dotáhla (joey + 4 auditoři)

| uzel | agent/model | outcome | nález |
|---|---|---|---|
| `joey` | joey-qa / sonnet | **PASS** | 5/5 AC pokryto, integration 5/5, regression OK (pytest **18 passed**, nezávisle ověřeno). Soubor `server/tests/integration/test_get_user_acceptance.py`. |
| `optimus` | optimus-perf / sonnet | **PASS** | O(1) PK lookup (`app_user.id` TEXT PK), žádný N+1/bottleneck. Perf test = overkill pro XS read. |
| `sheldon` | sheldon-spec / sonnet | **FAIL→vision** | spec `specs/get-user.md` jmenuje `AuthRepository.find_by_id()` a `UserView` = impl detail ve spec (CO vs JAK); patří do decision.md, kde už správně je. |
| `heimdall` | heimdall-security / opus | **FAIL→ted** | **HIGH:** `GET /users/{id}` je neautentizovaný → únik emailu (PII) + user-enumeration přes UUID. Porušuje constitution F8 (auth-required by default; public opt-out jen s explicitním odůvodněním v spec+kontraktu). decision.md odložil jen *autorizaci*, *authN* nikdo nerozhodl. |
| `vitek` | vitek-quality / sonnet | **FAIL→bob** | `server/src/users/service.py` `get_user(self, user_id)` bez typové anotace; oprav na `user_id: UUID`. reuse-existing jinak dodržen čistě. |

**a-drift (engine na reálných agentech): NULA pro happy-path.** Frontier správně fanoutnul
4 auditory paralelně a **správně vynechal `edna`** (`has_ui=false` → design audit se neaplikuje).
joey done → completed=7 → drive vydal celou ready audit-množinu jako jeden DISPATCH-ALL. ✓

## b-drift nálezy obsahu (3) — feature `get-user` má reálné mezery

- **D1 (heimdall, HIGH) — chybějící authN gate.** Viz tabulka. = otevřené **produktové
  rozhodnutí** (níže), ne jen bug. Bobova impl je věrná kontraktu → return na ted, ne bob.
- **D2 (sheldon) — impl detail ve spec.** Vision spec jmenuje konkrétní třídu/metodu.
  Drobné, ale legitimní (čistota: spec = chování, ne mechanismus).
- **D3 (vitek) — chybějící typová anotace** parametru service. Triviální hygiena.

Pozn.: D1–D3 jsou nálezy v **obsahu uzlů** (práce agentů), ne v engine. Přesně to, co měl
profil-B re-run najít — gate-vrstva naostro **chytá reálné problémy**.

## E1 — ENGINE nález (a-drift kandidát do frontier-scheduleru), EMPIRICKY OVĚŘEN

**Problém: re-flow je severity-blind a nereconciluje vícero paralelních gate-FAILů smysluplně.**

Empirie (sandbox = kopie live current-run.md, `result.sh --run-file`, ledger do /tmp):
nakrmeny 4 reálné audit-envelopy v pořadí optimus(PASS), sheldon(FAIL→vision),
heimdall(FAIL→ted), vitek(FAIL→bob):

```
optimus  PASS         → completed=8
sheldon  FAIL→vision  → re-flow 24 uzlů, completed=[intake]      counters sheldon->vision=1
heimdall FAIL→ted     → re-flow 19 uzlů (už un-completnuto)      counters heimdall->ted=1
vitek    FAIL→bob     → re-flow 14 uzlů (už un-completnuto)      counters vitek->bob=1
→ drive: DISPATCH vision   (restart od úplného vršku)
```

**Pozorování:**
1. **Severity-blind.** Kosmetický spec-nit (D2, sheldon→vision) spustí **stejně velký**
   re-flow (24 uzlů, celá pipeline) jako kdyby šlo o kritickou chybu spec. HIGH security (D1)
   i type-nit (D3) jsou pohlceny — nejhlubší return (vision) subsumuje mělčí přes
   `forward_closure`. Union „deepest-wins" je sám o sobě konzistentní, ALE chybí signál
   severity/scope, který by rozlišil „behavior-changing rework" od „non-behavioral cleanup".
2. **Ztráta finding-payloadu.** `returns_to` vrátí *řízení* na cíl, ale **nenese obsah
   nálezu** (failure-signature) k re-dispatchnutému agentovi — jen bumpne counter. Re-běh
   visionu/teda/boba se spoléhá, že orchestrátor payload donese ručně. Engine ho nezachová.
3. **Žádné batchování paralelních findingů.** 3 nezávislé nálezy u 3 různých vlastníků se
   „vyřeší" restartem od visionu a re-během 24 uzlů — místo aby se posbíraly a aplikovaly
   minimálně (D3 u boba in-place, D1 u teda) v jednom průchodu. Drahé na reálných agentech.

**Dopad:** frontier-scheduler (čerstvě „HOTOVÁ") umí *vydat* paralelní audit-set, ale nemá
příběh pro **jeho návratovou stranu** — co se stane, když z paralelního setu přijde víc FAILů
různé závažnosti do různých hloubek. Default (severity-blind full re-flow od nejhlubšího) je
funkčně bezpečný (nic se neztratí, vše se přepočítá), ale prakticky drahý a tupý.

**Návrh směru (NE teď — další wave):** (a) gate-output nese `severity` (blocking|advisory);
advisory FAIL = finding zaznamenán, ale NEspouští re-flow (drive pokračuje, finding visí jako
open item na uzlu); (b) failure-signature se přenese do re-dispatch vstupu cíle (payload-carry);
(c) volitelně: batch-reconcile okno — počkej na celý paralelní set, pak jeden re-flow od
minimální nutné hloubky. Viz `frontier-scheduler.md` (návratová strana frontieru).

## Otevřené produktové rozhodnutí (NE engine) — auth na get-user

`GET /users/{id}` vrací email+role bez tokenu. Buď (a) `security: [bearerAuth]` + `Depends(
get_current_user)` u boba (infra hotová, ~1 řádek) + rozhodnutí v decision.md/openapi; NEBO
(b) vědomě public s odůvodněním v spec+kontraktu. **Mlčení kontraktu ≠ povolení k public**
(F8). Autorizace („kdo smí číst koho") zůstává samostatně deferred. Toto rozhodne člověk až
se k feature vrátí; #4 ho jen odhalilo.

## Stav po uzávěrce

- Live `2026-06-11-get-user`: completed=7 (..joey), frontier=4 auditoři inflight = **pauznuto
  na audit-vrstvě**. NEposunuto do re-flow kaskády (rozhodnutí: zaznamenat, ne dráždit živý
  stav nedokončeným fix-loopem). Resumovatelné: dořeš D1 (auth) + D2/D3, pak rozhodni o E1
  re-flow strategii a teprve pak krmit FAILy do `done`.
- Reálné artefakty přibyly: `server/tests/integration/test_get_user_acceptance.py` (+ `__init__.py`).
- B1 fix (result.sh path-existence) zaveden samostatně dříve v session (selftest 28/28).
