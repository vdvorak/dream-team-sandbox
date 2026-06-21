---
type: feature-spec
feature: auth
scope: cross-project (knihovní)
---

# Auth — feature spec (stack-agnostic)

Kanonická autentizace pro projekty frameworku. Stack-agnostic **WHAT**; konkrétní impl per stack
v `impl/<stack>/`. Security-critical → **Heimdall audituje impl JEDNOU** v knihovně (ne per projekt).

## Varianta `base` (credentials)

### Operace
- **register** — email + heslo → účet. Heslo se hashuje (bcrypt; constitution F2 — žádná vlastní
  crypto). Email je unikátní.
- **login** — email + heslo → access token (JWT). Špatné creds → **jednotná** chyba (no user enumeration).
- **me** — z access tokenu vrátí aktuálního uživatele. Chybějící/neplatný token → 401.

### Token strategy (volba: `jwt | session`) — Watson se ptá, obě jsou v impl
- **jwt** (stateless) — access token = JWT, ≤ 30 min, podepsaný `APP_SECRET_KEY` (≥ 32 B). Claims
  `sub`/`exp`/`role`. Škálovatelné bez store; revokace = krátká životnost. (Refresh token = rozšíření.)
- **session** (stateful) — server vytvoří session (crypto-random token v `app_session`), pošle
  httpOnly cookie; `/me` = lookup v DB, `/logout` smaže session. Snadná revokace; potřebuje store.

### Pravidla (závazná)
- Heslo: min. délka ≥ 8; bcrypt cost ≥ 12; **plaintext NIKDY** nikam (log / response / db).
- Validace na serveru (write-flow): register podporuje `?validate` (unikátnost emailu, bez side-effektu).
- Chyby `{code, details}`; login fail = generický `invalid_credentials` (stejná odpověď pro neznámý
  email i špatné heslo — žádná enumeration).
- i18n: hlášky přes klíče, ne natvrdo.

### Acceptance
- [ ] register založí uživatele s bcrypt hashem; duplicitní email → 422 `{code, field_errors.email}`
- [ ] login správné creds → 200 + JWT; špatné → 401 `invalid_credentials` (identická odpověď pro
      neznámý email i špatné heslo)
- [ ] me s platným tokenem → uživatel; bez tokenu / expirovaný → 401
- [ ] heslo se NIKDY neobjeví v response ani v logu

## Varianty `oauth`, `mfa` (planned)
Opt-in moduly nad `base` — base auth + modul, ne paralelní implementace. Zavádějí se až bude potřeba.
