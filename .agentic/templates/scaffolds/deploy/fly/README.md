# Deploy platform — Fly.io (single-machine + embedded PostgreSQL)

Jedna Fly machina, PostgreSQL **zabalený v app image** a daty na připojeném
volume (`/data`). Levné, jednoduché, žádná managed DB. Vhodné pro malé / MVP
projekty. **Neškáluje horizontálně** (jedna machina vlastní pg). Pro škálování →
managed Postgres (Fly Postgres), mimo tento scaffold.

## Soubory

| Soubor | Role | Vlastník |
|---|---|---|
| `fly.toml` | machina, volume, env, port | **platform** (uprav `<app-name>`, region, zdroje) |
| `docker-entrypoint.sh` | embedded pg init + migrace + secret-gen + run | **platform** (poslední řádek = stack run cmd) |
| `Dockerfile` | build + runtime image | **platform** kostra; `STACK-SPECIFIC` sekce = stack |

## Setup

1. Zkopíruj `fly/` do rootu projektu (`fly.toml`, `Dockerfile`, `deploy/fly/docker-entrypoint.sh`).
2. Nahraď `<app-name>` (fly app, DB, volume) — nebo `APP_DB` env pro jiný název DB.
3. Uprav v `Dockerfile` sekce `STACK-SPECIFIC` (build/runtime) a v entrypointu run command, pokud nejsi na python-fastapi.
4. `fly volumes create <app-name>_data --region fra` · `fly secrets set APP_SECRET_KEY=...` (volitelné — entrypoint si vygeneruje a perzistuje).
5. `fly deploy`.

## Migrace

`AUTO_MIGRATE=true` (default v `fly.toml`) → entrypoint aplikuje `contracts/db/init/*.sql`
pak `contracts/db/migrations/V*.sql` v pořadí, idempotentně přes `schema_migrations`.

Vetted defaulty a rozhodovací kontext: `templates/stacks/_target/fly.md`.
