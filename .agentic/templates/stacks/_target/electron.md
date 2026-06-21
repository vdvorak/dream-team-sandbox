---
cache_key: template-stack-target-electron-v1.0
type: template
---

# Stack fragment — Electron (target)

Přidává se do `stack/desktop.md` k UI base fragmentu (`_base/solidjs`).
Vetted defaulty. Winny vlastní desktop kód.

---

```markdown
## Building blocks — Electron
| Nástroj | Role |
|---|---|
| Electron | desktop runtime (Chromium + Node) |
| electron-builder | packaging, instalátory (Win/macOS/Linux) |
| preload bridge | bezpečný IPC mezi main a renderer |

## Tech realizace — Electron
- Architektura: main proces (Node, OS přístup, data) vs renderer (UI,
  SolidJS). Žádný přímý Node přístup z rendereru.
- Bezpečný IPC (povinné, Heimdall): `contextIsolation: true`,
  `nodeIntegration: false`; komunikace přes preload `contextBridge` s
  explicitně whitelistovaným API. Žádné `remote`.
- Data: lokální DB (`_db/sqlite`) v main procesu; renderer přes IPC.
- Packaging: electron-builder; podpisy/notarizace per cílová platforma
  (Alfred / release).
```

---

## Pozn.
Bezpečnostní nastavení IPC je hard requirement (RCE riziko) — Heimdall ho
auditује. Renderer styling/komponenty dědí z `_base/solidjs` (design manuál).
