---
wave: 2026-06-10-deploy-platform
from: watson-interviewer
to: null
type: session-summary
returns_to: null
timestamp: 2026-06-10T00:00:00Z
---

# Session Summary — Wave: deploy-platform (2026-06-10)

## Tato session

Dvě tematické změny frameworku + review Machina projektu.

---

## Co bylo dokončeno

### 1. Deploy platforma jako první třída stacku

**Motivace:** Watson se ptal na hosting (Fáze 2), ale odpověď se nikam nepropagovala.
`_target/` měl jen `electron.md` a `fly.md` (nepoužívaný v composition table).

**Změny:**

- `templates/stacks/_target/docker-compose.md` — nový fragment (VPS/self-hosted Docker Compose)
- `templates/stacks/_target/wordpress-hosting.md` — nový fragment (shared/managed hosting, žádný Docker; vzor pneukarnik)
- `templates/stacks/README.md` — composition table rozšířena o deploy fragment pro každý vzorový projekt; `_target/` sekce dokumentuje všechny 4 platformy (v1.1)
- `agents/watson-interviewer.md` v1.6 → **v1.7**:
  - Fáze 2: explicitní otázky na deploy platformu + kontejnerizaci (s mapou platform → `_target` fragment + `containerized: true/false`)
  - Template library / Stack composition table: deploy fragment povinný pro každý projekt s nasazením
  - Formát výstupu: přidána pole `deploy-platform` a `containerized`

**Částečně splněno z open items:** "Watson → deploy scaffold" — Watson nyní ví, který `_target` fragment použít, ale krok pro fyzické zkopírování deploy scaffold souborů (fly/compose) Watson stále nemá. Alfred to stále dělá sám (workaround z v0.12.0).

### 2. xyflow jako vetted default pro DnD v SolidJS

- `templates/stacks/_base/solidjs.md` v2.0 → **v2.1**:
  - Building blocks tabulka: přidán `@xyflow/react` jako podmíněná knihovna pro node-graph / pipeline editor
  - Explicitní zákaz jiných DnD knihoven

**Pozor:** `@xyflow/solid` neexistuje na npm (potvrzeno Machinou). Vetted package je `@xyflow/react` — ale pro SolidJS projekt vyžaduje kompatibilní wiring nebo alternativu. Toto je nevyřešené — označit jako open item.

### 3. Machina — stack soubory

Review projektu ukázal: `stack/` prázdný, přestože implementace existuje.

- `stack/server.md` — vytvořen (python-fastapi + postgres + projekt-specifické závislosti: python-ulid, aiofiles; Scaffold sekce dokumentuje mezery)
- `stack/web.md` — vytvořen (solidjs v2.1; zachyceny mezery: chybí openapi-fetch, testovací závislosti; @thisbeyond/solid-dnd, @tiptap k verifikaci)

---

## Slabé místo

- `@xyflow/react` v SolidJS projektu: cross-framework použití nevyzkoušeno. Může vyžadovat wrapper nebo alternativu až přijde pipeline-editor feature.
- Watson scaffold krok pro deploy soubory stále chybí — Alfred gap přetrvává.

---

## Open items vzniklé touto session

- [ ] **@xyflow v SolidJS** — ověřit real-world integraci `@xyflow/react` v SolidJS projektu, nebo najít alternativu. Až pipeline-editor feature přijde na řadu (Machina).
- [ ] **Watson → deploy scaffold copy** — Watson ví, který `_target` fragment použít, ale nekopíruje fyzické soubory (Dockerfile, fly.toml, docker-compose.yml). Doplnit krok do §Template library pod Scaffold sekci (po vzoru app scaffold copy).
- [ ] **USAGE.md deploy setup chapter** — stále chybí (z předchozích open items).
- [ ] **Machina stack gaps** — doplnit openapi-fetch, vitest + testing-library, ověřit @tiptap (viz `Machina/stack/web.md §Scaffold`).

---

## Soubory změněné touto session

| Soubor | Akce |
|---|---|
| `templates/stacks/_target/docker-compose.md` | vytvořen |
| `templates/stacks/_target/wordpress-hosting.md` | vytvořen |
| `templates/stacks/README.md` | upraven (v1.1) |
| `agents/watson-interviewer.md` | upraven (v1.7) |
| `templates/stacks/_base/solidjs.md` | upraven (v2.1) |
| `Machina/stack/server.md` | vytvořen |
| `Machina/stack/web.md` | vytvořen |
