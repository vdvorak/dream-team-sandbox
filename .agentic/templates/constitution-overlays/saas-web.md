---
cache_key: template-overlay-saas-web-v1.0
type: template
---

# Overlay — multi-tenant SaaS web

Aplikuj pro webové aplikace se sdílenou instancí a více tenanty. Watson
vlije bullety do odpovídajících sekcí `PROJECT-CONSTITUTION.md`.

---

```markdown
→ Nefunkční požadavky (NFR)
- Multi-tenancy: izolace dat mezi tenanty na úrovni dat i přístupu
- Auth: JWT / server-side session (rozhodne Tony); RBAC per tenant
- Dostupnost: SaaS uptime SLA (doplň cíl, např. 99.9 %)
- Compliance: GDPR (zpracování osobních údajů uživatelů)

→ Doménová security pravidla
- Tenant izolace je bezpečnostní hranice — vynucená v repository/query vrstvě
- GDPR: právo na výmaz + export dat subjektu (implementované, ne ad-hoc)
- Audit log přístupů k datům napříč tenanty

→ Delivery topologie
- Sdílená instance, multi-tenant (NE per-instance deployment)
- Horizontální škálování; stateless app vrstva, stav v DB/cache

→ Doménové hard rules
- Žádný dotaz nad tenant daty bez `tenant_id` ve filtru — cross-tenant
  přístup = BLOCKER
- Tenant kontext se odvozuje z autentizace, nikdy z user-supplied parametru
```

---

## Pozn.
Konkrétní SLA čísla, auth mechanismus a cache vrstvu doplní Tony. Pro
zdravotní SaaS kombinuj s `health-sensitive-data`.
