---
cache_key: template-stack-solidjs-v2.1
type: template
---

# Stack — SolidJS web (kanonický reference)

**Zlatý standard** pro web target. Watson seeduje obsah níže (po `---` až po
`## Pozn.`) do projektového `stack/web.md` a zkopíruje kostru z
`templates/scaffolds/solidjs/`. Cíl: **dva solid projekty vypadají strukturou
i syntaxí skoro identicky.** Desktop = + `_target/electron`.

Tech-agnostic pravidla viz `rules/frontend.md`. Hygiena viz `constitution.md`.

Odchylka od tohoto referenceu = vědomé rozhodnutí (Ted/Leonard), ne drift.

---

## Technologie

- **SolidJS 1.8+** (fine-grained reaktivita), **@solidjs/router**
- **Vite** (build/dev), **Vitest** + **@solidjs/testing-library** + jsdom (testy)
- **@kobalte/core** — **headless** komponenty (dialog, select, … — chování +
  přístupnost hotové, BEZ stylů). Styling řídí projekt přes tokeny.
- **openapi-fetch** — typovaný API klient; typy generuje **openapi-typescript**
  z backendového `contracts/api/openapi.yaml`
- TypeScript (strict)

Pouze deklarované knihovny (constitution); nová závislost vetted.

## Struktura

```
src/
├── index.tsx          # render + Router (root = AppShell)
├── index.css          # DESIGN TOKENY (CSS custom properties) — autorita Leonard
├── api/
│   ├── client.ts      # openapi-fetch createClient<paths>
│   └── schema.ts      # generováno openapi-typescript (NEeditovat ručně)
├── components/
│   ├── ui/            # otokenované wrappery nad Kobalte (Button, Dialog, …) + *.module.css
│   └── layout/        # AppShell, … + *.module.css
├── pages/<feature>/   # page komponenta + *.module.css (+ *.test.tsx)
└── i18n/              # překlady (žádné hardcoded texty)
```

## Styling — KRITICKÉ (řeší „ne Tailwind, ne raw CSS sprawl")

Tři vrstvy, ostře oddělené:

1. **Tokeny** (`index.css` `:root` custom properties) = jediný slovník hodnot
   (barvy, spacing, radius, shadow). Vlastní **Leonard** (`design/manual/`).
   V kódu NIKDY magic hodnota (`13px`, `#abc`) — vždy `var(--space-4)` ap.
2. **Chování + a11y** = **Kobalte** (headless). Dialog/Select/… se NEpíše ručně
   — focus trap, klávesnice, ARIA, scroll-lock bere z Kobalte.
3. **Vizuál** = **CSS Modules** (`*.module.css`) konzumující tokeny. Markup
   zůstává čistý (`class={styles.card}`), žádná utility-soup.

**ZAKÁZÁNO:** Tailwind / utility-CSS (zaplevelí markup), ručně psané interaktivní
a11y (bug-prone — od toho je Kobalte), hardcoded barvy/spacing (constitution).

Mezi projekty se liší **jen tokeny** (design je vědomá proměnná); chování +
struktura + komponentové API jsou identické (uniformita).

## Komponenty a stav

- **Page komponenta** = jeden route; orchestruje data + layout; bez reusable
  business UI logiky
- **UI komponenta** (`components/ui/`) = otokenovaný wrapper nad Kobalte nebo
  prostý prezentační prvek; jedna odpovědnost
- State: signály lokálně; sdílený stav `createStore`/context, ne globální proměnné
- Reset hodnoty: `null`, ne `undefined` (konvence)
- Jednosměrný data flow (data dolů, události nahoru)

## Data a validace

- `apiClient` (openapi-fetch) typovaný z `schema.ts`; výstup brát jako untrusted
- Klient smí mít UX hint validaci; autorita je vždy server (constitution)
- Žádné hardcoded user texty — i18n (constitution §Lokalizace)

## i18n — povinné (od prvního řádku)

**Pravidlo:** žádný UI string natvrdo v JSX ani TS. Každý viditelný text → `t("namespace.key")`.

### Struktura

```
src/
├── i18n/
│   ├── index.ts          # init i18next + export t()
│   └── locales/
│       ├── cs.json       # primární jazyk (výchozí)
│       └── en.json       # fallback
```

### `i18n/index.ts` — kanonický vzor

```ts
import i18next from "i18next"
import cs from "./locales/cs.json"
import en from "./locales/en.json"

i18next.init({
  lng: "cs",
  fallbackLng: "en",
  resources: {
    cs: { translation: cs },
    en: { translation: en },
  },
  interpolation: { escapeValue: false },
})

export const t = (key: string, options?: Record<string, unknown>): string =>
  i18next.t(key, options) as string

export default i18next
```

### Klíče — vnořené po namespace

```json
{
  "common": { "loading": "Načítám...", "error": "Nastala chyba", "retry": "Zkusit znovu" },
  "nav":    { "home": "Domů" },
  "<feature>": { "<key>": "..." }
}
```

Klíče plochá notace v kódu: `t("common.loading")`, `t("nav.home")`. Nový namespace =
nová sekce v obou JSON, ne nový soubor.

### Knihovny

`i18next` + `@mbarzda/solid-i18next` (viz Building blocks tabulka).

## Konvence komponent

### Adresář `components/`

Sdílené UI komponenty žijí v `src/components/`. Dvě podsložky:

```
src/components/
├── ui/        # otokenované wrappery nad Kobalte + prezentační prvky
└── layout/    # AppShell a layoutové komponenty
```

### Komponenta = vlastní složka

Každá komponenta tvoří vlastní složku s explicitním barrel exportem:

```
components/ui/Button/
├── Button.tsx      # implementace
├── Button.css      # (nebo Button.module.css)
└── index.ts        # export { Button } from "./Button"
```

Importuje se: `import { Button } from "@components/ui/Button"`.
Plochý soubor (`Button.tsx` vedle `Dialog.tsx` vedle …) = zakázáno u komponent
s vlastním stylem.

### Sdílené utility a hooks

```
src/utils/   # čisté funkce (fetch wrapper, formátování, polling helper, …)
src/hooks/   # SolidJS-specific reaktivní utility (createInterval, useAsync, …)
```

Boilerplate (fetch loop, poll-interval, datum formát) se NEkopíruje mezi stránkami —
zavede se jednou v `utils/` nebo `hooks/` a reusuje.

## CSS — design tokeny (doplněk ke styling sekci výše)

- Tokeny (CSS custom properties v `index.css`) jsou **jediný slovník hodnot** —
  spacing, barvy, border-radius, shadow. Vše ostatní konzumuje `var(--token)`.
- Sdílené CSS utility (`.spinner`, `.sr-only`, …) žijí v `index.css` nebo
  dedikovaném `styles/global.css`; komponenty je NEredefinují.
- Hardcoded pixely/hex tam, kde existuje token = lint nález.

## Rendering

- **CSR default** (viz `rules/frontend`). Veřejný/SEO obsah → SSG/prerender nebo
  CMS-native (NE runtime SSR) — řeší overlay/ústava.

## Testování

- Vitest (`environment: jsdom`) + `@solidjs/testing-library`
- Mock `apiClient` (`vi.mock`); router přes `MemoryRouter`
- minimální high-signal suite (render + klíčová interakce per page)

## Building blocks — declared

Core + vetted optional jsou v `templates/stacks/recommended-libs.yaml` — agent se ptá
`scripts/pipeline/lib.sh --stack solidjs [--capability …]`, neimprovizuje volbu.

| Knihovna (core) | Role |
|---|---|
| solid-js + @solidjs/router | UI + routing |
| @kobalte/core | headless komponenty (chování + a11y) — styling přes CSS/SASS Modules |
| openapi-fetch + openapi-typescript | typovaný API klient z OpenAPI |
| lucide-solid | ikony |
| i18next + @mbarzda/solid-i18next | i18n (constitution: od prvního řádku) |
| vite + vite-plugin-solid | build |
| vitest + @solidjs/testing-library + jsdom + msw | testy + API mock |

**Styling:** komponentová knihovna (Kobalte) + **CSS/SASS Modules**. **ZÁKAZ Tailwind**
(zaplevelí zdroják) a inline-style klubek.

**Vetted optional (přidej až když schopnost potřebuješ — `lib.sh`):** drag-and-drop →
`@thisbeyond/solid-dnd`; node-graph/flow → `@xyflow/react`; rich-text → `@tiptap/*`;
html-sanitize → `dompurify`. Mimo recommended list = nová závislost → Tony + Heimdall.

## Scaffold

Reálná kostra: `templates/scaffolds/solidjs/` — tokeny, Kobalte-wrapped Button +
Dialog, AppShell, ukázková stránka + vitest. Watson kopíruje do `clients/web/`.
Ted/Leonard: stack-defined patterny = `scaffold-only` default.

## Extraction Candidates

| Pattern | Výskyty | Rozhodnutí |
|---|---|---|
| _(prázdné — Ted/Leonard plní po každé wave)_ | | |

## Pozn. pro Watson / Leonard

- Obsah od `## Technologie` po `## Extraction Candidates` se kopíruje do
  projektového `stack/web.md`.
- `index.css` tokeny jsou **default paleta** — Leonard je přepíše dle designu
  projektu. Komponentové API a chování zůstávají (uniformita).
- Desktop varianta: + `_target/electron` (renderer = tento solid base).
