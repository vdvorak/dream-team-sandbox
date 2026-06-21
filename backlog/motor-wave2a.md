---
id: motor-wave2a
type: feature
wave: 2026-06-21-motor-wave2a
priority: now
created: 2026-06-21
status: intake
---

# Motor wave 2a — CageEnforcementProvider + provider-agnostická runtime vrstva + AC-6/7

## Žadatel a kontext

Navazuje přímo na slice 1 (`2026-06-21-runtime-lifecycle`). CageEnforcementProvider je aktuálně
STUB (`NotImplementedError`). Tato wave ho nahrazuje realnou implementací + přidává novou
provider-agnostickou cage runtime vrstvu a dvě deferred AC (git status, file listing).

Granularita potvrzena uživatelem (2026-06-21): tři vlny místo jedné velké:
- **Wave 2a (tato):** motor bez PTY + AC-6 + AC-7
- **Wave 2b:** AC-8 PTY/terminal (WebSocket)
- **Wave 2c:** produkční deploy (Fly infra) + advisory hardening

## Co chceme

### 1. Provider-agnostická cage runtime vrstva (`server/cage/runtime.py`)

Nová vrstva pro lifecycle operace nad cage workspacem: `start` / `stop` / `status`.
**Oddělená od deploy orchestrace** (`server/cage/deploy/cage_deploy.py` — ta řeší
image build + Fly deploy; `runtime.py` řeší běžící instance).

**Provider abstrakce (no vendor lock-in):**
- Dnes: Fly.io jako provider.
- Architektura MUSÍ být provider-agnostická — přechod na jiný provider (VPS, Docker Compose,
  jiný cloud) co nejjednodušší.
- Vzor: podobně jako `EnforcementProvider` Protocol v `server/runtime/enforcement/provider.py`
  — uzavřený typ výsledku, provider protocol, konkrétní implementace za ním.
- Fly.io specifika (6PN, fly machines API, .internal DNS) NESMÍ leaknout přes provider rozhraní.

### 2. CageEnforcementProvider — reálná implementace (nahradí STUB)

Aktuálně: `server/runtime/enforcement/cage.py` → `NotImplementedError`.
Napojit na `server/cage/**`:
- `ensure_active()` → skutečné spuštění workspace přes cage runtime vrstvu (start/status).
- `health()` → skutečný health check cage runtime.
- Překlad `CageError` → `EnforcementFailed` (viz STUB docstring — vzor je tam).
- Zachovat fail-closed invariant (RCP-A2): žádná cesta nesmí vrátit `EnforcementActive`
  bez prokazatelně aktivního enforcement.

### 3. AC-6 — `getGitStatus` (nový endpoint)

`GET /v1/environments/{project_id}/git` — git status nad real workspace.
- Prostředí musí být `ready` (jinak `409 ERR_ENVIRONMENT_NOT_READY`).
- Response: stav working tree (čisté/dirty, branch, uncommitted files — dle kontraktu §10).
- Sandboxed: vždy uvnitř workspace (žádný path escape).
- Out-of-contract: nesmí leaknout interní workspace cesty ani substrát-nouns (RCP §7).

### 4. AC-7 — `listFiles` (nový endpoint)

`GET /v1/environments/{project_id}/files?path=` — seznam souborů v workspace.
- Prostředí musí být `ready`.
- Path sandbox: `ERR_PATH_ESCAPE` (`403`) při path traversal mimo workspace root.
- Paginace nebo limit na depth/count (spec určí konkrétní hodnoty).
- Nesmí leaknout interní workspace layout (overlay dirs, entrypoint.sh atd.).

## Architektonické vstupy (rozhodnutí uživatele)

- **Provider vrstva:** Varianta B — `server/cage/runtime.py` jako nová vrstva, lifecycle
  operace (start/stop/status) oddělené od deploy orchestrace (`cage_deploy.py`).
- **Provider abstrakce:** Fly.io dnes, ale design provider-agnostický (protocol + adapter vzor).
  Fly specifika schovány za adapter — výměna = nový adapter.

## Scope OUT (deferred)

- AC-8 PTY/terminal → wave 2b.
- Produkční deploy (Fly infra, secrets, image build, staging) → wave 2c.
- Advisory hardening (security/code-quality/perf z slice 1) → wave 2c nebo samostatná.
- Motor-extrakce do dream-team-app (koordinovaný L3) → budoucí.

## Acceptance criteria mapping

| AC | Popis | Stav po wave 2a |
|---|---|---|
| AC-6 | getGitStatus | **IN** |
| AC-7 | listFiles | **IN** |
| AC-2 | fail-closed (CageEnforcementProvider reálný) | **posílen** (STUB → reálný) |
| AC-9 | healthz (CageEnforcementProvider.health()) | **posílen** |
| AC-8 | PTY/terminal | DEFERRED → wave 2b |

## Existing artefacts (slice 1 základ)

- `server/runtime/enforcement/cage.py` — STUB, nahradit.
- `server/runtime/enforcement/provider.py` — Protocol + typy (zachovat beze změny).
- `server/cage/**` — ZEĎ implementace (read-only z pohledu runtime vrstvy).
- `specs/runtime-control-plane.md` + `acceptance/runtime-control-plane.md` — rozšířit o AC-6/7.
- `contracts/runtime-contract.md` v1.1.0 + `contracts/api/runtime.openapi.yaml` — rozšířit o AC-6/7 endpointy.
