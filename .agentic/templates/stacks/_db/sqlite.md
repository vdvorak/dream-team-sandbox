---
cache_key: template-stack-db-sqlite-v1.0
type: template
---

# Stack fragment — SQLite (db)

Přidává se do `stack/server.md` nebo `stack/desktop.md`. Vetted defaulty.
Typicky lokální / offline-first (desktop app, single-instance backend).

---

```markdown
## Building blocks — SQLite
| Nástroj | Role | Pozn. |
|---|---|---|
| SQLite | embedded relační DB | single-file, žádný server |
| driver | DB konektor | Python: sqlite3/aiosqlite; Node: better-sqlite3 |
| migrace | schema migrations | verzované, dopředu i zpět |

## Tech realizace — SQLite
- Repository (`rules/backend`) jako jediný přístup k DB.
- Migrace jsou kontrakt (`contracts/db/`, Chandler).
- Pozor na konkurenci: SQLite má omezený paralelní zápis (WAL mód, serializace
  zápisů) — návrh počítá s jediným writer kontextem.
- Offline-first: lokální data ownership (návaznost overlay `local-desktop`).
```

---

## Pozn.
Pro desktop (Electron) běží SQLite v main procesu; renderer k ní přistupuje
přes IPC (viz `_target/electron`), ne přímo.
