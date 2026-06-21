---
cache_key: template-overlay-wordpress-cms-v1.0
type: template
---

# Overlay — WordPress / headless CMS

Aplikuj pro WordPress weby a headless CMS topologie. Watson vlije bullety
do sekcí `PROJECT-CONSTITUTION.md`.

---

```markdown
→ Nefunkční požadavky (NFR)
- SEO jako first-class požadavek (reálné HTML pro roboty)
- Výkon first-paint pro veřejný obsah (Core Web Vitals)
- Compliance: GDPR (cookies, formuláře, návštěvnická data)

→ Delivery topologie
- WP hosting (managed / VPS); CDN pro statická aktiva
- Headless varianta: WP backend (obsah + API) + samostatný JS frontend
  (viz stack `_base/solidjs`)

→ Doménové hard rules
- SEO rendering: veřejné stránky **CMS-native (WP PHP) nebo SSG/prerender**,
  NE CSR. **Runtime custom SSR zakázán** (bezpečnost — viz `rules/frontend`).
  Booking/interaktivní island smí být CSR.
- Strukturovaná data (schema.org), canonical URLs, korektní meta
- WP core + pluginy průběžně aktualizované (CVE riziko)

→ Doménová security pravidla
- Pluginy a balíčky jen vetted (bezpečné/udržované/popular) — WP ekosystém
  má vysoké security riziko (Heimdall hlídá)
- Admin přístup s 2FA; žádné default credentials
```

---

## Pozn.
Headless: Watson složí `stack/cms.md` (`_base/wordpress`) + `stack/web.md`
(`_base/solidjs`) a topologii zapíše sem. Klasický WP web = jen `cms.md`.
