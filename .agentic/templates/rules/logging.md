---
cache_key: template-rules-logging-v1.0
type: template
---

# Rules template — logging (tech-agnostic)

Seed pro projektový `rules/logging.md`. Watson kopíruje při setupu, Ted
vlastní. Konkrétní logging knihovna → `stack/<target>.md`.

**Hranice:** tvar logování (struktura, úrovně, co se neloguje). Citlivá
**doménová** pole (co je PII pro tenhle projekt) patří do PROJECT-
CONSTITUTION §Doménová security, ne sem.

---

```markdown
# Logging rules

Tech-agnostic. Konkrétní knihovna viz `stack/<target>.md`.

## Forma
Strukturované logy (key-value / JSON), ne volný text — strojově
dotazovatelné. Correlation/request ID napříč vrstvami pro trasování.

## Úrovně
- **ERROR** — akční selhání (vyžaduje pozornost)
- **WARN** — degradace, recoverable anomálie
- **INFO** — business události (default produkce)
- **DEBUG** — vývoj, nikdy default v produkci

## Co se NIKDY neloguje
secrets, tokeny, hesla, autorizační hlavičky, plné PII, obsah citlivých
polí. (Doménově citlivá pole → PROJECT-CONSTITUTION §Doménová security.)

## Chyby
Logovat s typem + kontextem, nikdy nepolykat (viz constitution: žádné
swallowed exceptions). Žádné emoji v lozích (constitution).

## Výkon
Žádné logování v hot-path, které mění chování nebo výkon (pozor Optimus).
```

---

## Pozn. pro Watson / Ted

- Seznam „co se neloguje" je univerzální základ; doménová citlivá pole
  doplní Tony/Heimdall do PROJECT-CONSTITUTION (ne sem — tady je tech-agnostic
  vzor, tam projekt-specifický obsah).
