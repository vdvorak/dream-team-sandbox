---
contract: p5-interaction-typology
feature: p5-human-interaction-registry
owner: ted-architect
---

# Kontrakt — typologie human-interakcí

Definuje **schéma** každé interakce v `pipeline/interactions.yaml` a **typologii kindů**
(kind → UI control → typované I/O). Cíl: app vyrenderuje interakci jen z jejího `kind` +
`produces`, bez per-gate kódu. Implementuje Bob (interactions.yaml + check C10).

## Schéma interakce (každá položka v `interactions:`)

| pole | povinné | význam |
|---|---|---|
| `kind` | ano | typ interakce ∈ typologie níže (řídí UI control) |
| `prompt` | ano | text k uživateli (česky) |
| `level` | ano | L0–L3 (schvalovací úroveň, viz constitution) |
| `blocking` | ano | `true` = drží běh (halt_gate) · `false` = awaiting_human (nezdržuje) |
| `produces` | ano | **typovaný výstup**: `{ artifact: <typ z artifacts.yaml> }` NEBO `{ outcome: <O z vocabulary> }` |
| `options` | jen `choice`/`approval` | seznam `{ value, label }` (povolené odpovědi) |
| `delegate_to` | jen `delegate-or-provide` | role agenta, na kterou lze delegovat (alternativa k uploadu) |

## Typologie kindů (kind → UI control → I/O)

| kind | UI control (app) | produces | pozn. |
|---|---|---|---|
| `choice` | radio / select z `options` | `outcome` (zvolená value) | větvení routingu |
| `approval` | schválit / zamítnout | `outcome` (APPROVED/REJECTED) | typicky L3 blocking |
| `ack` | tlačítko „potvrdit" | `outcome: ACK` | informativní, non-blocking |
| `upload` | file upload widget | `artifact: <typ>` | člověk dodá obsah |
| `text` | text input | `artifact: <typ>` (nebo flag) | volná odpověď |
| `delegate-or-provide` | **dvojvolba**: `[upload <typ>]` XOR `[spustit <delegate_to>]` | `artifact: <typ>` (oba konce stejný typ) | viz níže |

## `delegate-or-provide` (vlajkový případ)

Člověk se rozhodne: **dodá artefakt sám** (upload), NEBO **deleguje na agenta**. **Oba konce
produkují stejný typovaný artefakt** → flow pokračuje identicky, jen zdroj se liší.

**Reuse-decision (constitution reuse policy): reuse-existing.** Routing „kdo dodá" už existuje —
projektová politika `design_source` (`author|intake|derive`) + role `design-intake`. P5 ho
**nenahrazuje**, jen formalizuje jako interakční `kind`. Vlajková interakce `design-source`
(dnes `kind: upload`) → překlopit na `kind: delegate-or-provide` s `delegate_to: ux-design` (Denisa)
a `produces: { artifact: mockup }`. Žádný nový routing — engine dál routuje přes `design_source` flag.

## Co implementuje Bob

1. `pipeline/interactions.yaml` — rozšířit na typovaný registr dle schématu výše; každá interakce
   `kind` + `produces`; `design-source` → `delegate-or-provide`. Hlavička = schéma (kind → UI → I/O).
2. `vocabulary.yaml` / `check.py` C10 — povolit `kind: delegate-or-provide`; ověřit, že každá interakce
   má `produces` s platným `artifact` typem (∈ artifacts.yaml) nebo `outcome` (∈ vocabulary).
3. Unit test (`scripts/pipeline/tests/`) — registr je validní dle schématu (pokud se sáhne na check.py).

## Error-codes

N/A — registr je statická data + validace, ne API s runtime chybami. Validační nálezy = C10 (check.sh).
