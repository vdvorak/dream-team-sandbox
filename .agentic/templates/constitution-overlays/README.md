---
cache_key: template-overlays-readme-v1.0
type: template
---

# Constitution overlays — keyed fragmenty

„Společné, ale ne-universal" pravidla pro celou *třídu* projektů. Watson je
podle typu projektu vlije do sekcí `PROJECT-CONSTITUTION.md`.

## Mechanismus

Každý overlay obsahuje bloky klíčované markerem `→ <sekce base ústavy>`.
Watson vezme bullety z bloku a **přidá je do odpovídající sekce** projektové
ústavy (ne nahradí — doplní). Cílové sekce (z `templates/project-constitution.md`):

- `→ Nefunkční požadavky (NFR)`
- `→ Doménová security pravidla`
- `→ Delivery topologie`
- `→ Doménové hard rules`
- `→ Cílová skupina`

## Kombinovatelnost

Overlays jsou aditivní. Health SaaS web = `saas-web` + `health-sensitive-data`.
Watson aplikuje všechny relevantní; duplicitní bullety dedupuje.

## Hranice

Overlay NEopakuje `constitution.md` (universal). Obsahuje jen to, co je
společné dané třídě projektů a zároveň projekt-specifické vůči universal
vrstvě. Konkrétní hodnoty (SLA čísla, jména polí) doplní Tony/Vision.

## Dostupné overlays

| Soubor | Třída projektu |
|---|---|
| `saas-web.md` | multi-tenant SaaS webová aplikace |
| `local-desktop.md` | lokální desktop app, offline-first |
| `wordpress-cms.md` | WordPress web / headless CMS |
| `health-sensitive-data.md` | zdravotní / citlivá osobní data (GDPR čl. 9) |
