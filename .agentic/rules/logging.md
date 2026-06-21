---
cache_key: rules-logging-v1.0
type: normative-rules
last_updated: 2026-06-10
---

# Logging Rules

Co smí a nesmí být v logu. Tech-agnostic — konkrétní knihovna viz `stack/<target>.md`.
Doménová citlivá pole (PII projektu) → `PROJECT-CONSTITUTION §Doménová security`.
Projektové odchylky a specifické forbidden keys → `rules/` v kořeni projektu.

## Forma

Strukturované logy (key-value / JSON), ne volný text — strojově dotazovatelné.
Correlation/request ID napříč vrstvami pro trasování.

## Úrovně

- **ERROR** — akční selhání vyžadující pozornost
- **WARN** — degradace, recoverable anomálie
- **INFO** — business události (default produkce)
- **DEBUG** — vývoj; nikdy default v produkci

## Forbidden v logu (jakákoli úroveň)

V logu, v persistovaných job zprávách, v API response ani v observability platformě
se nikdy nesmí objevit:

**Secrets:**
- API klíče (OpenAI, Google, Stripe, …)
- Šifrovací klíče
- Hesla (plaintext ani hash)
- OAuth access / refresh tokeny
- Session cookie hodnoty
- Invitation / verification tokeny (plain)

**Auth materiál:**
- Encrypted bloby citlivých konfigurací
- CSRF tokeny, session IDs

**Citlivý obsah:**
- Plné PII zákazníků (jméno, e-mail, adresa, identifikační čísla)
- Obsah citlivých business entit (co je citlivé → projekt definuje v PROJECT-CONSTITUTION)

**LLM materiál (pokud projekt volá AI):**
- Full prompt strings
- Full raw LLM responses
- Detailní error body ze SDK (mohou obsahovat prompt fragmenty)

**Stack traces v HTTP responses** — plný trace je OK v server-side logu / Sentry;
nikdy v API response.

## Allowed v logu

- UUID identifikátory entit (entity ID, job ID, …)
- Stabilní error kódy (z `contracts/error-codes.md`)
- Telemetrie bez citlivého obsahu (počty tokenů, cost, model, duration ms, HTTP status)
- Event types (created, updated, deleted, …)
- Exception class name samotná (bez detail textu, pokud text může obsahovat citlivá data)

## Exception handling

- Žádný `str(exc)` nebo `repr(exc)` v API response — viz `rules/error-responses.md`
- `logger.exception(...)` zachytí plný trace server-side
- Persistence do job zpráv: projít redakcí citlivých fragmentů;
  exception class name samotná je OK, detail text ne
- Observability platform (Sentry, Datadog, …):
  - `send_default_pii=False` nebo ekvivalent
  - `max_request_body_size=never` nebo ekvivalent (request body může nést upload)
  - `before_send` hook redactující frame-locals a autorizační hlavičky

## Výkon

Žádné logování v hot-path, které mění chování nebo výkon (sledovat Optimus).
