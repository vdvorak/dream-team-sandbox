---
feature-id: runtime-control-plane
flags: has_ui: false · touches_db: false · has_server: true
acceptance: acceptance/runtime-control-plane.md
note: slice 1 — lifecycle core; git/files/terminal deferred na navazující wave
---
# Control-plane server — lifecycle core (slice 1)

## Cíl

Postavit reálný HTTP control-plane server, který implementuje slice 1 kontraktu
(`contracts/runtime-contract.md` v1.0.0): životní cyklus prostředí (`ensure` / `get` /
`sleep` / `destroy`) + `healthz`. Server musí být spustitelný standalone na Linuxu
(dev provider) a zároveň garantovat fail-closed při napojení na reálný enforcement provider.

## Aktér a cíl

**Primární:** Aplikace (nebo generický curl klient) chce idempotentně zajistit, sledovat,
uspat a zrušit prostředí pro projekt — bez znalosti substrátu — a dostat zpět stav s
opaque connection handleem.

**Sekundární:** Operátor chce server spustit lokálně bez závislosti na cloudu a ověřit
lifecycle + fail-closed chování bez živého enforcement backendu.

## Hlavní scénář

Klient se autentizuje (mTLS nebo service token) → volá `POST ensure` s `project_id` +
`repo.url` + `tool` → server zkontroluje, zda prostředí existuje; pokud ne, spustí
provisioning přes enforcement provider → provider garantuje, že enforcement je aktivní;
teprve pak server přepne stav na `ready` → klient opakovaně volá `GET {project_id}` a
dostane stav (s `connection` handle pokud `ready`) → klient volá `POST sleep` (advisory)
nebo `DELETE {project_id}` → `GET /v1/healthz` vrátí verzi kontraktu a stav služby.

Pokud enforcement provider nemůže garantovat aktivní ZEĎ → server NESMÍ přepnout na `ready`;
vrátí `502 ERR_PROVISION_FAILED` nebo zůstane v `provisioning` (fail-closed).

## Scope

**In:**
- HTTP server na `GET /v1/healthz` + 4 lifecycle operace dle OpenAPI (`ensureEnvironment`,
  `getEnvironment`, `sleepEnvironment`, `destroyEnvironment`).
- Stavový automat `Environment`: `none → provisioning → ready → asleep`; `destroyed`
  z kteréhokoli stavu (viz kontrakt §2).
- In-memory state store per `project_id` (slice 1 — trvanlivost persistence deferred).
- Serializace per `project_id`: souběžné `ensure` pro tentýž projekt → jedno prostředí.
- Fail-closed garance: `ready` NIKDY bez úspěšné odpovědi enforcement providera.
- Pluggable enforcement-provider rozhraní: server volá provider přes interface; provider
  rozhoduje, zda enforcement je aktivní, a vrátí connection handle nebo chybu.
- **Fly provider** (tenký/stub): volá Fly control API nebo vrací stub connection; reálné
  Fly provisioning může být no-op v první iteraci.
- **Dev/local provider**: nevynucuje žádný skutečný enforcement, ale explicitně reportuje
  „enforcement active = true" — umožňuje standalone spuštění a testování lifecycle na Linuxu
  bez cloudu.
- Auth middleware: ověření mTLS klientského certifikátu nebo `Authorization: Bearer` tokenu;
  selhání → `401 ERR_UNAUTHORIZED`.
- App-facing error registr (reuse z kontraktu §8): server vrací pouze kódy z tohoto registru;
  interní provider chyby se nikdy neprůmítnou navenek.
- `phase` informativní string v `provisioning` stavu (tolerant reader — volný string, ne enum).
- `contract_version: "1.0.0"` ve všech `Environment` response i v `healthz`.

**Out (deferred na navazující wave):**
- `getGitStatus` (`GET …/git`) — AC-6.
- `listFiles` (`GET …/files`) — AC-7.
- `attachTerminal` (`GET …/terminal` WS) — AC-8.
- Reálné klonování repozitáře (git clone uvnitř kontejneru/workspace).
- Reálné spuštění AI agenta v kontejneru (MOTOR těžká část).
- Trvanlivá persistence stavu (DB / soubor).
- Drift-check CI fixture (vendoring do app-side — deferred do app-side wave).

## Enforcement-provider rozhraní (koncept)

Server definuje interface (název a tvar implementace jsou rozhodnutím CTO/architekta):

- **`provision(project_id, repo, tool) → (connection_handle | error)`** — vytvoří nebo
  obnoví prostředí; smí být idempotentní; vrátí connection handle POUZE pokud enforcement
  je aktivní; jinak vrátí chybu.
- **`teardown(project_id) → error?`** — odstraní prostředí; idempotentní.
- **`sleep(project_id) → error?`** — advisory; provider smí ignorovat.
- **`health() → (ok | degraded)`** — stav providera; volá se z `healthz`.

Connection handle vrácený providerem je opaque string pair (`control_url`, `terminal_url`);
server ho předá beze změny do `Environment.connection`. Handle nesmí obsahovat substrát-noun
dle kontraktu §7 (AC-11).

## Edge cases & otevřené otázky

- **`ensure` na `destroyed` prostředí:** kontrakt říká destroy je nevratné; `ensure` po
  destroy by logicky vytvořilo nové prostředí (none → provisioning). Toto chování musí být
  explicitně potvrzeno — zatím předpokládám „nové prostředí" (destroy nemaže záznamy, jen
  přepíná stav; `ensure` na `destroyed` = nový provisioning run).
- **Sleep semantika při probíhajícím ensure:** co se stane, pokud klient volá `sleep` zatímco
  prostředí je v `provisioning`? Pravděpodobně no-op nebo `2xx` s aktuálním stavem — definovat.
- **Provider health vs server health:** `healthz` vrací `status: ok | degraded`; kdy je
  `degraded` vs `503`? Navrhuju: provider odpovídá → `degraded`; provider nedosažitelný →
  `503 ERR_RUNTIME_UNAVAILABLE`.
- **Opaque connection v dev provideru:** dev provider vrátí placeholder URL (např.
  `http://localhost:9999`); toto musí projít AC-11 grep testem (žádný substrát-noun).
