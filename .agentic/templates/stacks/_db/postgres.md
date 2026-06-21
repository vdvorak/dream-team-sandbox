---
cache_key: template-stack-db-postgres-v1.0
type: template
---

# Stack fragment — PostgreSQL (db)

Přidává se do `stack/server.md` k base fragmentu. Vetted defaulty.

---

```markdown
## Building blocks — PostgreSQL
| Nástroj | Role | Pozn. |
|---|---|---|
| PostgreSQL | relační DB | per-instance / managed |
| driver | DB konektor | Python: asyncpg/psycopg; Java: JDBC |
| migrace | schema migrations | Python: Alembic; Java: Flyway/Liquibase |

## Tech realizace — PostgreSQL
- Repository (`rules/backend`) je jediný přístup k DB.
- Migrace jsou kontrakt (`contracts/db/`, Chandler) — verzované, dopředu
  i zpět; destruktivní migrace = L3 (constitution).
- Typovaný přístup (`rules/backend`): query přes typed builder/ORM napojený
  na schéma, ne stringové SQL. Parametrizace vždy.
- Transakce explicitně na hranici service operace.
```

---

## Pozn.
Konkrétní driver/ORM volí Tony dle base fragmentu (Python vs Java). Tabulka
výše uvádí defaulty per ekosystém.
