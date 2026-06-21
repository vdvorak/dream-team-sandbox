# Deploy scaffoldy — podle platformy

Deploy je **platformní** koncern, ne stackový. Proto je tento strom keyovaný
podle **deploy platformy**, ne podle stacku (na rozdíl od `scaffolds/<stack>/`).

```
deploy/
  fly/        # Fly.io — single-machine + embedded PostgreSQL
  compose/    # lokální dev — app + postgres service
```

## Dělba: platforma vs stack

- **Platforma vlastní** deploy mechaniku: `fly.toml`, `docker-entrypoint.sh`
  (embedded pg, init, migrace, secret-gen), topologii `docker-compose.yml`,
  volume, health, restart.
- **Stack jen zapojí** dvě věci, označené v souborech komentářem
  `STACK-SPECIFIC`:
  1. **build/runtime** vrstvu Dockerfile (base image, deps, kopírování kódu)
  2. **run command** (poslední řádek entrypointu, např. `uvicorn ...`)

Díky tomu se stejná platforma použije napříč stacky — mění se jen ty dvě sekce.

## Použití

Setup-time artefakt (kopíruje Alfred/Watson při zavádění deploye), **ne**
sync-time. Per platforma viz její `README.md`. Vetted defaulty + kdy co použít:
`templates/stacks/_target/<platform>.md`.

## Placeholdery

- `<app-name>` — jméno aplikace (Fly app, DB, volume). Nahraď při setupu.
- Ostatní jde přes env defaulty (`${POSTGRES_USER:-app}` apod.).
