# Web component catalog (solidjs)

Shared building blocks, které kostra veze. **Než vytvoříš komponentu, koukni sem; existuje-li
odpovídající, MUSÍ se použít** (constitution §Reuse policy — raw varianta = BLOCKER). Katalog
**roste** přes Extraction Candidates (`templates/extraction-candidates.md`): 2. výskyt patternu
→ `extract-shared` + **back-fill všech výskytů**.

| Block | Kdy použít | Kde |
|---|---|---|
| `Button` | obecné tlačítko | `components/ui/Button.tsx` |
| `Dialog` | modal (wrapper nad Kobalte) | `components/ui/Dialog.tsx` |
| `TextField` | form field navázané na `createFormStore` | `components/ui/TextField.tsx` |
| `createFormStore` | každý write formulář | `components/createFormStore.ts` |
| `AppShell` | layout chráněných stránek | `components/layout/AppShell.tsx` |
| `BackendStatusBanner` | indikátor nedostupnosti backendu | `components/BackendStatusBanner.tsx` |

Tohle je **startovní** katalog — projekt ho rozšiřuje, jak extrahuje opakované patterny.

## Conformance (mechanický back-align)

`catalog-conformance.yaml` deklaruje **anti-pattern signatury** (raw forma, kterou komponenta
nahrazuje). `scripts/catalog-conformance.sh` je deterministicky grepne přes `src/` a flagne
nezmigrovaná místa → **Vitek gate** (BLOCKER). Tím se komponenta prosadí *všude*, ne jen v novém kódu.

**Při extrakci nové komponenty** přidej:
1. řádek do tabulky výše,
2. signaturu do `catalog-conformance.yaml` (raw forma + `allow` výjimky),
3. back-fill: zrefaktoruj všechny dosavadní výskyty.
