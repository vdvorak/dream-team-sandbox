---
feature-id: runtime-contract
flags: has_ui: false · touches_db: false · has_server: true
acceptance: acceptance/runtime-contract.md
---
# Runtime jako standalone produkt — kontrakt schopností

## Cíl

Runtime vystavuje stabilní, substrátem-agnostický kontrakt, přes který
odběratel (aplikace nebo generický klient) řídí životní cyklus prostředí
a přistupuje k jeho schopnostem — bez přímého vhledu do vnitřku runtimu.
Kontrakt je fyzicky vlastněn tímto repem; odběratel ho vendoruje read-only.

## Aktér a cíl

**Primární:** Aplikace (řídící vrstva) chce zajistit, uspat, zrušit prostředí
pro projekt a číst jeho stav, soubory a terminál — bez znalosti substrátu.

**Sekundární:** Generický klient (curl / CLI) chce totéž bez aplikace.
Runtime musí být použitelný standalone.

## Hlavní scénář

Odběratel zavolá **zajisti prostředí** s odkazem na repozitář projektu →
runtime vrátí `ready` (nebo `provisioning` s pokyn k opakování) — prostředí
je garantovaně aktivní a ZEĎ je aktivní (bez aktivní ZDI se stav `ready`
nikdy neobjeví) → odběratel zavolá **stav prostředí** a dostane
připojovací adresu (opaque handle; odběratel neví, co je za ním) →
odběratel zavolá **čti soubory** nebo **stav repozitáře** pro přístup
k workspace projektovým datům → odběratel otevře **terminál** (obousměrný
PTY stream) a interaguje se zaklecovaným procesem → odběratel zavolá
**uspi** (advisory, bez záruky okamžitosti) nebo **zruš** prostředí →
zdravotní dotaz (`healthz`) vrátí verzi kontraktu a stav služby.

Při jakékoli operaci, kdy prostředí neexistuje nebo ZEĎ není aktivní, runtime
vrátí jasnou chybu — nikdy neteče stav `ready` bez garantovaného enforcement.

## Schopnosti (kontrakt)

| Schopnost | Popis |
|---|---|
| **Zajisti prostředí** | Idempotentně vytvoří nebo obnoví prostředí pro projekt; naklonuje repozitář. Výsledek: `ready` nebo `provisioning`. |
| **Stav prostředí** | Vrátí aktuální stav a opaque připojovací adresu (nebo `null` pokud není ready). |
| **Uspi prostředí** | Advisory požadavek na uvolnění zdrojů; idempotentní. |
| **Zruš prostředí** | Nevratné odstranění prostředí; idempotentní. |
| **Stav repozitáře** | Vrátí branch, stav pracovního stromu a poslední commit workspace prostředí. |
| **Čti soubory** | Výpis souborů v workspace s volitelným filtrováním; přístup mimo sandbox vrátí chybu. |
| **Připoj terminál** | Otevře obousměrný PTY stream; podporuje reconnect (re-attach); uzavření streamu prostředí neruší. |

## Principy kontraktu

- **Opacita:** odběratel vidí jen kontrakt; vnitřní mechanismy (substát, image,
  agent, enforcement) se přes kontrakt neodhalují.
- **Agnostika substrátu:** připojovací adresa je opaque; odběratel z ní nezjistí,
  na jakém substrátu prostředí běží.
- **Runtime nezná odběratele:** vystavuje jen kontrakt, funguje bez aplikace.
- **ZEĎ je vlastnost prostředí, ne parametr:** kontrakt nemá žádnou operaci
  ani pole, které by zmírňovalo egress, ingress nebo shell enforcement.
- **Fail-closed:** `ready` stav se neobjeví bez aktivní ZDI; pokud enforcement
  nelze ověřit, vrátí se chyba nebo stav `provisioning`.
- **BYOK token neteče přes control API:** token AI nástroje vstupuje interaktivně
  přes PTY session, runtime je vodič, ne trezor.
- **Idempotentnost:** zajisti a zruš jsou idempotentní; race pro jeden projekt
  končí jedním prostředím.
- **Verzování:** kontrakt je verzován; zdravotní dotaz vrátí verzi; non-breaking
  rozšíření (optional pole / operace / chybový kód) nevyžadují koordinaci;
  breaking změna = major verze + koordinovaný L3 v obou repech.

## Scope

**In:**
- Kontrolní rovina (HTTP+JSON): 7 operací výše + healthz.
- Datová rovina: obousměrný PTY stream s podporou změny velikosti a reconnect.
- Stavový automat prostředí: `none → provisioning → ready → asleep → destroyed`.
- Autentizace odběratele vůči runtimeu (aplikace se autentizuje vlastní identitou;
  BYOK token nikdy přes tuto rovinu).
- App-facing chybový registr (oddělen od interního cage registru).
- Versioning a drift-check fixture (OpenAPI artefakt vendorovaný do appky).

**Out:**
- Implementace (image, agent, lifecycle service, enforcement) — viz future L3.
- UI, dispatch logika, gates, project model — patří do aplikace.
- Interní cage chybové kódy, ruleset, de-root sekvence — nikdy v kontraktní ploše.
- BYOK token management — interaktivní PTY, nikdy control API.

## Edge cases & otevřené otázky

- **Reconnect terminálové session:** při výpadku transportu odběratel re-attach
  ke stávající session (workspace proces neexituje) — konkrétní close kódy a
  behavior viz kontrakt (Ted).
- **Souběžné `ensure` pro stejný projekt:** runtime serializuje; výsledek = jedno
  prostředí (Ted definuje idempotency klíč nebo per-project mutex).
- **Sleep semantika:** sleep je advisory; runtime může ignorovat (např. probíhá
  aktivní PTY session) — odběratel nesmí spoléhat na okamžitou změnu stavu.
- **Soubory mimo workspace:** `listFiles` s cestou mimo sandbox → chyba (path
  escape guard); detailní guard logika viz kontrakt.
