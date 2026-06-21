---
cache_key: template-stack-target-docker-compose-v1.0
type: template
---

# Deploy target — Docker Compose (VPS / self-hosted)

Vetted default pro nasazení na vlastní VPS nebo bare-metal server. Alfred vlastní
deploy kód; tento fragment definuje posvěcený pattern, ať se Dockerfile/compose
**neklonují od sourozence** (zdroj driftu). Scaffold soubory: `scaffolds/deploy/compose/`.

---

```markdown
## Deploy — Docker Compose (VPS / self-hosted)

| Building block | Volba |
|---|---|
| Platforma | Vlastní VPS / bare-metal, Docker Compose |
| Databáze | PostgreSQL jako **samostatný service** (`postgres:16`) ve stejném compose stacku |
| Migrace | dle stacku — Flyway (Java), Alembic (Python), nebo vlastní SQL runner při startu |
| Secrets | env soubor (`.env`, mimo repo) nebo systemd credentials / Vault |
| Statika | SPA servíruje server nebo Nginx reverse-proxy před app kontejnerem |
| Port | `8000` (app), `5432` (pg — jen interně, nepublikovat ven) |

**Kdy použít:** projekty s vlastním serverem, nutností plné kontroly prostředí,
nebo kde cloud-managed DB není žádoucí z cenových / datových důvodů.

**Kdy NE:** chceš managed infra bez ops zátěže → Fly.io (`_target/fly`).

**Co Alfred ladí:** image name, port mapping, `POSTGRES_*` env, volume names,
restart policy. Sekce `STACK-SPECIFIC` v Dockerfile dle stacku (build + run command).
```
