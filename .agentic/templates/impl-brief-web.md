---
cache_key: template-impl-brief-web-v1.0
type: template
---

# Impl Brief Template — Web

`impl/web/<feature>.md` obsahuje pouze to, co **není zřejmé** z kontraktů,
specs, rules a stacku:

- seznam screens a jejich klasifikace (list / form / detail / wizard)
- feature-specific výjimky od obecných UI pravidel
- specifické interakce nebo chování

## Sem NEPATŘÍ

- obecné patterny (ty jsou v `rules/frontend.md`)
- stack binding (ten je v `stack/web.md`)
- business pravidla (ta jsou v příslušném `specs/<feature>.md`)
- opakování obsahu kontraktu

## Struktura

```markdown
# <Feature> — Web Impl Brief

## Screens

| Screen | Route | Klasifikace | Poznámka |
|---|---|---|---|
| ItemsPage | /items | list | filtry v URL query params |

## Interakce

(Pouze specifické pro tuto feature — ne obecné patterny)

## i18n klíče

(Klíče specifické pro tuto feature — hodnoty jsou v cs.json/en.json)
```
