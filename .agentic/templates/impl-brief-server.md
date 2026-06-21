---
cache_key: template-impl-brief-server-v1.0
type: template
---

# Impl Brief Template — Server

`impl/server/<feature>.md` obsahuje pouze to, co **není zřejmé** z kontraktů,
specs, rules a stacku:

- seznam endpointů nebo operací a jejich klasifikace
- feature-specific výjimky od obecných pravidel
- feature-specific data flow nebo algoritmické kroky
- pořadí operací pokud není zřejmé ze spec

## Sem NEPATŘÍ

- obecné patterny (ty jsou v `rules/backend.md`)
- stack binding (ten je v `stack/server.md`)
- business pravidla (ta jsou v příslušném `specs/<feature>.md`)
- opakování obsahu kontraktu

## Struktura

```markdown
# <Feature> — Server Impl Brief

## Operace a klasifikace

| Operace | HTTP | Klasifikace | Poznámka |
|---|---|---|---|
| listItems | GET /items | read, paginated | — |

## Datový flow

(Pouze pokud není zřejmý ze spec — neopisovat spec)

## Feature-specific výjimky

(Odchylky od obecných pravidel v rules/ nebo stack/)
```
