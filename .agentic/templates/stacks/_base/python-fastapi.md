---
cache_key: template-stack-python-fastapi-v2.0
type: template
---

# Stack — Python + FastAPI + SQLAlchemy(async) (kanonický reference)

**Zlatý standard** pro server target v tomto stacku. Watson seeduje obsah níže
(po `---` až po `## Pozn.`) do projektového `stack/server.md` a zkopíruje kostru
z `templates/scaffolds/python-fastapi/`. Cíl: **dva python projekty vypadají
strukturou i syntaxí skoro identicky.**

Tech-agnostic pravidla viz `rules/backend.md`. Hygiena viz `constitution.md`.
DB je swappable přes SQLAlchemy — `_db/postgres` (prod) nebo `_db/sqlite`
fragment určuje driver; kód zůstává stejný.

Odchylka od tohoto referenceu = vědomé rozhodnutí (Ted), ne drift.

---

## Technologie

- **Python 3.12+**, FastAPI (≥0.110), Uvicorn (ASGI)
- **Pydantic v2** — request/response modely, validace, settings (pydantic-settings)
- **SQLAlchemy Core (async, ≥2.0)** — DB přístup přes `text()` SQL + AsyncSession
- **Alembic** — migrace jako SQL-only runner nad `contracts/db/migrations/`
- DB driver: **asyncpg** (Postgres, prod) / **aiosqlite** (testy, portabilně)
- **structlog** — strukturované logování; **httpx** — HTTP/test klient
- Testy: **pytest + pytest-asyncio** (`asyncio_mode=auto`)
- DI: FastAPI `Depends`

Pouze deklarované knihovny (constitution); nová závislost vetted (Tony/Heimdall).

## Module struktura

```
server/src/
├── main.py            # create_app() factory: CORS, exception handlers, router includes
├── database.py        # async engine (lazy), session factory, get_db() dependency
├── config.py          # pydantic-settings Settings + lru_cache get_settings()
├── shared/
│   ├── errors.py      # ApiError + handler → {code, details}
│   └── health.py      # /health, /health/deep
└── <feature>/         # feature-module
    ├── router.py      # FastAPI APIRouter, Depends(get_db), response_model
    ├── service.py     # business logika; bez HTTP/SQL; raises ApiError
    ├── repository.py  # SQLAlchemy text() SQL přes AsyncSession; map row → pydantic
    └── models.py      # pydantic request/response modely + Enum pro výčty
```

Vrstvení viz `rules/backend.md` (Router→Service→Repository). Router jen
transport; service bez HTTP/SQL; repository jediný DB přístup.

## Shared infrastruktura (kopíruje se identicky, neduplikovat)

| Prvek | Účel |
|---|---|
| `ApiError(code, status, details)` | doménová chyba; `raise` místo ručního JSONResponse |
| `api_error_handler` | registrovaný v `create_app`; → `{code, details}` |
| `get_db()` | FastAPI dependency — yield AsyncSession (`database.py`) |
| `get_settings()` | `lru_cache` pydantic Settings z `.env` (`config.py`) |
| `/health`, `/health/deep` | liveness + DB readiness |

## DB přístup

- **SQLAlchemy Core, ne ORM**: repository skládá `text("... :param")` + params,
  mapuje `result.mappings().all()` → pydantic modely. Parametrizace vždy
  (žádné f-string SQL).
- Migrace = `contracts/db/migrations/V{N}__{name}.sql` (server-owned kontrakt,
  Alembic jako SQL-only runner). Prod: UUID PK, `TIMESTAMPTZ`, PG ENUM/CHECK.
- Transakce na hranici service operace; `commit()` po write.

## Mapping rules (spec element → implementace)

| Spec element | Implementace |
|---|---|
| endpoint | `@router.<method>` v `router.py`, `response_model=<Model>`, `Depends(get_db)` |
| request tělo | pydantic `BaseModel` v `models.py` (validace přes Field/typy) |
| response tělo | pydantic `BaseModel`; citlivá pole se neserializují |
| business logika | `Service(db)` v `service.py`; router jen deleguje |
| DB přístup | `Repository(db)` v `repository.py` přes `text()` SQL |
| chyba | `raise ApiError(code, status, details)`; kód z `contracts/error-codes.md` |

## Programming binding (Python realizace `rules/` + `constitution`)

- volitelnost: `X | None` (explicitní), ne implicitní `None` skrz vrstvy
- konečný výčet → `str, Enum` třída, ne volný string v business logice
- type hints na všech signaturách (params i návrat)
- service/repository = třídy s `__init__(self, db)`; router instancuje per request
- netriviální query vstup → explicitní request/filter pydantic model

## Error shape

`{code, details}` (viz `constitution.md` + `rules/error-responses.md`) — zde se
needuplikuje. `ApiError` nese `code` (z registru) + volitelný `details` dict.
Nikdy `str(exc)`/traceback v response. Pydantic validační chyba → 422 (FastAPI default).

## Testování

- `pytest` + `pytest-asyncio` (`asyncio_mode=auto`); `httpx.AsyncClient` +
  `ASGITransport(app)` proti `create_app()`
- Testy běží **portabilně proti SQLite** (aiosqlite) — bez Dockeru; conftest
  vytvoří schéma z `contracts/db/migrations/`. Prod/integrace proti Postgres.
- `DATABASE_URL` se nastaví v conftestu PŘED importem app
- minimální high-signal suite (1 success / operaci, 1 validace / pravidlo)

## Building blocks — declared

| Knihovna | Role |
|---|---|
| FastAPI + Uvicorn | HTTP framework + ASGI |
| Pydantic v2 + pydantic-settings | modely, validace, config |
| SQLAlchemy[asyncio] | DB přístup (Core, text SQL) |
| Alembic | migrace (SQL-only runner) |
| asyncpg / aiosqlite | driver (prod / test) |
| structlog, httpx | logy, HTTP klient |
| pytest + pytest-asyncio | testy |

## Scaffold

Reálná kostra: `templates/scaffolds/python-fastapi/` — shared infra + 1 ukázkový
vertical slice (`example/`) + testy proti SQLite. Watson ji kopíruje. Package je
generický (`src.shared`, `src.example`) — nepřejmenovává se.
Ted: stack-defined patterny = `scaffold-only` default.

## Extraction Candidates

| Pattern | Výskyty | Rozhodnutí |
|---|---|---|
| _(prázdné — Ted plní po každé wave)_ | | |

## Pozn. pro Watson

- Obsah od `## Technologie` po `## Extraction Candidates` se kopíruje do
  projektového `stack/server.md`.
- DB volba: přidej `_db/postgres` (prod default) nebo `_db/sqlite` fragment do
  Building blocks. Kód kostry je DB-agnostic.
- Po seedu zkopíruj kostru `scaffolds/python-fastapi/` do `server/` + `contracts/`.
