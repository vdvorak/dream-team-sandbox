---
wave: 2026-05-30-drift-align-rollout
from: orchestrator-session (dream-team)
to: příští session
type: handoff
timestamp: 2026-05-30
---

# Handoff — scaffold-uniformita wave + drift-align rollout napříč 6 projekty

Podrobné předání. Čti celé, pak pokračuj dle §Co zbývá.

## ⭐ FINÁLNÍ STAV (update — sessions doběhly)

Drift-align rollout je **z ~95 % hotový**. Tabulka §3 níže je z dřívějška —
toto ji nahrazuje:

- **Parker2, UnagyDev, Vdoklad, Trabajario, pneukarnik = HOTOVO** (sync + B1 +
  B2 + Část A; Vdoklad navíc už vyčistil i backend.md+frontend.md). pneukarnik
  uklidil i ten velký strom (§5 vyřešeno, zbývá 1 minor dirty soubor).
- **murio = zbývá JEDINÁ věc: `rules/backend.md` + `rules/frontend.md`** — pořád
  Parker copy-paste (logging/error-responses už opravené). Je to **flagnuté v
  murio `improvements/`** (commit „log drift-align follow-up nálezy").

**→ Jediný zbývající úkol:** čistá session v `~/dev/AI/murio` → odparkerovat
`backend.md`+`frontend.md`. murio JE **postgres** → PostgreSQL ENUM sekce
**ZŮSTÁVÁ**; opravit jen integrace (OpenAI/Gmail/web-scraping/manuscript →
BankID/ISDS/payment/AI, pohřební doména) + Fly.io (ověř použití). Ted → Vitek/
Heimdall/Sheldon gate → commit. Tím je celý rollout uzavřen.

## 1. Co se v této session udělalo

**A) Framework `dream-team` → v0.10.0 (HOTOVO, commitnuto na main):**
- Fáze 0–4 wave „scaffold-uniformita": kanonické stack reference + reálné
  spustitelné scaffoldy (java-quarkus, python-fastapi, solidjs — všechny
  ověřené build/test), activation profily (solo/standard/full), value-streams
  design, constitution dodatky (primitives/inference/type-refs, ochrana dev-dat),
  SSR→SSG (runtime SSR zakázán), `rules/defaults.md`.
- Detail viz `STATE.md` + git log (commity v0.6.0 → v0.10.0).

**B) Drift-align rollout do 6 projektů v `~/dev/AI/`** (viz §3 stav).
Každý projekt dostal `DRIFT-ALIGN.md` (Část A = teď, Část B = po syncu).

## 2. Klíčový princip (PLATÍ I DÁL)

- **Orchestrátor (já / příští session) NESAHÁ ručně do projektových rules/** —
  opravu dělá **flow uvnitř session projektu** (Ted → Vitek/Heimdall/Sheldon
  gate → commit). Nad projektem s **aktivní session se needituje zvenčí**.
- Drift-align passy jsou **sekvenční + file-state-driven** → skládají se na sebe,
  nerozbíjejí se. Rozbíjí jen **concurrency** (2 passy nad stejným souborem).
- Follow-up se píše do **`STATE.md §Open Items`** (durable), NE do `DRIFT-ALIGN.md`
  (ten se po dokončení maže).

## 3. Stav per projekt (přečteno z disku 2026-05-30)

| Projekt | Sync 0.10 | Část A | B1 | B2 | Strom | Verdikt |
|---|---|---|---|---|---|---|
| **Parker2** | ✅ | n/a origin | ✅ | ✅ full | čistý | **HOTOVO** (Parker obsah v rules = správně) |
| **UnagyDev** | ✅ | n/a | ✅ | ✅ full | čistý | **HOTOVO** |
| **Trabajario** | ✅ | ✅ | n/a | ⏳ | čistý | zbývá jen **B2 profil** + `rm DRIFT-ALIGN.md` |
| **Vdoklad** | ✅ | ✅(log/err) | ⏳ | ⏳ | čistý | čeká **B1** + viz §4 backend/frontend |
| **murio** | ❌ 0.5.1 | ✅(log/err) | ⏳ | ⏳ | čistý | **nesyncnuto** → sync → B1 → B2 + §4 |
| **pneukarnik** | ✅ | ✅ | ✅ | ✅ std | ⚠️ OBŘÍ | drift-align hotový; viz §5 |

## 4. 🔴 Scope gap, který se řešil (DŮLEŽITÉ — nedořešeno)

Původní DRIFT-ALIGN scope řešil jen `logging.md` + `error-responses.md`. Z disku
ale potvrzeno, že **`rules/backend.md` A `rules/frontend.md` jsou taky Parker2
copy-paste** — v **murio i Vdoklad** (Parker2 = origin, jeho jsou správné).

**Rozhodnutí (Volba 1)** pro B1 kolizi: B1 commit drž fokusovaný (smazat
programming.md, DB-enum pravidlo adaptovat), zbytek backend.md flagnout. Plný
drift-align backend.md+frontend.md = **samostatný Part-A pass**.

**Co udělat (per projekt, ve flow té session):**
- **Vdoklad** (SQLite): `backend.md` PostgreSQL ENUM (`SAEnum create_type=False`,
  `ALTER TYPE`) → **SQLite CHECK constraint**; integrace OpenAI/Gmail/web-scraping
  → reálné integrace; „manuscript/rukopis" → fakturační doména; Fly.io
  horizontal-scaling → desktop (žádný Fly). `frontend.md` taky odparkerovat.
- **murio** (Postgres): ENUM sekce **zůstává** (murio JE postgres); fix integrace
  (OpenAI/Gmail/web-scraping/manuscript → murio realita: BankID/ISDS/payment/AI,
  pohřební doména) + Fly.io ověřit. `frontend.md` odparkerovat.

→ Doplnil jsem `backend.md`+`frontend.md` do **Část A** v `murio` + `Vdoklad`
DRIFT-ALIGN.md (sessions stály → bezpečné). Flow to při resume udělá.

## 5. ⚠️ pneukarnik — necommitnutý strom (mimo drift-align)

Drift-align (sync+B1+B2) commitnutý a hotový. ALE pracovní strom je plný
necommitnutých změn: ~20 specs, ~15 web komponent/testů, 3 wordpress PHP, nové
`i18n/`, `booking/`, `ssg-prerender.md`, 4 handoffs složky (datum 05-28 → spíš
**starší nahromaděná práce**, ne z dnešní session). **Vyžaduje review:** co to je,
commitnout / zahodit. Drift-align na tom nezávisí.

## 6. Co zbývá — pořadí (vše ve flow té session, ne orchestrátor ručně)

1. **Trabajario** — otevři → „dokonči B2 profil (standard)" → `rm DRIFT-ALIGN.md`.
2. **Vdoklad** — otevři → „pokrač B1 (Volba 1), pak backend.md+frontend.md Část A
   dle DRIFT-ALIGN.md", → B2 → `rm`. (plan mode na B1 + backend.md = citlivé.)
3. **murio** — otevři → `agentic-sync.sh` (0.5.1→0.10.0) → restart → B1 → B2 +
   backend.md+frontend.md Část A → `rm`.
4. **pneukarnik** — vyřeš §5 strom (samostatně).
5. **Parker2, UnagyDev** — hotové, nesahat.

## 7. Mimochodem — caveman incident (vyřešeno)

murio session hlásila „malicious exfil + blanking output". **False positive** —
byl to plugin `caveman` (token-komprese, navíc ani nebyl enabled). Komprese
blankovala output + murio agent četl Parker exfil/secrets balast v logging.md a
spojil si to. **Odinstalován kompletně.** Žádná kompromitace.

## 8. Jak navázat

Framework je file-driven → **nepotřebuješ obnovovat tuhle konverzaci**. Příští
session (v dream-team) čte `STATE.md` + tento handoff. Per projekt: čistá session
v daném repu → „Proveď drift-align dle DRIFT-ALIGN.md" (resp. dle bodu §6).
