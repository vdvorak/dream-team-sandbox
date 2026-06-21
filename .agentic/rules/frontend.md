---
cache_key: rules-frontend-v1.0
type: normative-rules
last_updated: 2026-06-10
---

# Frontend Patterns

Tvar klientské vrstvy, tech-agnostic. Platí pro **všechny UI targety**.
Konkrétní framework/knihovny → `stack/<target>.md`.
Projektové odchylky → `rules/` v kořeni projektu.

Universal hygiena → `constitution.md §Standardy kódu`.
Lokalizace principy → `constitution.md §Lokalizace` (zde jen frontend-specifický detail).
Server jako validační autorita → `constitution.md §Strict server validation`.

## Hranice souboru

**Sem patří:** tech-agnostic UI patterny, odpovědnosti komponent, data flow,
rendering strategie, styling architektura.

**Sem nepatří:** specifický framework (React/Vue/Solid/…), CSS Modules API,
konkrétní názvy komponent nebo souborů.

## Komponenty a odpovědnosti

### Page komponenta
- Jeden routed endpoint = jedna page komponenta
- Page orchestruje data fetching, state a layout
- Žádná reusable business UI logika — ta patří do sdílených komponent

### Shared komponenta
- Jedna odpovědnost, nezávisí na konkrétní page
- Přijímá data přes props; žádné vlastní API calls
  (výjimka: self-contained widgety jako datepicker nebo file uploader)

### Form handling
- Formulář vždy odesílá na server — žádná autoritativní lokální validace
- Server vrátí chybový kód → klient překládá a zobrazí u příslušného pole
- Loading state formuláře se zobrazí po odeslání a zmizí po odpovědi

## Form model (write binding)

Každý write formulář má **jeden centrální form model** = jediný zdroj pravdy pro perzistovaná
field data, field chyby, touched stav, submit/loading stav a dirty baseline. Stránka nedrží
paralelní lokální stav pro tatáž pole.
- Model se konfiguruje jednou persistencní operací (+ volitelný loader + success handler).
- Pokud loader čte `*ExtData` (→ `rules/backend.md §API model role`), model může vlastnit celý
  root response, ale má **explicitně určený editable subtree** (`data`) = write payload;
  readonly sourozenci jsou kontext stránky, ne field-binding cíl.
- Frontend se řídí kontraktními rolemi `*View`/`*Data`/`*ExtData`; nevymýšlí vlastní boundary.
- **Validace = dry-run téže persistencní operace** (viz §Write-flow), ne paralelní klientská logika.
- UI se k poli váže přes **tenkou field abstrakci** (`value`/`set`/`blur`/`error`); field komponenta
  nezná interní storage ani path mechaniku.
- Create/edit větvení patří do persistencní operace, ne do UI vrstvy. Dirty se odvozuje proti
  baseline, ne z heuristického flagu.
- Konkrétní binding (`createFormStore` / `FormModelController` …) → `stack/<target>.md`.

## Write-flow (klient)

- Klient volá serverový **validation-only** režim pro živé UX hinty (debounce při psaní, na blur,
  před submitem). Na submit: validation-only → při úspěchu commit.
- Server commit vždy re-validuje (→ `rules/backend.md §Write-flow`); klient validaci jen
  zobrazuje, není autorita.
- Field chyba se ukáže u pole, global chyba nad formulářem; pole nezačíná chybou dřív, než na něj
  uživatel vstoupil nebo se pokusil odeslat.

## Rendering

- **App / interaktivní obsah → CSR** (client-side rendering) — default.
- **Veřejný / SEO obsah → SSG / prerender** (statické HTML při buildu) nebo
  CMS-native rendering. Ne CSR (špatné SEO).
- **Runtime custom SSR zakázán** — zvyšuje útočnou plochu (render nad user inputem,
  hydration vulns, DoS); SSG dá stejné SEO bez běhového renderu.
  Výjimka = vědomé rozhodnutí v PROJECT-CONSTITUTION s opodstatněním.

## Styling — tři oddělené vrstvy

1. **Tokeny** (`design/manual/tokens.css`, vlastní Leonard) = jediný slovník
   hodnot (barvy, spacing, radius). V kódu NIKDY magic hodnota — vždy `var(--token)`.
2. **Chování + a11y** = headless komponentová knihovna (dialog, select, …).
   Interaktivní komponenty se nepíší ručně — headless lib zajistí focus trap,
   klávesnici, ARIA, scroll-lock. Konkrétní lib → `stack/<target>.md`.
3. **Vizuál** = CSS Modules konzumující tokeny; markup zůstává čistý.

Zakázáno: utility-CSS frameworky (Tailwind), hardcoded barvy/spacing.

## Error handling

- Každá page zobrazuje chybový stav při selhání API call
- 422/400 s `code` → lokalizovaná zpráva dle kódu
- 500/síťová chyba → obecná hláška s možností retry

## Loading states

- Každá async operace má loading stav viditelný uživateli
- Loading stav nesmí zakrýt existující obsah (pokud je k dispozici)
- Polling (job tracking) aktualizuje UI přírůstkově

## Navigace

- SPA s client-side routing
- Každá stránka má URL odpovídající funkci
- Deep links fungují — uživatel může přejít přímo na URL

## Paginace a filtry

- Stav filtrů a paginace je v URL query params (sdílitelné, reload-safe)
- Výchozí řazení a paginace → viz spec každé funkce

## Polling

- Job tracking: poll každých 3–5 sekund
- Poll se zastaví jakmile job dosáhne terminálního stavu (COMPLETED / FAILED / STOPPED)
- UI zobrazuje aktuální progress a relevantní log záznamy

## Mobile responsiveness

- Breakpoint pro mobilní layout: `max-width: 768px` (nebo dle design manuálu)
- Na mobilních zařízeních se sidebar skryje; navigace přejde do fixního spodního pruhu
- Bázová velikost písma 16px — navržená pro mobilní čtení bez zoomu
- Sekce specifické pro desktop se skryjí přes CSS (ne vymažou)

## Backend availability indicator

- Globální vizuální indikátor nedostupnosti backendu, viditelný na všech routách
- Backend **nedostupný** při: síťové chybě requestu nebo response `5xx`
- Backend **dostupný** po jakékoli odpovědi mimo `5xx`
- Detekce ze dvou zdrojů: aktivní polling probe + pasivní pozorování API volání
- Polling nezávislý na uživatelské akci
- Text indikátoru výhradně z i18n klíče — nikdy hardcoded
- Nesmí blokovat interakci (žádný blokující overlay)

## Doménové konstanty a fail-closed

- UI neduplikuje enum hodnoty z kontraktu ad-hoc rozeseté po stránkách; drží je na jednom
  feature-local místě, **typově vázané na kontrakt/schema**.
- Odvozené struktury (lookup mapy, pořadí) se **generují** z téhož zdroje, nepíšou ručně.
- Neznámá enum hodnota **fail-closed** — preferovaně compile-time, jinak explicitní runtime chyba.
  **Žádný tichý fallback** (leda spec výslovně popisuje fallback UX jako záměr).
- Feature-local konstanta smí být záměrná **podmnožina** backend unionu; plné pokrytí se nevynucuje
  bez důvodu. Kód pracující s hodnotou mimo podmnožinu fail-closed.
- Konkrétní binding (`satisfies`, exhaustive switch přes `never`) → `stack/<target>.md`.

## Generovatelnost

Frontend pattern musí být definovaný tak, aby šel znovu vytvořit po smazání kódu.
Reusable rozhodnutí musí být opřená o normativní pravidlo (zde nebo v `stack/`).
