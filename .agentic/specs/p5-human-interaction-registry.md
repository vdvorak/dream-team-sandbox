---
feature: p5-human-interaction-registry
class: feature
spec_language: cs
owner: vision-po
---

# P5 — Human-interaction registry

## Cíl (max 3 věty)

Typovat všechny human-interaction body flow tak, aby do běhu šlo **vstoupit přes deterministicky
definovaný interface** (ne terminál) a budoucí app je uměla vyrenderovat bez per-gate kódu. Každá
interakce = jasný vstup → **typovaný výstup do flow** (minimální diverzita).

## Scope

- Rozšířit `pipeline/interactions.yaml` ze 3 ad-hoc interakcí na **úplný typovaný registr**.
- **Typologie kindů**: `choice` · `approval` · `ack` · `upload` · `text` · **`delegate-or-provide`**.
- Každá interakce: `kind` + `prompt` + `level` (L0–L3) + `blocking` + **`produces`** (typovaný
  `artifact:<typ>` z `artifacts.yaml`, nebo `outcome:<O>` z `vocabulary.yaml`).
- **`delegate-or-provide`** = vlajkový případ: člověk buď **dodá artefakt** (upload), NEBO **deleguje
  na agenta**. Konkrétně rozhodnutí o designu: *upload vlastního HTML návrhu* XOR *spustit Denisu*.
- **Schéma typologie** (kind → UI control → I/O) zdokumentované v hlavičce `interactions.yaml`, aby
  app renderovala per kind bez custom kódu.

## Acceptance criteria

1. `interactions.yaml` je typovaný registr: každá interakce má `kind` ∈ povolené množiny + `produces`.
2. Existuje `delegate-or-provide` interakce pokrývající „upload vlastního designu XOR spustit agenta".
3. `kind` množina ve `vocabulary.yaml` (nebo check) rozšířena o `delegate-or-provide`; `check.sh` C10 zelené.
4. `produces` každé interakce je napojené na `artifacts.yaml` typ (artifact) nebo `vocabulary` outcome.
5. Schéma typologie (kind → UI control → I/O) zdokumentované v `interactions.yaml`.
6. Engine nerozbit: `selftest.sh` 57/57; `check.sh` C1–C15 OK.

## Edge cases & otevřené otázky

- `delegate-or-provide`: jak engine routuje „delegoval" vs „dodal"? → **oba konce produkují stejný
  typovaný artefakt** (`mockup`); volbu *kdo dodá* řeší existující `design_source` flag + `design-intake`
  role (nevymýšlet nový routing — viz Decided).
- Blocking vs non-blocking je per interakce (`blocking:`), ne per kind — zachovat.

## Decided (rozhodnutí výše ve flow — NEopakovat níže)

- **`has_ui: false`** (registr/schéma, ne obrazovka), **`touches_db: false`** — žádná DB, žádný klient.
- `delegate-or-provide` má **oporu v existujícím** `design_source` flagu + `design-intake` roli;
  P5 jen formalizuje jeho interakční typ, nezavádí nový routing.
- **NEstavíme app UI** — jen deterministickou definici (registr + schéma), kterou app konzumuje.
- Live-session escape hatch (vstup do běžící agent session) = **mimo scope** (pozdějc, porušuje determinismus).
