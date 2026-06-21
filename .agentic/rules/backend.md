---
cache_key: rules-backend-v1.1
type: normative-rules
last_updated: 2026-06-10
---

# Backend Patterns

Tvar serverové vrstvy, tech-agnostic. Platí pro **všechny backend targety**.
Konkrétní framework/ORM → `stack/<target>.md`.
Projektové odchylky a doménové patterny → `rules/` v kořeni projektu.

Universal hygiena (typy, secrets, swallowed exceptions, …) → `constitution.md §Standardy kódu`.
Validace a error shape → `constitution.md §Strict server validation` + `§F5`.
Cancellability + idempotence → `constitution.md §Cancellability povinná` + `§Idempotence`.

## Hranice souboru

**Sem patří:** tech-agnostic architektonické patterny, vrstvení, transakční hranice,
multi-replica safety, specifické bezpečnostní vzory (credential token, šifrování).

**Sem nepatří:** specifický framework/ORM, konkrétní názvy tříd/modulů,
feature-specific business pravidla, obecná hygiena (ta je v constitution).

## Vrstvení a odpovědnosti

### Router / Controller (HTTP vrstva)
- Přijímá a validuje HTTP request, deleguje na service, vrací response
- Žádná business logika, žádné přímé DB dotazy

### Service (business vrstva)
- Implementuje business pravidla ze spec, orchestruje repository + integrace
- Spravuje transakce
- Žádný SQL ani HTTP detail frameworku

### Repository (data vrstva)
- Jediný přístup k DB; vrací domain objekty nebo None / null
- Žádná business logika
- **Jedna tabulka = jeden repozitář**, sdílený napříč rolemi/service; admin/jiné dotazy
  se přidají sem (např. `findAllForAdmin`), nevzniká paralelní repo per role
- (Projekt bez DB → tato vrstva N/A.)

### Integration (externí volání)
- Každá externí závislost izolovaná do vlastního modulu
- Žádný přímý přístup k DB
- Každé volání má timeout a fallback — selhání integrace nesmí shodit lokální operaci

## API model role (read/write boundary)

Kontrakt rozlišuje tři role modelů — backend i frontend se jimi řídí, nevymýšlí vlastní boundary:
- **`*View`** — readonly model pro čtení zdroje
- **`*Data`** — write payload pro create/update/validate (jediný write model)
- **`*ExtData`** — read model pro init/edit flow: obsahuje `data: *Data` + readonly kontext
  (reference data, permissions, warnings); **není druhý write model**

- Read operace sloužící jako vstup write formuláře vrací `*ExtData`; editable subtree je vždy
  v poli `data`. Sourozenecká pole k `data` jsou readonly kontext — **nikdy** součást write payloadu.
- Standardní editovatelný zdroj nezavádí paralelní „form-only" endpoint s jinou business pravdou.

## File vs DB — hranice úložiště

Architektonická hranice z north-star D8 (komerční škála + API-first). Porušení je breaking
change a vyžaduje L3 schválení.

**Soubor (repozitář):** výhradně engine artefakty — definice grafu (`delivery.yaml`),
stav běhu (`current-run.md`), interakce (`interactions.yaml`). Plus výchozí seed soubory
frameworku v repu appky (šablony, počáteční fixture).

**DB:** všechna aplikační a produktová data — backlog/issues, todos, uživatelská data,
vše co je „obsah produktu" nebo se mění za provozu.

**Rozhodovací test:** Pokud je to obsah produktu, mění to uživatel za běhu nebo by to mělo
mít API — patří do DB. Pokud je to definice toho, jak engine/projekt funguje, a sedí to
v repozitáři jako kód — patří do souboru.

## Identifikátory

- Resource ID je **UUID** (default) — stabilní, ne-enumerovatelné, bezpečné v distribuci.
  `int`/serial jen s explicitním důvodem (interní sekvence, perf), zdůvodnit ve spec.
- Na hranici (path param, request/response model) je ID **typované** (UUID), ne raw string —
  konzistentní parsing/validace. Konkrétní typ binding → `stack/<target>.md`.

## Typy operací

create | update | delete | read-detail | read-collection | action/command.
Create a update jsou **separátní** operace (různá pravidla / životní cyklus); **žádný upsert**,
který by skryl rozdíl. Sdílená validace se extrahuje do společného pravidla, ne spojením operací.

## Write-flow: validation-only + commit

Každý write endpoint nabízí **validation-only režim** (dry-run):
- validation-only vrací jen validační výsledek (field/global errors) a **NESMÍ mít side-effecty**
- commit (reálný zápis) **vždy validuje server-side znovu** — nikdy nevěř, že klient dry-run
  zavolal. Validace je intrinsická každému zápisu; režim jen gate-uje, zda se po ní commitne.
- klient volá validation-only pro živé UX hinty (`rules/frontend.md §Write-flow`); autorita je
  vždy server (`constitution §Strict server validation`)
- konkrétní binding (query flag, response typ) → `stack/<target>.md`. Primárně CRUD; čisté
  action/command endpointy režim mít nemusí.

## Kolekce

Při prvním seznamovém endpointu spec rozhodne: paginace? filtr? řazení? výchozí řazení?
(Když spec neurčí, AI nevolí sama.) Kontraktní role kolekcí:
- **`ApiListOf<T>`** — prostá kolekce bez stránkovacích metadat
- **`ApiPageOf<T>`** — offset/page model (potřeba celkového počtu nebo skoku na stránku)
- **`ApiSliceOf<T, TCursor>`** — výchozí pro infinite scroll; `TCursor` je explicitní typ se
  stabilním řazením + tie-breaker (typ. `id`); klient řídí `loadMore` z `hasMore`/`nextCursor`,
  nesyntetizuje request z počtu už načtených položek

## Transakce

- Každá write operace s více záznamy musí být atomická
- Chyba uprostřed operace = rollback celé transakce
- Dávková operace / background job má vlastní transakční hranici pro každou
  zpracovanou položku — chyba u jedné neshodí již zapsané

## Background joby

Idempotence a cancellability viz `constitution.md §Idempotence` a `§Cancellability povinná`.

- Job musí kontrolovat stop flag pravidelně (ne jen na začátku)
- Progress se aktualizuje alespoň po každé zpracované položce
- Chyba u jedné položky nepřeruší celý job — zaznamená se, zpracování pokračuje
- V jednu chvíli může běžet nejvýše jeden job stejného typu

### Multi-replica safety

- Throttle, rate-limit a stop-signal stav ukládán v DB, ne v paměti procesu.
  In-memory varianta akceptovatelná pouze jako test fixture nebo na explicitně
  single-process deploymentu (dokumentovat v spec).
- Cancel signalizován persistentním stop flagem (DB sloupec) — worker polluje.
  In-memory cancellation napříč replikami nefunguje.
- Globální capacity limity enforce-ují přes DB count nebo advisory lock.

## Credential-grade single-use token

Vzor pro out-of-band verifikační flow (password reset, data export, erasure).

- Plain token generován kryptograficky bezpečným zdrojem (≥ 32 byte URL-safe)
- V DB se ukládá **pouze hash** — plain token nikdy persistovaný
- TTL ≤ 30 minut; po expiraci nepoužitelný
- Single-use: konzumace atomicky v jedné transakci s business effectem
- Token cestuje k uživateli out-of-band (e-mail) — nikdy přes URL v UI ani v logu
- Confirm endpoint: `Cache-Control: no-store`; token nesmí být v response body
- Self-service request endpoint vrací vždy 202 — enumeration mitigation
- Throttle: per-user i per-IP sliding window

Pokud feature potřebuje delší životnost (např. pozvánka), nepatří pod tento vzor.

## Šifrování citlivých hodnot

- Citlivé konfigurační hodnoty (API klíče, OAuth tokeny) šifrované před uložením
- Dešifrování za běhu při čtení — klient nikdy nedostane ciphertext
- Konkrétní implementace viz `stack/<target>.md`

## Strukturované vstupy operací

- Netriviální vstup → explicitní request/command/filter objekt, ne dlouhý seznam parametrů
- List/filter operace → společný model

## Generovatelnost

- Backend pattern musí být definovaný tak, aby šel znovu vytvořit po smazání kódu
- Reusable rozhodnutí musí být opřená o normativní pravidlo (zde nebo v `stack/`)
- Existující kód je důkaz současného stavu, ne autorita pro budoucí regenerace
