---
cache_key: template-rules-frontend-v1.0
type: template
---

# Rules template — frontend (tech-agnostic)

Seed pro projektový `rules/frontend.md`. Watson ho kopíruje při setupu
(pokud má projekt UI klienta), Ted/Leonard ho pak vlastní a customizují.

**Hranice:** tvar frontend řešení (struktura, data flow, styling přístup),
NE universal hygiena (constitution) a NE konkrétní framework (React/Vue/
Solid → `stack/<target>.md`).

---

```markdown
# Frontend rules

Tech-agnostic tvar klientské vrstvy. Hygiena viz `.agentic/constitution.md`.
Konkrétní framework viz `stack/<target>.md`.

## Struktura komponent
- Prezentační komponenty (bez business logiky) vs kontejnerové (drží data).
- State žije co nejlokálněji; sdílený state explicitně ve store, ne
  prostřednictvím globálních proměnných.
- Jednosměrný data flow (data dolů, události nahoru).

## Rendering
- **App / interaktivní obsah → CSR** (client-side rendering) — default.
- **Veřejný / SEO obsah → SSG / prerender** (statické HTML při buildu) nebo
  **CMS-native rendering** (např. WordPress PHP). Ne CSR (špatné SEO).
- **Runtime custom SSR zakázán** — server renderující HTML při každém requestu
  zvyšuje útočnou plochu (render nad user inputem, hydration vulns, DoS). SSG
  dá stejné SEO bez běhového renderu. Výjimka = vědomé rozhodnutí v
  PROJECT-CONSTITUTION s opodstatněním.

SSG ≠ SSR: SSG renderuje jednou při buildu (statické soubory, bezpečné),
SSR renderuje za běhu (nebezpečné). Pro SEO chceme SSG/prerender.

## Styling — tři oddělené vrstvy
1. **Tokeny** (`design/manual/tokens.css`, vlastní Leonard) = jediný slovník
   hodnot (barvy, spacing, radius). V kódu NIKDY magic hodnota — vždy `var(--token)`.
2. **Chování + a11y** = **headless komponentová knihovna** (dialog, select…).
   Interaktivní komponenty se NEpíší ručně — focus trap, klávesnice, ARIA,
   scroll-lock bere z headless lib (konkrétní v `stack/`). Ručně psaná
   interaktivní a11y = bug-prone, zakázáno.
3. **Vizuál** = CSS Modules konzumující tokeny; markup zůstává čistý.

**Zakázáno:** utility-CSS frameworky typu Tailwind (zaplevelují markup,
obcházejí tokeny), hardcoded barvy/spacing (constitution §Pravidla pro design).
Mezi projekty se liší **jen tokeny** (design = vědomá proměnná); chování,
struktura a komponentové API zůstávají identické (uniformita).

## Data a validace
- API klient typovaný; vstupy/výstupy přes schémata (realizace v `stack/`).
- Klient smí mít UX hint validaci, ale autorita je vždy server (constitution).
- Žádné hardcoded user texty — i18n od začátku (constitution §Lokalizace).
```

---

## Pozn. pro Watson / Leonard

- „Žádný Tailwind" = čistota zdrojáku (utility-soup v markupu) + tokeny jako
  autorita. Alternativa NENÍ raw CSS sprawl — je to **tokeny + headless lib
  (chování) + CSS Modules (vizuál)**. Tu drahou část (interaktivní a11y) nikdy
  nepíšeš ručně, bereš z headless lib. Konkrétní lib určuje `stack/` (solidjs
  → Kobalte). Pokud projekt design manuál nemá, Leonard ho zakládá.
- Rendering rozlišuj podle obsahu, ne jeden default na vše: app/interaktivní
  = CSR, veřejný/SEO = SSG/prerender nebo CMS-native. Runtime SSR je out
  (bezpečnost). Tím CSR nikdy nekoliduje se SEO — každý obsah má svůj režim.
