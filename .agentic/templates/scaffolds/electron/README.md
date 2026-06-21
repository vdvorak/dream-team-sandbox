# Scaffold — Electron desktop (SolidJS renderer)

Reálná spustitelná kostra desktop aplikace. Watson ji při setupu electron projektu
**zkopíruje** do `clients/desktop/`. Electron je tu **platform shell** kolem
SolidJS rendereru — UI patterny (Kobalte + tokeny + CSS Modules) ber ze
`solidjs` scaffoldu, tady řešíme jen okno, IPC most a balení.

## Stack (vetted)

| Vrstva | Volba | Proč |
|---|---|---|
| build | **electron-vite** | main/preload/renderer přes Vite + TS + HMR |
| balení | **electron-builder** | dmg / nsis / AppImage |
| renderer | **SolidJS** | shodný s web scaffoldem (sdílené komponenty/patterny) |
| jazyk | **TypeScript** (strict) | typovaný most renderer↔main |

## Bezpečnostní baseline (Heimdall)

Kostra je bezpečná by-default — neměň, leda s důvodem:
- `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`
- renderer sahá na main **jen** přes typovaný preload most (`window.api`), nikdy
  ne na celé `ipcRenderer`; každý kanál je explicitní
- `setWindowOpenHandler` posílá externí odkazy do prohlížeče, ne do okna appky
- CSP v `index.html`: jen vlastní bundle (žádné remote/inline skripty)

## Layout

```
electron/
  package.json  electron.vite.config.ts  electron-builder.yml
  tsconfig.json (renderer)  tsconfig.node.json (main+preload)  vitest.config.ts
  src/main/index.ts                 # app lifecycle, BrowserWindow, IPC handlery
  src/preload/index.ts              # contextBridge → typovaný window.api
  src/preload/index.d.ts            # ambient typy mostu pro renderer
  src/renderer/index.html
  src/renderer/src/{index.tsx,App.tsx}
  src/renderer/src/lib/{greeting.ts,greeting.test.ts}   # vzor testovatelné čisté logiky
```

## Build & test

```bash
cd clients/desktop      # po kopii Watsonem; ve scaffoldu jsi přímo zde
npm install             # pozor: stáhne electron binárku (~velká)
npm test                # vitest — čistá renderer logika (bez Electronu)
npm run typecheck       # tsc renderer + main/preload
npm run dev             # electron-vite dev (okno + HMR; potřebuje GUI/display)
npm run package         # electron-builder → dist/ (instalátor pro platformu)
```

První feature: přidej IPC kanál v `main/index.ts` (`ipcMain.handle`), vystav ho
v `preload/index.ts` (rozšíří `window.api` typ), zavolej z rendereru. UI komponenty
kopíruj ze `solidjs` scaffoldu.

## Renderer = SolidJS → platí solidjs patterny

Renderer není zvláštní svět: je to SolidJS, takže **přebírá `solidjs` scaffold patterny**
1:1. Pro write formuláře zkopíruj do `src/renderer/src/` z `solidjs` scaffoldu:
`components/createFormStore.ts` (write binding — rules/frontend.md §Form model),
`components/ui/TextField.tsx` (field wrapper), Kobalte wrappery a design tokeny
(`index.css`). Desktop-only app tím má stejný frontend↔backend store jako web.

## Docker dev-run

`docker_dev: false` — Electron potřebuje GUI/display toolchain, dev běh je na hostu.
Backend (cíl IPC/HTTP volání) běží v Dockeru přes svůj scaffold.
