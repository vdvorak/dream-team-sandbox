# Acceptance criteria — runtime-control-plane (slice 1+2a)

Slice 1+2a scope: lifecycle core (`ensure` / `get` / `sleep` / `destroy` / `healthz`),
stavový automat, fail-closed garance, enforcement-provider rozhraní, auth, stav repozitáře
(AC-6), seznam souborů (AC-7). Terminál (AC-8) deferred na wave 2b.

Tagger: `[security]` `[integration]` `[automated]` `[manual E2E]`

---

## Přehled: které AC z runtime-contract jsou IN-SCOPE vs DEFERRED

| AC | Název | Stav |
|---|---|---|
| AC-1 | ensure | **IN** (slice 1) |
| AC-2 | fail-closed / ZEĎ garance | **IN** (slice 1+2a — reálný CageEnforcementProvider) |
| AC-3 | get + opaque connection | **IN** (slice 1) |
| AC-4 | sleep | **IN** (slice 1) |
| AC-5 | destroy | **IN** (slice 1) |
| AC-6 | git status | **IN** (wave 2a) |
| AC-7 | files | **IN** (wave 2a) |
| AC-8 | terminal / PTY | DEFERRED (wave 2b) |
| AC-9 | healthz | **IN** (slice 1+2a — reálný provider.health()) |
| AC-10 | standalone usability | **IN** (bez PTY kroků) |
| AC-11 | agnostika kontraktu | **IN** (slice 1) |
| AC-12 | ZEĎ-disjunktnost | **IN** (slice 1) |
| AC-13 | BYOK neteče | **IN** (slice 1) |
| AC-14 | auth odběratele | **IN** (slice 1) |

Kritéria níže jsou konkrétní na úrovni serveru (HTTP response, hlavičky, stavový automat).
Tam, kde existuje identické AC v `acceptance/runtime-contract.md`, je uvedena reference —
tato kritéria jsou aditivní (slice-level granularita implementace).

---

## RCP-1 — ensure: základní flow `[integration]` `[automated]`

Ref: AC-1.

| # | Podmínka | PASS |
|---|---|---|
| 1a | `POST /v1/environments/{id}/ensure` s platným `project_id`, `repo.url`, `tool` | `200` s `status: ready` nebo `202` s `status: provisioning` + hlavička `Retry-After` |
| 1b | Response body obsahuje `contract_version: "1.1.0"` | Přítomno v každém `Environment` objektu |
| 1c | Opakovaný `ensure` se stejným `project_id` + stejným `repo.url` na `ready` prostředí | `200 ready`; nevznikne druhé prostředí (idempotence) |
| 1d | Souběžné `POST ensure` pro tentýž `project_id` (2+ souběžné requesty) | Výsledek = jedno prostředí; race nevrátí dvě různá `ready`; žádný `5xx` |
| 1e | `ensure` s `repo.url` jiným než u živého prostředí | `409` s kódem `ERR_REPO_MISMATCH`; prostředí nedotčeno |
| 1f | `ensure` s neplatným `tool` (hodnota mimo povolený seznam) | `400` s kódem `ERR_TOOL_NOT_ALLOWED` |
| 1g | `ensure` s nevalidním `repo.url` (syntakticky chybné URI) | `400 ERR_INVALID_REQUEST` (schema-validace); `422` v tomto scénáři = FAIL; nikdy `5xx` |
| 1h | `ensure` s extra polem v request body (např. `"firewall": "off"`) | `400 ERR_INVALID_REQUEST` (additionalProperties odmítnuto); nikdy tiché přijetí — AC-12c |

---

## RCP-2 — fail-closed garance `[security]` `[integration]`

Ref: AC-2.

| # | Podmínka | PASS |
|---|---|---|
| 2a | Dev provider spuštěn; `ensure` dokončeno → provider reportuje enforcement active | `getEnvironment` vrátí `status: ready`; `connection` neprázdné |
| 2b | Provider konfigurován tak, aby vrátil chybu enforcement (simulace selhání) | `getEnvironment` NESMÍ vrátit `status: ready`; vrátí `502 ERR_PROVISION_FAILED` nebo `status: provisioning` |
| 2c | Provider nedosažitelný (simulace výpadku) | `ensure` vrátí `503 ERR_RUNTIME_UNAVAILABLE`; nikdy `200 ready` |
| 2d | Server je spuštěn bez jakéhokoli nakonfigurovaného providera | Server odmítne startovat nebo vrátí `503` na každém požadavku; nikdy `200 ready` |

---

## RCP-3 — get environment + opaque connection `[integration]` `[automated]`

Ref: AC-3.

| # | Podmínka | PASS |
|---|---|---|
| 3a | `GET /v1/environments/{id}` pro `ready` prostředí | `200` s `connection.control_url` a `connection.terminal_url` neprázdnými |
| 3b | `connection` URL grep: `Fly\|docker\|6PN\|\.internal\|:808[0-9]` | 0 výskytů v obou URL (AC-11c) |
| 3c | `GET /v1/environments/{id}` pro neexistující `project_id` | `404` s kódem `ERR_ENVIRONMENT_NOT_FOUND` |
| 3d | `GET /v1/environments/{id}` pro `asleep` nebo `destroyed` prostředí | `connection: null`; `status` korektně uveden |
| 3e | `GET /v1/environments/{id}` pro prostředí v `provisioning` | `connection: null`; `status: provisioning`; přítomen `phase` string (neprázdný, libovolná hodnota) |

---

## RCP-4 — sleep `[integration]` `[automated]`

Ref: AC-4.

| # | Podmínka | PASS |
|---|---|---|
| 4a | `POST /v1/environments/{id}/sleep` na `ready` prostředí | `200`; stav přejde na `asleep` nebo zůstane `ready` (advisory) — obojí PASS |
| 4b | `POST sleep` na `asleep` prostředí (idempotence) | `200`; nikdy `5xx` |
| 4c | `POST sleep` na `destroyed` prostředí | `200` nebo `404`; nikdy `5xx` |
| 4d | `POST sleep` na neexistující `project_id` | `200` nebo `404`; nikdy `5xx` |

---

## RCP-5 — destroy `[integration]` `[automated]`

Ref: AC-5.

| # | Podmínka | PASS |
|---|---|---|
| 5a | `DELETE /v1/environments/{id}` na existující prostředí | `200` nebo `202`; následné `getEnvironment` vrátí `404` nebo `status: destroyed` |
| 5b | `DELETE /v1/environments/{id}` opakovaně (idempotence) | `200` nebo `404`; nikdy `5xx` |
| 5c | `DELETE /v1/environments/{id}` na neexistující `project_id` | `200` nebo `404`; nikdy `5xx` |
| 5d | Stav po destroy: `ensure` na `destroyed` `project_id` | Spustí nový provisioning (nové prostředí); stav přejde do `provisioning`/`ready` |

---

## RCP-9 — healthz `[automated]`

Ref: AC-9.

| # | Podmínka | PASS |
|---|---|---|
| 9a | `GET /v1/healthz` bez auth | `200` s `status ∈ {ok, degraded}` a `contract_version: "1.1.0"` |
| 9b | `contract_version` v healthz = `contract_version` v každém `Environment` response | Shoduje se (drift-check manuálně; CI fixture deferred na app-side wave) |
| 9c | Provider nedosažitelný → healthz | `200 degraded` nebo `503`; nikdy tiché `ok` při výpadku providera |

---

## RCP-10 — standalone usability bez aplikace (slice 1 rozsah) `[manual E2E]`

Ref: AC-10 (zkrácená verze — bez git/files/PTY kroků, které jsou deferred).

Scénář: generický klient (curl) projde lifecycle bez aplikačního kódu.

| Krok | Akce | PASS |
|---|---|---|
| S1 | `POST ensure` s libovolným `project_id` + repo URL (nebo stub URL u dev providera) | Dosáhne `ready` (přes `202` polling nebo přímý `200`) |
| S2 | `GET {project_id}` | `200 ready`; `connection` neprázdné |
| S3 | `POST sleep` | `200`; stav `asleep` nebo `ready` |
| S4 | `POST ensure` znovu | `200 ready` (wake from asleep, idempotentní) |
| S5 | `DELETE {project_id}` | `200`/`202`; následný `GET` = 404/destroyed |
| S6 | `GET /v1/healthz` | `200 ok` |

Podmínka: žádný krok nevyžaduje aplikační kód; stačí service token nebo dev-mode auth.

---

## RCP-11 — agnostika kontraktu `[security]` `[automated]`

Ref: AC-11.

| # | Podmínka | PASS |
|---|---|---|
| 11a | Grep všech response bodies v integračních testech | `Fly\|Docker\|nftables\|6PN\|tmux\|WORKSPACE_AGENT_BASE` = 0 výskytů v polích ani hodnotách |
| 11b | Grep app-facing error kódů vrácených serverem | Žádný substát-specifický identifikátor; pouze kódy z kontraktu §8 |
| 11c | `connection` URL z dev providera jsou opaque (bez substrát-noun) | Regex AC-3b grep = 0 výskytů |

---

## RCP-12 — ZEĎ-disjunktnost `[security]`

Ref: AC-12.

| # | Podmínka | PASS |
|---|---|---|
| 12a | Revize OpenAPI schématu (strojová validace) | Žádný parametr, query, request/response pole neumožňuje zmírnit enforcement |
| 12b | `ensure` s extra polem simulujícím enforcement bypass | Request odmítnut `400 ERR_INVALID_REQUEST` (additionalProperties:false) — viz RCP-1h |
| 12c | Žádná operace nevrátí detaily ZDI (ruleset, policy, capability seznam) | Grep response schématu = 0 výskytů pro `policy\|ruleset\|allowlist\|capability` jako response pole |

---

## RCP-13 — BYOK token neteče přes control API `[security]`

Ref: AC-13.

| # | Podmínka | PASS |
|---|---|---|
| 13a | OpenAPI schéma + server code review | Žádné pole nepřijímá ani nevrací AI tool token nebo credential |
| 13b | `EnsureRequest` odmítne jakékoli pole nesouvisející s `repo` a `tool` | `400 ERR_INVALID_REQUEST` (additionalProperties:false) — viz RCP-1h |

---

## RCP-14 — auth odběratele `[security]` `[integration]`

Ref: AC-14.

| # | Podmínka | PASS |
|---|---|---|
| 14a | Libovolná operace bez autentizace (bez Bearer, bez mTLS) | `401` s kódem `ERR_UNAUTHORIZED`; nikdy `5xx` |
| 14b | Operace s platnou identitou (service token v dev modu) | Operace provedena nebo jiná business chyba (`4xx` non-auth); nikdy `401` |
| 14c | `GET /v1/healthz` bez auth | `200` (healthz je veřejný endpoint — `security: []` v OpenAPI) |

---

---

## RCP-6 — git status v prostředí `[integration]` `[automated]`

Ref: AC-6.

| # | Podmínka | PASS |
|---|---|---|
| 6a | `GET /v1/environments/{project_id}/git` na `ready` prostředí | `200` s tělem obsahujícím: `status` (čisté/dirty), informace o větvi, seznam necommitovaných souborů |
| 6b | `GET /v1/environments/{project_id}/git` na prostředí v jiném stavu než `ready` | `409 ERR_ENVIRONMENT_NOT_READY`; nikdy `5xx` |
| 6c | `GET /v1/environments/{project_id}/git` pro neexistující `project_id` | `404 ERR_ENVIRONMENT_NOT_FOUND` |
| 6d | Response body neobsahuje žádný substrát-noun (Fly, docker, 6PN, .internal, workspace layout) | Grep response body: žádný výskyt substrát-nounu z §7 kontraktu |
| 6e | `GET /v1/environments/{project_id}/git` bez autentizace | `401 ERR_UNAUTHORIZED`; nikdy `5xx` |

---

## RCP-7 — seznam souborů v prostředí `[integration]` `[automated]`

Ref: AC-7.

| # | Podmínka | PASS |
|---|---|---|
| 7a | `GET /v1/environments/{project_id}/files` (bez parametru nebo `path=/`) na `ready` prostředí | `200` se seznamem souborů a složek v workspace root |
| 7b | `GET /v1/environments/{project_id}/files?path=<validní-podadresář>` | `200` se seznamem obsahu daného podadresáře |
| 7c | `GET /v1/environments/{project_id}/files?path=../../etc/passwd` nebo jiný path traversal mimo workspace | `403 ERR_PATH_ESCAPE`; nikdy `5xx`; žádný obsah mimo workspace |
| 7d | `GET /v1/environments/{project_id}/files` na prostředí v jiném stavu než `ready` | `409 ERR_ENVIRONMENT_NOT_READY`; nikdy `5xx` |
| 7e | `GET /v1/environments/{project_id}/files` pro neexistující `project_id` | `404 ERR_ENVIRONMENT_NOT_FOUND` |
| 7f | Response body neobsahuje interní workspace layout (overlay dirs, entrypoint.sh apod.) | Ověření: interní artefakty cage nejsou viditelné klientovi |
| 7g | `GET /v1/environments/{project_id}/files` bez autentizace | `401 ERR_UNAUTHORIZED`; nikdy `5xx` |

---

## Deferred AC (wave 2b+)

| AC | Podmínka |
|---|---|
| AC-8 | `attachTerminal` (PTY/WS) — deferred na wave 2b (PTY + kontejner) |
| AC-10 S3/S4 | Standalone kroky pro terminal — deferred spolu s AC-8 |
