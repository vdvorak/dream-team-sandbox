# Scaffold — Python + FastAPI + SQLAlchemy(async) + PostgreSQL

Reálná spustitelná kostra serveru. Watson ji při setupu python-fastapi projektu
**zkopíruje** do `server/`. Kanonický popis patternů:
`templates/stacks/_base/python-fastapi.md`.

## Co Watson upraví

- `src/config.py` — app title / env proměnné dle projektu (jinak generické)
- `contracts/db/migrations/` — projektová schémata (V1__init.sql je jen ukázka)

(Package se NEpřejmenovává — `src.shared` / `src.example` jsou generické.)

## Layout (zrcadlí projekt)

```
server/
  requirements.txt  requirements-dev.txt  pyproject.toml  run.sh  .env.example
  src/{main,database,config}.py
  src/shared/{errors,health}.py
  src/example/{router,service,repository,models}.py
  tests/{conftest,test_example}.py
contracts/db/migrations/V1__init.sql   # → projektové contracts/ (Chandler-owned)
```

## Co kostra ukazuje

- **shared/** — kanonická infra: `ApiError` + handler (shape `{code, details}`),
  health endpointy, **`ValidationResult`** (validation-only dry-run) a **`ApiListOf`/
  `ApiPageOf`/`ApiSliceOf`** generika (kolekční role, rules/backend.md §Kolekce).
  Kopíruje se identicky.
- **example/** — JEDEN vertical slice (router → service → repository → models)
  v kanonickém tvaru: FastAPI `Depends(get_db)`, SQLAlchemy Core `text()` SQL,
  pydantic v2 modely. Ukazuje **model role** `*Data`/`*View`/`*ExtData`
  (rules §API model role) a **write-flow** `?validate=` (rules §Write-flow):
  dry-run jen validuje (200 `ValidationResult`), commit re-validuje server-side
  a teprve pak zapíše (201 nebo 422 `{code, details.field_errors}`).

## Build & test

```bash
cd server
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # běží proti SQLite (bez Dockeru)
bash run.sh                 # dev: uvicorn (potřebuje DATABASE_URL na Postgres)
```

Produkce: Postgres přes `DATABASE_URL` (asyncpg) + Alembic SQL-only runner nad
`contracts/db/migrations/`. Testy běží portabilně proti SQLite (aiosqlite).
První feature: zkopíruj `example/` jako vzor, drž mapping rules ze `stack/server.md`.

## Docker dev-run (host-nezávislost)

Lokální smyčka **v kontejneru** (`docker_dev: true` v manifestu) — app s hot-reloadem
+ Postgres, bez instalace Pythonu/PG na hostu:

```bash
docker compose -f docker-compose.dev.yml up --build    # app :8000 + postgres :5432
```

Zdroják (`server/`) je mountovaný → editace = reload. `Dockerfile.dev` veze i dev
závislosti, takže testy jdou pustit v kontejneru: `docker compose -f docker-compose.dev.yml run --rm app pytest`.
