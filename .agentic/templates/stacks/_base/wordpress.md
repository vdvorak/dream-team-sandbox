---
cache_key: template-stack-wordpress-v1.0
type: template
---

# Stack fragment — WordPress (base)

Skládá se do `stack/cms.md`. Vetted defaulty; Tony per projekt upraví.
Pozor: WordPress je CMS platforma — řada universal vrstev (Router/Service/
Repository) se aplikuje volněji. Pro veřejný web platí SEO → SSR/SSG default
(přebíjí `rules/frontend` CSR), což řeší `constitution-overlays/wordpress-cms`.

---

```markdown
## Building blocks — WordPress
| Knihovna / nástroj | Role |
|---|---|
| WordPress core | CMS, obsah, admin |
| PHP | runtime |
| Composer | správa PHP závislostí (vetted pluginy/balíčky) |
| ACF | strukturovaná pole obsahu |
| WPGraphQL / REST API | datová vrstva pro headless klienta (volitelné) |
| PHPUnit | testy custom kódu |

## Tech realizace — WordPress
- Custom logika v pluginu/theme, oddělená od presentation; žádná business
  logika v šablonách.
- Pluginy a balíčky pouze vetted (constitution: bezpečná/udržovaná/popular) —
  WP ekosystém má vysoké security riziko, Heimdall hlídá.
- Headless varianta: WP jako obsahové API (WPGraphQL/REST) + samostatný
  frontend (viz `_base/solidjs`); topologii řeší overlay `wordpress-cms`.
- SEO: CMS-native rendering (WP PHP servíruje reálné HTML) — pro veřejný web
  žádané. NE runtime custom SSR; interaktivní island smí být CSR.
```

---

## Pozn.
Pokud je projekt **headless** (WP backend + JS frontend), Watson složí
`stack/cms.md` (tento fragment) + `stack/web.md` (`_base/solidjs`) a topologii
zapíše přes overlay `wordpress-cms`.
