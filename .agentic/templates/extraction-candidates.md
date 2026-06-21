---
type: reuse-tracking
last_updated: <YYYY-MM-DD>
---

# Extraction Candidates

Živý registr patternů viděných napříč vlnami, které **ještě nejsou zesdílené** jako
komponenta/abstrakce. Operační páka pravidla reuse (`constitution §Reuse policy §Operační
mechanismus`): bez tracking se 2. výskyt nepozná a každá stránka/feature si plodí vlastní
divy, spany a styly.

**Orchestrátor: ČTI tuto tabulku PŘED každou feature a AKTUALIZUJ ji PO každé.**
Platí pro všechny targety (web/mobile/desktop frontend i backend), ne jen web.

> **Tip (advisory):** `scripts/extraction-scan.sh` automaticky najde bloky opakované ≥3×
> (deterministicky, doslovný copy-paste) a navrhne je jako kandidáty — sníží závislost na
> ručním všimnutí. Neblokuje; jen reportuje, ty rozhodneš o extrakci.

| Pattern | Výskytů | Soubory | Stav / trigger |
|---|---|---|---|
| _(příklad)_ `label / value` info řádek | 1 | `pages/profile/…` | sledovat — 2. výskyt → `extract-shared` jako `DataField` |
| _(příklad)_ opakovaný loading/empty/error blok | 1 | `pages/example/…` | sledovat — 2. výskyt → `ListState` |

## Pravidla práce s registrem

1. **Nový pattern (1. výskyt)** → přidej řádek (`Výskytů: 1`, soubor, navržená budoucí komponenta).
2. **2. výskyt** → `Výskytů: 2`; orchestrátor **nesmí** pokračovat v codegenu bez:
   - `extract-shared` (extrakce = první krok vlny), nebo
   - BLOCKER se zdůvodněním (doménová specificita / nestabilní kontrakt / jednorázovost).
3. **Po `extract-shared`**:
   - popiš komponentu v katalogu (`stack/<target>`) + zdůvodnění,
   - **back-fill**: zrefaktoruj **všechny** dosavadní výskyty (i historické) na novou komponentu,
   - zruš řádek zde (přešel do katalogu = autority).

> Komponenta v katalogu existuje → raw inline varianta téhož = **drift** (Vitek conformance gate).
