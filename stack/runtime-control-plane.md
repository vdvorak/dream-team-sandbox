---
feature-id: runtime-control-plane
type: stack
slice: 1 (lifecycle core)
owner: tony-cto
contract: contracts/runtime-contract.md v1.0.0 · contracts/api/runtime.openapi.yaml
---
# Stack — runtime-control-plane (slice 1)

Konkrétní technologické volby pro control-plane server. Spec
(`specs/runtime-control-plane.md`) a kontrakt jsou agnostické; tento soubor fixuje nástroje
a zdůvodnění. **Žádná závislost mimo framework `python-fastapi` scaffold** (viz
`.agentic/templates/scaffolds/python-fastapi/server/requirements.txt`) — slice 1 nepřidává
nový dep (stack-impact: NONE).

## Jazyk / runtime

- **Python 3.12** — konzistentní s existujícím `server/cage/**` a `tests/**` (pytest).
  Ověřeno: prostředí má 3.12.4.

## Web framework + server

- **FastAPI ≥ 0.115** (scaffold deklaruje `>=0.110`; nainstalováno 0.115.0).
  - Důvod: OpenAPI 3.1 nativně (FastAPI 0.99+ generuje 3.1), Pydantic v2 modely → schémata
    1:1 s `runtime.openapi.yaml`. `additionalProperties:false` (RCP-1h/12b/13b) =
    Pydantic `model_config = ConfigDict(extra="forbid")`.
  - `oneOf [Connection, null]` (Environment.connection) = `Connection | None` v Pydantic v2.
- **uvicorn[standard] ≥ 0.29** — ASGI server, standalone běh (`uvicorn src.main:app`).
- **ASGI / async** — async je správná volba: enforcement-provider call je I/O (v dev variantě
  trivální, v reálné variantě síťové volání na cage). Lifecycle handlery async, in-memory
  state mutace pod `asyncio.Lock` per `project_id` (viz Souběžnost níže).

## Validace dle kontraktu

- **Pydantic v2 ≥ 2.9** modely jako jediný zdroj request/response shape; FastAPI z nich
  generuje OpenAPI. **Drift-check**: vygenerovaný `/openapi.json` se v CI/testu porovná proti
  `contracts/api/runtime.openapi.yaml` (kontrakt je autorita — `architecture-is-forever`).
  Pokud FastAPI generuje 3.0-flavour detail (např. nullable přes `anyOf` místo `oneOf`),
  to NENÍ blocker — sémantika sedí; drift-check tolerantní na ekvivalentní 3.0/3.1 zápis.
- `project_id` pattern `^[A-Za-z0-9_-]+$` (1–128) = FastAPI Path param s `pattern`.
- `repo.url` `format: uri` → Pydantic validace; syntakticky chybné URI → `422 ERR_CLONE_FAILED`
  nebo `400` (RCP-1g). **Pozor**: chybný `tool` musí být `400 ERR_TOOL_NOT_ALLOWED`, ne 422 —
  tool validace je business (allowlist), ne schema; pořeš v service vrstvě, ne Pydantic enumem
  (enum by dal 422). Viz riziko B.

## Lifecycle state machine

- **In-memory** `dict[project_id, Environment]` + `asyncio.Lock` per `project_id`
  (serializace souběžného `ensure` — RCP-1d, kontrakt §2). Slice 1 NEMÁ trvanlivou persistenci
  (spec Out). „Přežití stavu mezi voláními" = po dobu běhu procesu; restart = prázdný stav
  (akceptovatelné pro slice 1, dokumentovat).
- Stavy `provisioning → ready → asleep / destroyed` dle kontraktu §2. `destroyed` se drží
  v mapě (ne smaž), aby `GET` mohl vrátit `destroyed` místo 404 a `ensure` po destroy spustil
  čistý cyklus (RCP-5a/5d).

## Enforcement-provider abstrakce

- **Protocol / ABC** `EnforcementProvider` se dvěma operacemi (async): `ensure_active(...)
  -> EnforcementResult` (active+handle | error — třetí možnost neexistuje, spec §Fail-closed)
  a `health() -> {ok|degraded|unavailable}` (RCP-9c).
- **Dvě implementace**: `DevEnforcementProvider` (reálný enforcement nevynucuje, vrací opaque
  stub `connection` URL — slice 1 default) a stub/placeholder pro reálný provider (interface
  jen; reálná cage integrace je OUT). Volba přes config/env (`pydantic-settings`).
- **Fail-closed v kódu**: `ready` se nastaví VÝHRADNĚ po `ensure_active` == active. Žádný
  provider → server odmítne start nebo `503` na každý request (RCP-2d). Provider error → ne-ready
  (`502 ERR_PROVISION_FAILED`); provider nedosažitelný → `503 ERR_RUNTIME_UNAVAILABLE` (RCP-2b/2c).
- **Nepropustnost**: provider interní chyby se NIKDY nemapují na app-facing detail — jen na
  `ERR_PROVISION_FAILED` / `ERR_RUNTIME_UNAVAILABLE` (kontrakt §4, RCP-11b).

## Auth (App→Runtime)

- Slice 1 = **service token** (`Authorization: Bearer`) jako dev-mode mechanismus; mTLS je
  produkční primární (kontrakt §3) ale pro lokální testovatelnost stačí token. FastAPI
  dependency, chybí/neplatný → `401 ERR_UNAUTHORIZED` (RCP-14a), nikdy `5xx`.
- `GET /v1/healthz` = `security: []` veřejný (RCP-14c, OpenAPI `security: []`).

## Error handling

- **Sdílený envelope** `{code, message, detail?}` (kontrakt §8). POZOR: scaffold
  `shared/errors.py` má shape `{code, details}` — runtime kontrakt vyžaduje `{code, message,
  detail}`. Nepoužít scaffold 1:1; implementovat envelope dle kontraktu §8 / OpenAPI `Error`
  schématu. Jen kódy z app-facing registru §8 (RCP-11b).

## Test approach

- **pytest + pytest-asyncio** (auto mode — `pyproject.toml` `asyncio_mode = "auto"`),
  **FastAPI `TestClient` / `httpx.ASGITransport`** — in-process integrační testy bez síťě,
  bez Fly, bez kontejneru. Pokrývá RCP-1..5/9/14 plně lokálně (`[integration][automated]`).
- **Dev provider** umožní deterministicky simulovat: active / provider-error / provider-down
  (RCP-2a/2b/2c) přes config injection.
- **Agnostika grepy** (RCP-3b/11a/11c/12c): test projede všechna response bodies regexem na
  substrát-nouny (`Fly|docker|6PN|.internal|:808x|nftables|tmux|policy|ruleset|...`) = 0 výskytů.
- **Schema drift test**: `app.openapi()` vs vendorovaný `runtime.openapi.yaml`.
- Layout: `tests/server/integration/` (analogicky k `tests/server/unit/`).

## Co je OUT (slice 1) — nepřidávat dep

- Reálné git clone, PTY/WebSocket data plane (`attachTerminal`), reálná cage integrace,
  trvanlivá persistence (DB), Fly deploy. WS endpoint v kontraktu existuje, ale AC-8 deferred —
  v slice 1 buď neimplementovat, nebo jen 101→close stub. `SQLAlchemy` ze scaffold requirements
  NENÍ pro slice 1 potřeba (has_db=false) — neinstalovat / neimportovat.

## Stack-impact

`NONE` — vše v rámci `python-fastapi` scaffold deps. Nový target: žádný (jen server).
Cross-target: žádný (no UI/mobile/desktop/web).
