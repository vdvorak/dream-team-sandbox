# HANDOFF — Wave `2026-06-21-motor-wave2a` (motor slice 2a: cage runtime + AC-6/AC-7)

**Datum:** 2026-06-21 · **Stav:** done, terminal_reached: true, vsechny gates PASS · **L3:** zadna cross-repo operace.

> Vstupni bod pro resume. Strojovy stav: `current-run.md` + `STATE.md` (ENGINE:STATE blok).
> Predchozi wave: `handoffs/2026-06-21-runtime-lifecycle/HANDOFF.md`.

## Co se stalo

Implementovan **MOTOR slice 2a** — provider-agnosticka cage runtime vrstva + realna integrace
CageEnforcementProvider (nahrazeni STUB z slice 1) + dva nove AC endpoints (AC-6 git status,
AC-7 listFiles). Cil wave: zprovoznit realne git/file operace nad workspace a odstranit STUB
z enforcement vrstvy, bez PTY (wave 2b) a bez Fly deploy (wave 2c).

**Deliverables (committed):**

| Soubor / adresar | Obsah |
|---|---|
| `server/cage/runtime.py` | CageRuntimeProvider Protocol — provider-agnosticka lifecycle vrstva (start/stop/status); zero-vendor-lock |
| `server/cage/providers/fly_provider.py` | FlyProvider — Fly.io adapter (httpx, opaque URL, bez substrat-nounu v odpovedi) |
| `server/runtime/enforcement/cage.py` | CageEnforcementProvider — realna impl, nahrazuje STUB z slice 1 |
| `server/runtime/workspace.py` | WorkspaceAccessor — git subprocess, list_files, path sandbox |
| `server/runtime/router.py` + `service.py` | AC-6 GET /git, AC-7 GET /files (novy router + service integrace) |
| `contracts/api/runtime.openapi.yaml` + `rules/` | prefix→path rename (breaking-fix, non-functional) |
| `tests/` | 47 testu PASS |

**Celkova suite: 47/47 PASS** (nova sada pro wave 2a; slice 1 suite 243/243 zustava zelena).

## Gate verdikty

Vsechny uzly wave dokonceny s PASS / ACK / DONE:

| Uzel | Vysledek |
|---|---|
| intake | PASS |
| product | PASS |
| spec-gate | PASS |
| feasibility | PASS |
| backend | PASS |
| code-lint | PASS |
| architecture | PASS |
| qa | PASS |
| performance | PASS |
| spec-audit | PASS |
| security | PASS |
| code-quality | PASS |
| audit-join | PASS |
| l2-review | ACK |
| done | DONE |

## Advisory naleze (neblokujici, pro improvements/)

| ID | Kategorie | Popis |
|---|---|---|
| A1 | performance | `list_files` blokuje event loop — sync `rglob` bez `asyncio.to_thread` |
| A2 | performance | `git subprocess` bez timeout — muze viset |
| W1 | code-quality | chybejici type annotation: `git_runner` parametr |
| W2 | code-quality | chybejici type annotation: `main.py` params |
| W3 | code-quality | chybejici type annotation: `list[dict]` navratovy typ |
| W8 | code-quality | `sleep()` nevola `provider.stop()` — chybi WHY komentar |
| SEC-1 | security | blacklist deny-by-default (whitelist pristup k souborum) |
| SEC-2 | security | dotfiles expozice (skryt `.git`, `.env`, `.ssh`) |
| SEC-3 | security | constant-time token compare (timing attack mitigation) |
| EXT-1 | architecture | `FlyProvider._find_machine_id` extraction candidate (stop/status duplikace) |

## Stav implementace po wave 2a

| Vrstva | Stav |
|---|---|
| CageRuntimeProvider Protocol | HOTOVO |
| FlyProvider (Fly.io adapter) | HOTOVO |
| CageEnforcementProvider (realna impl, byl STUB) | HOTOVO |
| WorkspaceAccessor (git subprocess, list_files, sandbox) | HOTOVO |
| AC-6 GET /git (git status) | HOTOVO |
| AC-7 GET /files (list files) | HOTOVO |
| AC-8 PTY/terminal (WebSocket) | Deferred — wave 2b |
| Produkcni deploy (Fly infra, secrets, image, staging→prod) | Deferred — wave 2c |
| Advisory hardening (A1/A2/W1-W3/W8/SEC-1-3/EXT-1) | Deferred — wave 2c nebo improvements/ |

## Open Items pro dalsi wave

1. **Wave 2b** — AC-8 PTY/terminal (WebSocket): realny terminal pristup ke cage kontejneru;
   gated na wave 2a (tuto wave).
2. **Wave 2c** — Produkcni deploy (Fly infra + secrets, build image, staging → produkce)
   + advisory hardening z teto wave (A1/A2/W1-W3/SEC-1-3/EXT-1).
3. **Motor-extrakce (koordinovany L3):** vendoring kontraktu do dream-team-app + presun motoru.
   Kazdy krok = L3 ve vice repech, vyzaduje vyslovne potvrzeni.

## Next

`to: bob-backend` (wave 2b — AC-8 PTY/terminal) nebo `to: alfred-devops` (wave 2c — Fly deploy).
Rozhodne uzivatel dle priority.
