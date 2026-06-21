---
cache_key: template-stack-target-fly-v1.0
type: template
---

# Deploy target — Fly.io (single-machine + embedded Postgres)

Vetted default pro nasazení server projektů. Alfred vlastní deploy kód; tento
fragment dává posvěcený pattern, ať se Dockerfile/fly.toml **neklonují od
sourozence** (zdroj driftu). Scaffold soubory: `scaffolds/deploy/fly/`.

---

```markdown
## Deploy — Fly.io (single-machine + embedded Postgres)

| Building block | Volba |
|---|---|
| Platforma | Fly.io, jedna machina (`min_machines_running = 1`) |
| Databáze | PostgreSQL **embedded v app image**, data na volume `/data` |
| Migrace | `AUTO_MIGRATE=true` → entrypoint, idempotentně přes `schema_migrations` |
| Secret | `APP_SECRET_KEY` — Fly secret, nebo auto-gen + persist na volume |
| Statika | SPA servíruje server přes `APP_STATIC_DIR` (žádný extra CDN) |
| Port | `internal_port = 8000` |

**Kdy použít:** malé / MVP / cost-sensitive projekty. Jedna machina, jeden
volume, žádná managed DB cena.

**Kdy NE:** potřeba horizontálního škálování nebo HA databáze → managed Postgres
(Fly Postgres / externí), což tento pattern nepokrývá.

**Co Alfred ladí:** `<app-name>`, `primary_region`, `[[vm]]` zdroje, `[env]`.
Sekce `STACK-SPECIFIC` v Dockerfile/entrypointu dle stacku (build + run command).
```
