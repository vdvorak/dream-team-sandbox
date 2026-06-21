# Scaffold — SolidJS web (Kobalte + design tokens)

Reálná spustitelná kostra web klienta. Watson ji při setupu solidjs projektu
**zkopíruje** do `clients/web/`. Kanonický popis: `templates/stacks/_base/solidjs.md`.

## Styling filozofie (proč ne Tailwind, proč ne raw CSS)

Tři oddělené vrstvy:
- **tokeny** (`src/index.css` `:root`) = slovník hodnot; nikdy magic číslo
- **chování + a11y** = **Kobalte** (headless) — Dialog/Select se nepíše ručně
- **vizuál** = CSS Modules (`*.module.css`) konzumující tokeny; čistý markup

Mezi projekty se mění **jen tokeny** (design). Komponentové API + chování zůstávají.

## Co Watson upraví

- `src/index.css` tokeny → design projektu (Leonard, `design/manual/`)
- `src/api/schema.ts` → generuje `openapi-typescript` z backend `openapi.yaml`
  (ukázkový schema.ts je hand-written stub pro běh kostry)

## Build & test

```bash
cd clients/web        # po kopii Watsonem; ve scaffoldu jsi přímo zde
npm install
npm test              # vitest (jsdom) — bez backendu, api se mockuje
npm run typecheck     # tsc --noEmit
npm run build         # tsc + vite build
npm run dev           # vite dev server (proxy /api → backend)
```

První feature: zkopíruj `pages/example/` jako vzor, komponenty z `components/ui/`
(Kobalte wrappery), styling přes tokeny.

## Form binding (write)

`components/createFormStore.ts` = kanonický write binding (rules/frontend.md §Form model):
jeden centrální store = pravda o data/errors/touched/submitting/dirty; validace je
**dry-run téže persistencní operace**; `submit` udělá validation-only → při čistém commit
(server re-validuje). UI se k poli váže přes tenký `Field` (`components/ui/TextField.tsx`).

```tsx
const form = createFormStore<{ label: string }>({
  defaultData: { label: "" },
  // validate=true → ?validate dry-run; false → commit
  save: async (data, validate) => {
    const { data: res, error } = await apiClient.POST("/examples", {
      params: { query: { validate } }, body: data,
    });
    return { fieldErrors: res?.fieldErrors, error };
  },
  onSuccess: () => refetch(),
});
// <TextField field={form.field("label")} label="Popisek" disabled={form.submitting()} />
```

## Web-app baseline (zadrátované)

Kostra je rules-compliant web-app start, ne jen 1 stránka:
- **i18n od prvního řádku** — `src/i18n/` (i18next, CS default); v komponentách `t("klíč")`,
  texty v `locales/{cs,en}.json`. Žádný literál k uživateli (constitution §Lokalizace).
- **auth plumbing** — `src/auth/tokenStore.ts` (access token v signálu mimo context) +
  `client.ts` middleware injektuje `Authorization` automaticky. Stránky token nepředávají ručně.
- **BackendStatusBanner** — globální indikátor nedostupnosti backendu na všech routách
  (rules/frontend.md §Backend availability), mountnutý v `index.tsx`.

Feature-specific (kostra nezavádí, doplní spec): login UI / `AuthProvider` + route guards,
širší katalog komponent (`Page` container, `ListState`, `ErrorPage`) — vzor viz UnagyDev web client.

## Doménové konstanty (bound to contract + fail-closed)

Enum hodnoty z kontraktu se nepíšou ad-hoc — drž je feature-local, **typově vázané na
`schema.ts`** přes `satisfies`, odvozené struktury generuj (rules/frontend.md §Doménové konstanty):

```typescript
import type { components } from "@/api/schema";
type ExampleKind = components["schemas"]["ExampleData"]["kind"];

// satisfies → když backend změní enum, TypeScript spadne ZDE
export const EXAMPLE_KINDS = ["A", "B"] as const satisfies ReadonlyArray<ExampleKind>;

// fail-closed: neznámá hodnota throw (žádný tichý fallback), `never` chytne chybějící case
function kindLabel(k: ExampleKind): string {
  switch (k) {
    case "A": return t("example.kind.A");
    case "B": return t("example.kind.B");
    default: { const _x: never = k; throw new Error(`Unknown kind: ${_x}`); }
  }
}
```

## Docker dev-run (host-nezávislost)

Vite dev server **v kontejneru** (`docker_dev: true` v manifestu), bez Node na hostu:

```bash
docker compose -f docker-compose.dev.yml up --build     # web :5173 (HMR)
```

`src/` je mountovaný → HMR funguje. Backend běží zvlášť (jeho compose); vite proxuje
`/api` → `:8000` (`vite.config.ts`). Pro backend na hostu je v compose namapovaný
`host.docker.internal` (host-gateway).
