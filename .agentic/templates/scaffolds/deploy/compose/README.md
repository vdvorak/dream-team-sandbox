# Deploy platform — lokální docker-compose

Univerzální lokální běh: app + **samostatný** `postgres:16` service (na rozdíl od
Fly prod, kde je pg embedded). Bez názoru, použitelné pro každý server projekt.

## Soubory

| Soubor | Role |
|---|---|
| `docker-compose.yml` | topologie app + postgres + volume + health (**platform**) |
| `Dockerfile.dev` | dev image jen pro app, hot reload (`STACK-SPECIFIC`) |

## Setup

1. Zkopíruj do rootu: `docker-compose.yml` + `deploy/compose/Dockerfile.dev`.
2. Pokud nejsi na python-fastapi, uprav `Dockerfile.dev` (base + run cmd).
3. `docker compose up --build` → app na `http://localhost:8000`, pg na `:5432`.

DB jméno/uživatel přes `POSTGRES_*` env (default `app`). Migrace si řeš ručně /
runnerem; `contracts/db/init/` se aplikuje při prvním initu pg.
