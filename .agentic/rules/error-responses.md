---
cache_key: rules-error-responses-v1.0
type: normative-rules
last_updated: 2026-06-10
---

# API Error Responses

Globální pravidla pro tvar chybových odpovědí. Platí pro **všechny API endpointy**.
Projektové odchylky a project-specific allowlist → `rules/` v kořeni projektu.

## Hranice

**Sem patří:** shape `{code, details}`, allowlist klíčů, zakázané obsahy.
**Sem nepatří:** konkrétní error kódy (viz `contracts/error-codes.md`),
feature-specific HTTP status mapping (viz specs).

## Shape

```json
{
  "code": "<stable.dot.code>",
  "details": { /* allowlist keys only */ }
}
```

`code` je stabilní identifikátor; klient na něj mapuje překlad i UX.
Změna `code` je breaking change → vyžaduje migrační plán.

## Registr kódů

Zdroj pravdy = `contracts/error-codes.md` (vlastní Ted). Každý kód:
- stabilní identifier
- HTTP status
- stručný popis (pro vývojáře, ne pro koncového uživatele)

Nové kódy se přidávají do registru, nikdy ad-hoc v kódu.

## HTTP status mapping (default)

| Třída chyby | HTTP |
|---|---|
| validace vstupu | 400 / 422 |
| neautentizováno | 401 |
| nedostatečná práva | 403 |
| nenalezeno | 404 |
| konflikt stavu / verze | 409 |
| rate limit | 429 |
| interní selhání | 500 |

Ted rozšiřuje tabulku dle projektu (`rules/error-responses.md` v kořeni).

## Allowlist `details` keys

Pouze klíče z allowlistu smějí být vráceny klientovi. Projekt definuje svůj
specifický allowlist v `rules/error-responses.md` v kořeni. Výchozí obecné klíče:

| Key | Hodnota | Použití |
|---|---|---|
| `field` | string | název validovaného pole při 400/422 |
| `id` | string / int | identifikátor entity |
| `retry_after` | int (sekundy) | rate-limit / lockout / retry hint |
| `max` | int / number | limit (size, count) |
| `min` | int | minimum |
| `running` | int | aktuálně běžící počet (concurrency cap) |

Jiné klíče bez zápisu do allowlistu = porušení tohoto pravidla.

## Zakázané obsahy v response

NIKDY do API response:

- `str(exc)`, `str(e)`, `repr(exc)` — exception text může obsahovat prompt
  fragmenty, library internals, file paths
- Stack trace (jakákoli forma)
- Exception class name v API response (server-side log je OK)
- Obsah citlivých business entit (texty, soubory, PII)
- OAuth tokeny, settings hodnoty markované jako sensitive
- Detailní hlášky třetích stran (SDK error body)
- Raw obsah audit_logs nebo job_messages před filtrací

Pokud chyba pochází ze třetí strany, v API response zůstane jen `code` a allowlist
`details`. Plný `logger.exception` se zapíše server-side.

## Klient

Klient nikdy nezobrazuje raw `code` uživateli — překládá přes i18n.
`details` slouží pro strojové zpracování / formuláře, ne jako hotová hláška.
