---
cache_key: template-rules-error-responses-v1.0
type: template
---

# Rules template — error responses (tech-agnostic)

Seed pro projektový `rules/error-responses.md`. Watson kopíruje při setupu
(pokud má projekt API), Ted vlastní (registr kódů žije v `contracts/`).

**Hranice:** error shape `{code, details}` je dané `constitution.md` — zde
se NEopakuje, jen **rozšiřuje** o registr kódů a HTTP mapping.

---

```markdown
# Error responses rules

Rozšíření universal error pravidla z `.agentic/constitution.md`
(shape `{code, details}`, žádný str(exc)/stack trace v response).

## Registr kódů
Zdroj pravdy = `contracts/error-codes.md` (vlastní Ted). Každý kód:
- stabilní identifier `UPPERCASE_WITH_UNDERSCORES`
- HTTP status
- stručný popis (pro vývojáře, ne pro koncového uživatele)

Nové kódy se přidávají do registru, nikdy ad-hoc v kódu.

## HTTP status mapping
Kód nese doménovou sémantiku, status je transport:

| Třída chyby | HTTP |
|---|---|
| validace vstupu | 400 / 422 |
| neautentizováno | 401 |
| nedostatečná práva | 403 |
| nenalezeno | 404 |
| konflikt stavu | 409 |
| interní selhání | 500 |

## Klient
Klient nikdy nezobrazuje raw `code` uživateli — překládá přes i18n
(constitution §Lokalizace: server vrací kódy, klient překládá). `details`
slouží pro strojové zpracování / formuláře, ne jako hotová hláška.
```

---

## Pozn. pro Watson / Ted

- Tabulka mapování je default — Ted ji per projekt rozšíří (např. 429 rate
  limit, 402 payment). Registr samotných kódů je kontrakt (`contracts/`),
  ne rules — proto je runtime registr oddělen od tohoto patternu.
