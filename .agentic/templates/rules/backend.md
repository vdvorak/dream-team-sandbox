---
cache_key: template-rules-backend-v1.0
type: template
---

# Rules template — backend (tech-agnostic)

Seed pro projektový `rules/backend.md`. Watson ho kopíruje při setupu
(pokud má projekt server-side), Ted ho pak vlastní a customizuje.

**Hranice (kritické):** tento soubor popisuje **tvar** backend řešení
(vrstvy, hranice, patterny) — NIKDY neopakuje universal hygienu z
`constitution.md §Standardy kódu` (typy, swallowed exceptions, secrets...).
Konkrétní **nástroje** (framework, ORM, query builder) NEpatří sem — ty jsou
v `stack/<target>.md`. Sem patří princip, tam realizace.

---

```markdown
# Backend rules

Tech-agnostic tvar serverové vrstvy. Hygiena viz `.agentic/constitution.md
§Standardy kódu`. Konkrétní knihovny viz `stack/<target>.md`.

## Vrstvy a hranice
Router/Controller → Service → Repository. Závislost teče jen dolů.

- **Router/Controller** — pouze transport (HTTP routing, deserializace,
  delegace validace). Žádná business logika.
- **Service** — business logika. Testovatelná bez HTTP a bez DB
  (viz constitution §Business logika testovatelná bez infrastruktury).
- **Repository** — jediný přístup k DB. Zbytek kódu nevolá DB přímo.
  (Projekt bez DB → tato vrstva N/A.)

## Typovaný přístup k DB
SQL se píše tak, aby překladač / type-checker zachytil změnu schématu a
nekompatibilitu **při buildu**, ne až za běhu (princip za jOOQ / typed ORM —
konkrétní nástroj v `stack/`). Žádné stringově skládané SQL — parametrizace
vždy (viz constitution: strict server validation, bezpečné dotazy).

## API konzistence
Veřejné API vrstvy/modulu definováno přes interface/kontrakt, aby
implementace byly zaměnitelné a konzistentní (realizace: interface v
TS/Java, Protocol/ABC v Pythonu — viz `stack/`).

## Chyby
Error shape `{code, details}` je dané constitution. Mapování interních chyb
na kódy + HTTP statusy → `rules/error-responses.md`. Žádné placeholder
implementace, žádné spolknuté výjimky (constitution).
```

---

## Pozn. pro Watson / Ted

- Watson kopíruje fenced obsah do `rules/backend.md`. Pokud projekt nemá DB,
  Ted sekce Repository / Typovaný DB přístup označí N/A (nemaže — dokumentuje
  rozhodnutí).
- Repository pattern je default „kde dává smysl" — ne dogma pro triviální
  CRUD bez doménové logiky. Ted rozhoduje per projekt.
