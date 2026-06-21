---
type: boundary-audit
wave: 2026-06-21-runtime-contract
owner: ted-architect
status: v1
sources:
  - PROJECT-CONSTITUTION.md
  - contracts/runtime-contract.md
  - /home/vitek/.claude/plans/logical-churning-shore.md §Audit + §Roadmapa extrakce MOTORu
  - read-only: /home/vitek/dev/AI/dream-team-app/ (L3 cross-repo zákaz — NEMĚNIT)
---
# Boundary Audit — runtime-boundary

> Kompilace nálezů k wave `2026-06-21-runtime-contract`. Popisuje stav hranic MOTOR/ZEĎ
> mezi repem `dream-team-sandbox` (RUNTIME) a `dream-team-app` (APLIKACE). Žádná změna kódu
> není součástí tohoto dokumentu — vše je PROPOSAL k budoucímu koordinovanému L3.

---

## A) Hraniční přestupky — MOTOR dnes žije v appce

Níže jsou soubory v `dream-team-app`, které patří do RUNTIME per North Star.
Stav ověřen read-only; realita odpovídá plánu s jednou nuancí (viz poznámky).

| Soubor (v `dream-team-app`) | Co dělá | Klasifikace |
|---|---|---|
| `poc/workspace-container/agent.py` | In-container server: `/clone` (git clone, idempotentní), `/git-status` (branch + changed files + last commit), `/pty` (WS PTY bridge přes tmux + pty.openpty), `/repo-status` (lightweight clone check), `/files` (recursive file fetch s path-traversal guard) | MOTOR (schopnosti: clone, git, PTY, file-read) + ZEĎ (path-traversal guard v `/files` a `/repo-status`) |
| `server/services/workspace_container.py` | Docker lifecycle: `ensure_workspace` (run/rm/wait-readiness), `_docker()` volání; `WORKSPACE_AGENT_BASE` env — localhost default nebo remote URL; `ensure_repo` (lazy clone pres agenta) | MOTOR (lifecycle, clone orchestrace) |
| `server/routers/terminal_router.py` | PTY WS bridge: app-side WS endpoint `/api/terminal/pty`; CF-Access JWT auth (header `cf-access-jwt-assertion` / cookie); relay na `_AGENT_WS` (agentův `/pty`) | MOTOR (relay logika) + ZEĎ-boundary (CF-Access auth ZUSTAVA v appce; relay je MOTOR) |
| `server/services/workspace_files.py` | Tenký HTTP klient k agentovi: `fetch_files` + lazy-clone (volá `ensure_repo` pokud `cloned=false`); `repo_status` check; parsuje agent odpověd | MOTOR (file-read klient, lazy-clone orchestrace) |
| `poc/workspace-container/Dockerfile` + `entrypoint.sh` | Container image workspace agenta: Python + Claude Code CLI install, init script (volume symlinky, uid setup) | MOTOR + ZEĎ overlay (hardened init pořadí; de-root sekvence bude zde) |
| `Dockerfile.workspace` (root) | Build context pro Fly deploy workspace image — volá `poc/workspace-container/Dockerfile` kontextem | MOTOR |
| `fly.workspace.toml` | Fly app `dream-team-workspace`: region, build (→ `Dockerfile.workspace`), volumes (`dt_workspace`, `dt_claude_config`), žádný `[http_service]` (6PN only) | MOTOR (substrát lifecycle config) |
| `poc/workspace-container/managed-settings.json` | Locked Claude Code settings (BYOK gate, tool allowlist uvnitř workspace) | ZEĎ |
| `poc/workspace-container/deny-secrets.sh` | Secrets enforcement při init: blokuje injekci high-value secrets do workspace env | ZEĎ |

**Poznámka — nuance vs plán:** Plán hovoří o `WORKSPACE_AGENT_BASE` jako o leaku.
Realita v `workspace_container.py` je přesnější: proměnná se používá **výhradně interně
v appce** (volby: localhost Docker nebo Fly 6PN URL); nikdy není exponována do kontraktní
plochy ani vrácena klientovi. Budoucí kontrakt ji nahradí opaque `connection` handle na
straně runtime — to je správný směr, ale leak dnes není přímo v kontraktní rovině,
jen v kódu appky.

**Dalsi nuance — lazy clone vs `ensure`:** `workspace_files.py` dnes implementuje lazy-clone
sekvenci (fetch → pokud `cloned=false` → `ensure_repo` → znovu fetch). Kontrakt to řeší
složením clone do `ensure` (jedna operace, race odstraněn). Dnešní appka tak nese logiku,
která patří do runtime.

---

## B) Co zůstává v appce (NEpřesouvat)

Tyto části `dream-team-app` jsou výhradně aplikační a runtime je vůbec nevidí:

- **UI / klientská vrstva** (Svelte/web, projekt views, schvalovací dialogy)
- **Project model a repozitáře** (`file_projects_repository`, `projects_router`, …)
- **Dispatch / engine / flow** (graph_service, run_state_service, agents_service)
- **Gates a approvals** (done_service, interaction_service)
- **CF-Access auth** (JWT validace na WS endpoint — auth zůstane v appce; runtime jen relay)
- **GitHub integrace** (github_service — write credentials nikdy do workspace)
- **Parsery a graph engine** (issues, todos, file_issues_service)
- **Connection orchestrace** (connection_service — app-side state nad projekty)

---

## C) Standalone mezery — runtime dnes nemá

Věci, které North Star vyžaduje, ale `dream-team-sandbox` dnes neobsahuje:

| Mezera | Popis | Dopad |
|---|---|---|
| Vlastní verzovaný base image | Image (`Dockerfile.workspace`) žije v appce; runtime nemá vlastní image registry ani versioning | Runtime nelze nasadit standalone bez appky |
| Vlastní agent | `agent.py` je v `poc/workspace-container/` appky; sandbox ho jen overlay-deployuje přes cage-deploy | Ownership + versioning mismatch |
| Lifecycle service | `cage-deploy` je one-shot (build+deploy); neexistuje service s API pro `ensure/sleep/destroy` | Kontrakt nelze volat — `/v1/*` nikde neběží |
| Contract server | Žádný HTTP server v sandboxu nevystavuje `/v1/environments/…` dle `runtime-contract.md` | Standalone drive (curl/CLI) není možný |
| CLI / standalone entrypoint | Žádný `runtime-cli` ani jednoduchý skript pro curl-driven test kontraktu | Verifikace standalone usability chybí |
| Live integration testy | Žádný harness v sandboxu, který ověří I1–I11 přes kontrakt; `server/cage/` testy jsou interní | Acceptance přes kontrakt neexistuje |

---

## D) Cage wave = ZEĎ (zachováno)

Výstupy wave `2026-06-21-containment-cage` jsou platná enforcement vrstva RUNTIME a
zůstavají nedotčeny:

| Artefakt | Role |
|---|---|
| `server/cage/**` (ruleset, enforcer, acl, drift, lint, cage_deploy) | ZEĎ implementace (overlay-at-deploy model) |
| `contracts/containment-cage.md` | Cage spec — ZEĎ invarianty |
| `contracts/error-codes.md` | Interní cage error registr (ODDELENY od app-facing registru kontraktu) |
| `rules/cage-enforcement.md` | Normativa ZDI |
| Invarianty I1–I11 (v `PROJECT-CONSTITUTION.md`) | Acceptance criteria ZDI — platná spec, NEMENAT |

Tyhle artefakty jsou **ZEĎ** per North Star. Runtime-contract kontrakt je od nich disjunktní:
interní cage error kódy nikdy neleaknou do app-facing roviny (viz `contracts/runtime-contract.md §4`).

---

## E) Mapování de-facto interface → kontrakt

Každý dnešní endpoint agenta v appce mapuje na operaci nového kontraktu:

| Dnešní endpoint (v `agent.py` / appce) | Operace kontraktu | Poznámka |
|---|---|---|
| `POST /clone` + `ensure_workspace()` | `POST /v1/environments/{id}/ensure` (`ensureEnvironment`) | Clone složen do ensure; race odstraněn |
| `GET /repo-status` | součást `GET /v1/environments/{id}` (`getEnvironment`) — pole `repo.cloned` | Lightweight check → stav objektu |
| `GET /git-status` | `GET /v1/environments/{id}/git` (`getGitStatus`) | Shape: `{branch, dirty, changed_files[], last_commit}` |
| `GET /files` | `GET /v1/environments/{id}/files` (`listFiles`) | Path-traversal guard zachován; error `ERR_PATH_ESCAPE` |
| `GET /pty` (WS, v agentovi) přes relay `/api/terminal/pty` (appka) | `GET /v1/environments/{id}/terminal` (WS, `attachTerminal`) | CF-Access auth zůstane v appce před relay; kontrakt používá mTLS/token na App→Runtime |
| `GET /health` (agentův) | `GET /v1/healthz` | Kontrakt vrací i `contract_version` |
| `WORKSPACE_AGENT_BASE` env | Opaque `connection.control_url` + `connection.terminal_url` v `environment` objektu | Substrát (6PN / localhost / VPS) neviditelný pro odběratele |

---

## F) Roadmapa extrakce MOTORu

BUDOUCÍ koordinovaný L3. Neprovádět bez výslovného potvrzení uživatele. Každý krok
= koordinovaný L3 v obou repech (`dream-team-sandbox` + `dream-team-app`).

**Krok 1 — Stabilizovat kontrakt + vendor do appky**
Runtime kontrakt (`contracts/runtime-contract.md` + `contracts/api/runtime.openapi.yaml`)
se vendoruje / submoduluje do appky read-only. CI drift-check (`healthz.contract_version`
vs vendorovaná verze) v obou repech. Žádný přesun kódu.

**Krok 2 — Přesun agent + lifecycle + image ownership do runtime**
`poc/workspace-container/agent.py`, `Dockerfile` a `entrypoint.sh` se přesunou do sandboxu.
Sandbox dostane vlastní image registry + verzovaný base image. `fly.workspace.toml` migruje
sem. Appka přestane image buildit.

**Krok 3 — App nahradí vnitřní motor tenkými contract-klienty**
`workspace_container.py`, `workspace_files.py` a relay v `terminal_router.py` se nahradí
HTTP/WS stuby volajícími `/v1/*` kontraktu. CF-Access JWT auth zůstane v appce (před voláním
do runtime). `WORKSPACE_AGENT_BASE` se odstraní — nahrazuje ho `connection` handle z
`getEnvironment` odpovědi.

**Krok 4 — Live acceptance (I1–I11 harness) přes kontrakt**
Harness v sandboxu ověří všechny invarianty ZDI přes kontraktní plochu (ne interním
voláním). `ensure` → `ready` → spusť test-suite I1–I11 → `destroy`.

**Krok 5 — Retire dvojí implementace**
Po úspěšném přijetí acceptance: odstraní se duplikátní motor-kód z appky. Appka zůstane
čistý odběratel kontraktu.

---

## Závěr — shoda plán vs realita

Realita appky sedí s plánem na 95 %. Dvě upřesnění:

1. **`WORKSPACE_AGENT_BASE` není leak do kontraktní plochy** — je to interní konstanta
   v `workspace_container.py`, ne response pole. Kontrakt ji správně nahradí opaque
   `connection` handle; dnešní stav je přijatelný jako přechodový.

2. **Lazy-clone v `workspace_files.py` je aplikační logika patřící do runtime.** Sekvence
   `repo_status → ensure_repo → fetch_files` řeší race, který kontrakt eliminuje složením
   clone do `ensure`. Jde o největší funkční duplikaci, která zmizí v Kroku 3 roadmapy.

Vše ostatní (motor v appce, standalone mezery, cage-wave artefakty, endpoint mapping)
odpovídá plánu přesně. Žádný kód se tímto dokumentem nepřesouvá.
