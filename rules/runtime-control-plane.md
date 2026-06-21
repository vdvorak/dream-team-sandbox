---
type: rules
layer: runtime-control-plane
owner: ted-architect
normative: true
contract: contracts/runtime-contract.md v1.1.0 · contracts/api/runtime.openapi.yaml
slice: 1 (lifecycle core)
---
# Rules — runtime control-plane (vnitřní architektura serveru)

Tech-agnostická-kde-to-jde, jinak konkrétní (rules/ je INTERNÍ — smí jmenovat substrát).
Normativní (MUST / MUST NOT). Kontrakt (`contracts/runtime-contract.md` v1.1.0 +
`runtime.openapi.yaml`) je **autorita a NEMĚNÍ se** (změna = L3). Tato pravidla popisují, jak
postavit server, který kontrakt naplní, a definují rozhraní, která spec záměrně vynechal.
Implementátor = bob-backend; diagnostika = ted/heimdall/joey. *Architecture is forever.*

## RCP-A1 — Vrstvy serveru (Router → Service → Repository)

- **MUST** dodržet 3 vrstvy (konvence bob-backend, scaffold `example/`):
  - **Router** (`src/runtime/router.py`) — JEN HTTP: routing, dekódování path/body, Pydantic
    request/response shape, `Depends` auth, mapování `RuntimeError`→HTTP envelope. **MUST NOT**
    nést lifecycle logiku, state-machine rozhodnutí ani volání providera.
  - **Service** (`src/runtime/service.py`) — lifecycle logika, **state machine**, fail-closed
    rozhodnutí, **serializace per `project_id`**, volání enforcement-provideru, mapování
    interní→app-facing chyby. Žádný HTTP import (`Request`/`Response`) — testovatelný bez ASGI.
  - **Repository** (`src/runtime/repository.py`) — JEN úložiště stavu prostředí. Slice 1 =
    **in-memory** `dict[project_id, EnvironmentRecord]`. Žádná business logika, žádné fail-closed
    rozhodnutí. **MUST NOT** mazat `destroyed` záznam (drží se pro `GET`→destroyed a `ensure`-po-destroy).
- **MUST:** serializace souběhu (`asyncio.Lock` per `project_id`) leží ve **service**, ne v
  routeru ani repository (RCP-1d). Lock chrání read-modify-write nad jedním `project_id`; různé
  `project_id` běží paralelně.
- **MUST NOT:** importovat SQLAlchemy / `database.get_db` / `AsyncSession` (slice 1 `touches_db:
  false`). Scaffold `example/` je DB-vázaný — **nepřebírat jeho DB závislost**, jen tvar vrstvení.

## RCP-A2 — Enforcement-provider rozhraní (spec ho vynechal — definice zde, load-bearing)

Abstraktní hranice mezi control-plane serverem a bezpečnostním enforcementem (ZEĎ). Spec
(`§Zaměnitelný enforcement provider`) ho žádá vyměnitelný; tvar je architektonický.

- **MUST:** `EnforcementProvider` = Python `Protocol` (nebo ABC) v `src/runtime/enforcement/provider.py`
  se **dvěma async operacemi** a žádnou třetí cestou:
  - `async ensure_active(project_id: str, repo: RepoSpec, tool: str) -> EnforcementOutcome`
  - `async health() -> ProviderHealth`  (`ok | degraded | unavailable`; pro `healthz` RCP-9c)
- **MUST — dvouhodnotový výsledek (fail-closed, žádná třetí cesta):** `ensure_active` vrátí
  výhradně jeden ze dvou tvarů, modelovaných jako uzavřený součtový typ (NE bool + nullable
  handle, NE výjimka místo hodnoty pro očekávané selhání):
  - `EnforcementActive(handle: ConnectionHandle)` — enforcement je **prokazatelně aktivní** a
    nese **opaque** connection handle (control_url + terminal_url).
  - `EnforcementFailed(kind: FailureKind, internal_code: str | None)` — enforcement nelze
    aplikovat ani ověřit. `kind ∈ {provider_error, provider_unreachable}`. `internal_code` je
    interní cage kód (`contracts/error-codes.md`) NEBO `None` — **drží se JEN pro log/observability
    uvnitř runtimu, NIKDY se neserializuje navenek** (viz RCP-A5).
- **MUST NOT:** žádný „best-effort" / „pusť to ven, když nejde enforcement" stav. Žádná
  cesta, kde service nastaví `ready` bez `EnforcementActive` (CE-2 paralela; spec §Fail-closed).
- **MUST:** `ConnectionHandle` produkuje provider (ne service) — provider zná substrát, service ne.
  Service handle jen předá do `Connection` response beze změny (opacita, kontrakt §1).
- **Dvě implementace (slice 1):**
  - **`DevEnforcementProvider`** (`enforcement/dev.py`, slice 1 default): reálný enforcement
    **NEVYNUCUJE** (provoz nasucho — spec). Vrací `EnforcementActive` s **opaque stub handle**
    (viz RCP-A6 / riziko E pro tvar URL). Konfigurovatelný do tří režimů pro testy (RCP-2):
    `active` (default) | `fail` (→ `EnforcementFailed(provider_error)`) | `down`
    (→ `EnforcementFailed(provider_unreachable)`).
  - **`CageEnforcementProvider`** (`enforcement/cage.py`, **STUB — neimplementovat v slice 1**):
    rozhraní + napojovací bod. Reálná integrace volá existující ZEĎ (`server/cage/**`:
    host-policy applier / overlay / deploy) — **tenká adaptérová vrstva**: přeloží `ensure_active`
    na cage operaci (ověř aktivní host-enforced policy + získej connection k workspace), chytí
    `CageError` (`server/cage/errors.py`) a přeloží na `EnforcementFailed(kind, internal_code=e.code)`.
    **MUST NOT** v slice 1 reálně volat cage (cage integrace je OUT — stack §Co je OUT). Jen
    deklarovat rozhraní a TODO napojovací bod.
- **MUST:** výběr provideru přes config (`pydantic-settings`, `enforcement_provider: dev | cage`).
  **Default = `dev`.** Bez nakonfigurovaného provideru → server **odmítne start** NEBO vrátí
  `503 ERR_RUNTIME_UNAVAILABLE` na každý lifecycle request (RCP-2d) — NIKDY `200 ready`.

## RCP-A3 — Fail-closed bod (jediný, load-bearing)

- **MUST:** `status: ready` se v service nastaví **VÝHRADNĚ** v jediném místě — bezprostředně po
  `ensure_active(...) == EnforcementActive`. Tento řádek je **jediná brána k `ready`**; nesmí
  existovat jiná cesta, kterou se prostředí dostane do `ready`.
- **MUST — mapování výsledku na stav/HTTP (kontrakt §4):**
  - `EnforcementActive` → `status: ready`, `connection` = handle → `200`.
  - `EnforcementFailed(provider_error)` → prostředí NESMÍ být `ready`; zůstane `provisioning`
    NEBO `502 ERR_PROVISION_FAILED` (RCP-2b).
  - `EnforcementFailed(provider_unreachable)` → `503 ERR_RUNTIME_UNAVAILABLE`; NIKDY `200 ready`
    (RCP-2c). `503` je fail-closed default i pro „provider vůbec nenakonfigurován" (RCP-2d).
- **MUST:** `healthz` reportuje `degraded` (NE `ok`), když `provider.health()` ≠ `ok` (RCP-9c);
  `unavailable` → `200 degraded` nebo `503`, NIKDY tiché `ok`. `healthz` je `security: []` veřejný
  (RCP-14c) — JEDINÝ endpoint bez auth.

## RCP-A4 — Stavový automat (implementačně)

Stavy = kontrakt §2: `none → provisioning → ready → asleep | destroyed`. Service je jediný
mutátor; repository jen drží `EnvironmentRecord`.

- **MUST — přechody:**
  - `ensure` na `none` (nikdy nevzniklo / po `destroyed`) → nový `provisioning` cyklus → (fail-closed
    brána RCP-A3) → `ready` / chyba. Po `destroyed` = **čisté nové prostředí** (fresh; kontrakt §2,
    RCP-5d) — žádný zbytkový stav z předchozí inkarnace (repo, handle, phase se resetují).
  - `ensure` na `ready` se **stejným `repo.url`** → idempotentní no-op-sync, vrátí totéž `ready`;
    NEVZNIKNE druhé prostředí (RCP-1c).
  - `ensure` na `ready`/`provisioning`/`asleep` s **jiným `repo.url`** → `409 ERR_REPO_MISMATCH`;
    prostředí **nedotčeno** (RCP-1e; 1 prostředí = 1 repozitář, kontrakt §2). Porovnání na
    normalizovaném `url` (ne na `ref`).
  - `ensure` na `asleep` → wake → nový `provisioning`→`ready` cyklus (idempotentní z pohledu klienta,
    RCP-S4).
  - `sleep` → advisory: stav přejde na `asleep` NEBO zůstane `ready` (obojí PASS, RCP-4a).
    Idempotentní na `asleep` (RCP-4b). Na `destroyed`/`none` → `200` nebo `404`, NIKDY `5xx`
    (RCP-4c/4d). Edge: `sleep` při `provisioning` → `200` s aktuálním stavem, **příprava se
    NEPŘERUŠÍ** (spec Edge cases).
  - `destroy` z **kteréhokoli** stavu → `destroyed` (NEBO `202` při async); idempotentní (RCP-5b).
    Na `none` → `200` nebo `404`, NIKDY `5xx` (RCP-5c).
- **MUST — idempotence & no-5xx:** `sleep`/`destroy` opakované NEBO na neexistující `project_id`
  NIKDY nevrátí `5xx` (kontrakt §2; RCP-4/5). Idempotence řeší service (kontrola aktuálního stavu),
  ne klient.
- **MUST — souběh:** souběžné `ensure` pro tentýž `project_id` serializované `Lock`em → vznikne
  **jedno** prostředí; race NIKDY nevrátí dvě různá `ready`, NIKDY `5xx` (RCP-1d, kontrakt §2).
- **MUST:** `phase` (volný string, NE enum) je přítomen typicky při `provisioning` (RCP-3e). Mimo
  `ready` je `connection: null` (RCP-3d). `contract_version: "1.1.0"` v **každém** `Environment`
  response (RCP-1b) i v `healthz` — jediný zdroj (konstanta/config), drift-check shoda (RCP-9b).

## RCP-A5 — Nepropustnost interních chyb (kontrakt §4, load-bearing)

Interní cage kódy (`contracts/error-codes.md`: `ERR_NO_POLICY`, `ERR_PROXY_DOWN`,
`ERR_INVM_FW_FAILED`, …) se **NIKDY** nepromítnou do app-facing roviny.

- **MUST:** jediné místo překladu interní→app-facing je **service** (NE router, NE provider).
  Provider vrátí `EnforcementFailed(kind, internal_code)`; service přeloží na app-facing kód
  **dle `kind`**, NIKDY dle `internal_code`:

  | provider výsledek | app-facing | HTTP |
  |---|---|---|
  | `EnforcementFailed(provider_error, *)` | `ERR_PROVISION_FAILED` | `502` |
  | `EnforcementFailed(provider_unreachable, *)` | `ERR_RUNTIME_UNAVAILABLE` | `503` |
  | provider nenakonfigurován | `ERR_RUNTIME_UNAVAILABLE` | `503` |

- **MUST NOT:** `internal_code` (ani `CageError.detail`, ani `str(exc)`, ani stacktrace) se
  objeví v `Error.message`, `Error.detail`, hlavičce ani logu doručeném klientovi. `internal_code`
  patří JEN do server-side observability logu. App-facing `detail` (`additionalProperties: true`)
  smí nést jen NE-substrátová, NE-cage data (např. `{retry_after: N}`), nikdy enforcement důvod.
- **MUST:** app-facing envelope smí nést jen kódy z kontraktu §8 (enum v OpenAPI `Error.code`,
  RCP-11b). Žádný `ERR_CAGE_*` / `ERR_NO_POLICY` / `ERR_PROXY_DOWN` navenek (RCP-11b).
- **Diagnostický signál:** dvojnásobnou roli kódů hlídá grep test (RCP-11b) — app-facing kódy ⊆ §8;
  průnik s `contracts/error-codes.md` = 0.

## RCP-A6 — Agnostika app-facing roviny (kontrakt §7; rizika C/D/E)

App-facing rovina (response body, error kódy, `connection` URL) **MUST** zůstat substrátem-agnostická.
Rules/ smí být konkrétní; **navenek nesmí** uniknout žádný substrát-noun (kontrakt §7, RCP-11).

- **Riziko A — `tool` validace → `400`, NE `422`.** **MUST:** `tool` validovat **allowlistem ve
  service vrstvě** (nepodporovaný → `400 ERR_TOOL_NOT_ALLOWED`). **MUST NOT** modelovat `tool` jako
  Pydantic `Enum`/`Literal` — to dá `422` (schema validace), což je špatný kód i špatná vrstva
  (RCP-1f). V OpenAPI/Pydantic `tool: str` (volný), business kontrola je service.
- **Riziko B — error envelope `{code, message, detail}`, NE scaffold `{code, details}`.**
  **MUST:** implementovat envelope dle kontraktu §8 / OpenAPI `Error` (`code` povinné, `message`
  povinné, `detail` optional `object`). **MUST NOT** použít scaffold `shared/errors.py` 1:1 —
  jeho shape je `{code, details}` (chybí `message`, jiný klíč). Net-new `RuntimeApiError`
  (`src/runtime/errors.py`) nese `code, message, detail, http_status`; exception handler serializuje
  přesně `{code, message, detail?}`. **MUST:** týž envelope produkuje i handler schema-validačních
  chyb (`RequestValidationError` → `ERR_INVALID_REQUEST` `400`, riziko D) — žádná operace nesmí vrátit
  FastAPI default `422 {detail:[...]}`, ten porušuje §8 shape.
- **Riziko C — OpenAPI drift: kontrakt je autorita.** **MUST:** `runtime.openapi.yaml` je
  **autoritativní** artefakt; FastAPI-generovaný `/openapi.json` se proti němu drift-checkuje.
  **Tolerovatelný sémantický ekvivalent** (NENÍ drift-fail): nullable `connection` zapsané FastAPI
  jako `anyOf: [Connection, {type: null}]` místo kontraktního `oneOf: [Connection, {type: null}]`
  — `oneOf` vs `anyOf` u disjunktní `{T | null}` je sémanticky ekvivalentní (hodnota je buď
  `Connection`, nebo `null`, nikdy obojí). **Drift-fail (NENÍ tolerovatelné):** odlišný set polí,
  jiné `required`, jiný `enum` (zúžení/rozšíření app-facing error kódů), chybějící operace, jiné
  HTTP kódy, jiný `additionalProperties`. Shoda `contract_version` je tvrdá (RCP-9b).
- **Riziko D — `additionalProperties: false` i na vnořeném `repo`; schema-chyba → `400 ERR_INVALID_REQUEST`.**
  **MUST:** `extra="forbid"` (`ConfigDict`) platí na `EnsureRequest` **i** na vnořeném `repo` objektu —
  extra pole jako `repo.firewall`, `repo.egress`, `repo.policy` (bypass-pokus) → `400` (RCP-1h/12b/13b).
  OpenAPI to už vyžaduje (`EnsureRequest.additionalProperties: false` **a**
  `EnsureRequest.repo.additionalProperties: false`). **MUST:** modelovat `repo` jako vlastní vnořený
  Pydantic model s `extra="forbid"`, NE `dict`/`Any` (ten by bypass propustil).
- **MUST — přesný kód+status pro schema-selhání (kontrakt §8, `contract_version 1.1.0`):** jakákoli
  Pydantic/schema-validační chyba request body — **neznámé/zakázané pole** (vč. enforcement-bypass
  kdekoli v body i v `repo.*`), **chybějící required** pole, **špatný typ**, **nevalidní tvar `repo.url`**
  — **MUST** být serializována jako **`400` s app-facing kódem `ERR_INVALID_REQUEST`** v envelope
  `{code, message, detail?}` (RCP-1h/12b/13b/1g). **MUST NOT** propustit FastAPI/Pydantic **default
  `422` `{detail:[...]}`** (jiný status i jiný shape než kontrakt §8) — router **MUST** zaregistrovat
  handler na `RequestValidationError` (a Pydantic `ValidationError`), který přemapuje na
  `ERR_INVALID_REQUEST` + `400` + envelope §8. **MUST NOT** mapovat schema-chybu na `ERR_CLONE_FAILED`
  (`422`, sémanticky „klon selhal za běhu", ne schema) ani na `ERR_TOOL_NOT_ALLOWED` (to je výhradně
  business allowlist `tool`, riziko A). Extra pole / bypass-pokus = `400 ERR_INVALID_REQUEST`, NIKDY
  tiché přijetí (AC-12c).
- **Hranice dvou `400` kódů (load-bearing, kontrakt §8):** `ERR_INVALID_REQUEST` = **schéma** body
  nesedí (router/handler na validation error). `ERR_TOOL_NOT_ALLOWED` = body schématicky validní, ale
  hodnota `tool` mimo allowlist (**service** vrstva, riziko A). Disjunktní trigger; obojí `400`.
- **Riziko E — dev-provider connection URL: opaque, bez substrát-nounu, bez portu 808x.**
  **MUST:** `DevEnforcementProvider` generuje `control_url`/`terminal_url`, které **NEOBSAHUJÍ**
  žádný substrát-identifikátor: ne `Fly`/`fly.dev`/`docker`/`6PN`/`.internal`, ne public IP, **ne
  port `:808x`** (RCP-11c/3b). **MUST:** použít opaque host + opaque token segment, např.
  `https://rt.<opaque-id>.example/control/<opaque-token>` a `wss://rt.<opaque-id>.example/terminal/<opaque-token>`
  — bez portu, bez substrát-nounu, neodvoditelný substrát. `terminal_url` schéma `wss://` (WS),
  `control_url` `https://`. Handle je **neprůhledný**: klient ho použije beze změny a nezjistí z něj,
  na čem prostředí běží (spec §Neprůhledné handly, kontrakt §1).

## RCP-A7 — Auth (App→Runtime)

- **MUST:** každá lifecycle operace (`ensure`/`get`/`sleep`/`destroy`) vyžaduje App→Runtime
  identitu (FastAPI `Depends`). Slice 1 dev-mode = **service token** (`Authorization: Bearer`);
  mTLS je produkční primární (kontrakt §3) — slice 1 ho nevyžaduje pro lokální testovatelnost.
- **MUST:** chybí/neplatná identita → `401 ERR_UNAUTHORIZED`, **NIKDY `5xx`** (RCP-14a). Platná
  identita → operace běží (jiná business chyba je OK, ale NE `401`, RCP-14b).
- **MUST:** `GET /v1/healthz` = veřejný (`security: []` v OpenAPI), bez auth → `200` (RCP-14c).
- **MUST NOT:** žádné control-API pole/hlavička/query přijímá nebo vrací **BYOK / AI tool token**
  (kontrakt §3, RCP-13a). `EnsureRequest` přijímá JEN `repo` + `tool` (`extra="forbid"` to vynutí,
  RCP-13b). BYOK vstupuje výhradně interaktivně uvnitř PTY (deferred slice).

## RCP-A8 — ZEĎ-disjunktnost (kontrakt §4; RCP-12)

- **MUST NOT:** žádná operace/parametr/query/hlavička/pole zmírňuje, nastavuje ani odhaluje
  egress/ingress/shell enforcement (kontrakt §4, RCP-12a). OpenAPI to garantuje (žádné takové pole);
  service NESMÍ přidat skryté chování reagující na neznámé pole.
- **MUST NOT:** žádná response vrací `policy`/`ruleset`/`allowlist`/`capability` jako pole (RCP-12c).
- **MUST:** pokus o enforcement-bypass pole (`firewall`/`egress`/… kdekoliv v body včetně `repo.*`)
  → `400 ERR_INVALID_REQUEST` (schema-chyba `additionalProperties:false`; RCP-A6 riziko D), NIKDY
  tiché ignorování s oslabením ZDI (AC-12c).

## Reuse decision (per constitution §Reuse policy)

| pattern | kategorie | rozhodnutí |
|---|---|---|
| Router→Service→Repository vrstvení | **scaffold-only** | Tvar z `example/` scaffold (stack-defined). MUST převzít vrstvení, NE DB závislost (`touches_db: false`). |
| Pydantic v2 modely ↔ OpenAPI shape | **reuse-existing** | Stack-defined (FastAPI 0.115 + Pydantic v2). `extra="forbid"` = `additionalProperties: false`. |
| `pydantic-settings` config | **reuse-existing** | Scaffold `config.py` Settings pattern; rozšířit o `enforcement_provider`, `service_token`. |
| Error envelope | **feature-local** | Scaffold `{code, details}` NEVYHOVUJE (riziko B). Net-new `RuntimeApiError` + handler `{code, message, detail}` dle kontraktu §8. NEsdílet se scaffoldem (jiný shape). |
| `healthz` | **feature-local** | Scaffold `shared/health.py` nezná `contract_version` ani provider degradaci (RCP-9). Net-new runtime healthz. |
| Cage error registr (`server/cage/errors.py`, `CageError`) | **reuse-existing (read-only)** | Reálný `CageEnforcementProvider` (deferred) chytá `CageError` a mapuje na `EnforcementFailed`. NEROZŠIŘOVAT registr; čte se jen pro překlad (RCP-A5). |
| `EnforcementProvider` abstrakce | **feature-local (slice 1)** | Net-new; 1 výskyt → žádný extract teď. Sledováno jako Extraction Candidate (viz níže) — 2. spotřebitel (např. budoucí MOTOR/workspace provider) povýší na `extract-shared`. |

**Žádný `extract-shared` teď** (žádný pattern nemá 2+ výskyt v slice 1). Žádný net-new sdílený
building block. Stack-defined bloky (FastAPI/Pydantic/scaffold vrstvení) mají hard přednost a
jsou použity.

## Co je net-new vs reuse (souhrn pro implementátora)

- **Net-new:** `src/runtime/{router,service,repository,models,errors}.py`,
  `src/runtime/enforcement/{provider,dev,cage}.py`, runtime healthz, config rozšíření.
- **Reuse:** vrstvení (scaffold), Pydantic/FastAPI/OpenAPI generování, `pydantic-settings`,
  `CageError` registr (read-only, deferred provider).
- **NEpoužít:** scaffold `shared/errors.py` (jiný envelope shape), SQLAlchemy/`database.py`/`get_db`
  (no DB v slice 1).
