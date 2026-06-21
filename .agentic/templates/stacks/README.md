---
cache_key: template-stacks-readme-v1.1
type: template
---

# Stack templates — composable fragmenty

Watson skládá projektový `stack/<target>.md` z fragmentů místo generování
od nuly. Fragment = **deklarované knihovny** (vetted defaulty) + **tech
realizace** principů z `rules/` a `constitution.md`.

```
_base/    framework základ (python-fastapi, java-quarkus, solidjs, wordpress)
_db/      databázová vrstva (postgres, sqlite)
_target/  runtime/packaging + deploy platforma
            electron           — Electron desktop
            fly                — Fly.io (single-machine + embedded pg)
            docker-compose     — VPS / self-hosted Docker Compose
            wordpress-hosting  — shared / managed WordPress hosting (žádný Docker)
```

## Kompozice (dělá Watson)

`stack/<target>.md` = `_base/<framework>` + `_db/<db>` (pokud server s DB)
`+ _target/<deploy>` (vždy, pokud projekt má deploy; jen library/no-deploy bez fragmentu)
`+ _target/electron` (navíc pro desktop), + skeleton tail (`§Scaffold`
prázdná, `§Extraction Candidates` prázdná tabulka — viz Watson duties).

| Projekt (vzor) | Kompozice → soubor |
|---|---|
| python-fastapi-postgres + Fly.io (Parker2) | `_base/python-fastapi` + `_db/postgres` + `_target/fly` → `stack/server.md` |
| python-fastapi-postgres + VPS Docker (murio) | `_base/python-fastapi` + `_db/postgres` + `_target/docker-compose` → `stack/server.md` |
| python-fastapi-sqlite + Fly.io | `_base/python-fastapi` + `_db/sqlite` + `_target/fly` → `stack/server.md` |
| java-quarkus-postgres + Fly.io | `_base/java-quarkus` + `_target/fly` → `stack/server.md` |
| solidjs web (žádný vlastní deploy) | `_base/solidjs` → `stack/web.md` |
| solidjs electron (Vdoklad desktop) | `_base/solidjs` + `_target/electron` (+ `_db/sqlite`) → `stack/desktop.md` |
| wordpress + shared hosting (pneukarnik) | `_base/wordpress` + `_target/wordpress-hosting` → `stack/cms.md` |

**Poznámka — SolidJS web:** frontend target typicky nemá vlastní deploy fragment —
deploy obstarává buď server (SPA servíruje server) nebo hosting (Netlify/Vercel),
a to je zdokumentováno v server `_target/` nebo v PROJECT-CONSTITUTION.

## Hranice

Fragment NESE **nástroj** (framework, ORM, knihovna, deploy mechanismus).
Princip (tvar) je v `rules/`, hygiena v `constitution.md` — fragment je
NEopakuje, jen realizuje konkrétním nástrojem. Vše jsou **vetted defaulty**
(splňují constitution: bezpečná/udržovaná/popular) — Tony per projekt upraví.
