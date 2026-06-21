# STATE.md — dream-team-sandbox

<!-- ENGINE:STATE START -->
<!-- Strojově psané enginem na terminálu `done` (statewrite.py) — NEEDITUJ ručně.
     Uzavřené vlny = FAKTA o tom, co je hotové; lidský narativ pod markerem je pro PŘÍBĚH. -->
```yaml
closed_waves:
  2026-06-21-runtime-lifecycle:
    closed_at: '2026-06-21T19:27:39.714400+00:00'
    status: done
    wave_base: ce416f24808fd65e0279d85cfb5813ea62afac88
    class: feature
    nodes: 15
    last_outcome: ACK
    return_loops: 1
    summary: runs/2026-06-21-runtime-lifecycle/summary.md
    ledger: runs/2026-06-21-runtime-lifecycle/ledger.yaml
    touches:
      touches_db: false
      touches_server: true
      touches_shared_ui: false
      has_ui: false
  2026-06-21-motor-wave2a:
    closed_at: '2026-06-21T00:00:00.000000+00:00'
    status: done
    wave_base: d647abd4ffa23e11c92500645c32d24f333cdb20
    class: feature
    nodes: 15
    last_outcome: DONE
    return_loops: 0
    summary: runs/2026-06-21-motor-wave2a/summary.md
    ledger: runs/2026-06-21-motor-wave2a/ledger.yaml
    touches:
      touches_db: false
      touches_server: true
      touches_shared_ui: false
      has_ui: false
```
<!-- ENGINE:STATE END -->

## Aktualni fokus

**Zadna aktivni wave.** Wave `2026-06-21-motor-wave2a` uzavrena (terminal_reached: true, DONE).
Dalsi krok: wave 2b (AC-8 PTY/terminal) nebo wave 2c (Fly deploy + advisory hardening) dle priority.

✅ **Wave 2a — MOTOR real: CageEnforcementProvider + provider-agnostická cage runtime vrstva + AC-6/AC-7 HOTOVO (2026-06-21).**
- `server/cage/runtime.py` — CageRuntimeProvider Protocol (provider-agnosticka lifecycle vrstva).
- `server/cage/providers/fly_provider.py` — FlyProvider (Fly.io adapter, httpx, opaque URL).
- `server/runtime/enforcement/cage.py` — CageEnforcementProvider (realna impl, nahrazeni STUB).
- `server/runtime/workspace.py` — WorkspaceAccessor (git subprocess, list_files, path sandbox).
- `server/runtime/router.py` + `service.py` — AC-6 GET /git, AC-7 GET /files.
- `contracts/api/runtime.openapi.yaml` + `rules/` — prefix→path rename.
- 47 testu PASS.

✅ **Runtime control-plane lifecycle core (slice 1) HOTOVO (2026-06-21).** PATER RUNTIMU
postavena — 5 operaci stavoveho automatu (ensure/get/sleep/destroy/healthz), fail-closed
EnforcementProvider kontrakt (uzavreny typ), 3-vrstvova architektura (router/service/repository).
243/243 testu PASS. Kontrakt bumpnut v1.0.0 → v1.1.0 (ERR_INVALID_REQUEST, non-breaking).
Deploy track vedome odlozen na slice 2 (realny motor + cloud infra). Slice 1 navic
empiricky overen zivym demem (curl: cely lifecycle + fail-closed v 'down' rezimu → nikdy ready).

### Wave `2026-06-21-runtime-lifecycle` — completed (15 nodes, vsechny PASS, return_loops: 1)
- intake · product · spec-gate (3 kola resolve-loop; strukturalni lean prepis) · feasibility ·
  architecture · security (heimdall opus) · code-quality · **implementation (bob)** · qa ·
  perf · spec-audit (1x FAIL po contract-bumpu → AC-1g/1b/9a opraveny → PASS). Deploy
  track (devops/deploy) vedome preskocen — odlozeno na slice 2.

### Deliverables (vse committed)
- `server/runtime/**` (13 modulu) — router/service/repository, EnforcementProvider Protocol
  (EnforcementActive|EnforcementFailed uzavreny soucet), DevEnforcementProvider (active/fail/down),
  CageEnforcementProvider (STUB = slice 2). Spustitelny: `uvicorn server.runtime.main:app`.
- `specs/runtime-control-plane.md` + `acceptance/runtime-control-plane.md` (RCP-1..14).
- `rules/runtime-control-plane.md` (RCP-A1..A8) + `stack/runtime-control-plane.md`.
- `tests/`: 49 unit + 74 integration + 7 perf — 243/243 PASS.
- **`contracts/runtime-contract.md` + `contracts/api/runtime.openapi.yaml`** — bumpnuto
  v1.1.0 (ERR_INVALID_REQUEST pridan, non-breaking).

### Wave `2026-06-21-runtime-contract` — completed (7 nodes, vsechny PASS)
- Repo re-charter (L3): North Star, identita RUNTIME, kontrakt napsan.
- `PROJECT-CONSTITUTION.md`, `contracts/runtime-contract.md` (v1.0.0),
  `contracts/api/runtime.openapi.yaml`, `audit/runtime-boundary.md`.

### Cage wave (`2026-06-21-containment-cage`) = ZEĎ (zachovana, paused/superseded framing)
T1+T2 hotovo, T3 qa staticky (128/128); zive AC + deploy = budouci motor-extrakce L3.
`server/cage/**`, `contracts/{containment-cage,error-codes}.md`, `rules/cage-enforcement.md`, I1-I11.

## Open Items (budouci, gated)

- [x] **Wave 2a (hotovo):** CageEnforcementProvider + provider-agnostická cage runtime vrstva (`server/cage/runtime.py`) + AC-6 git status + AC-7 listFiles. Wave `2026-06-21-motor-wave2a`. 47 testu PASS.
- [ ] **Wave 2b:** AC-8 PTY/terminal (WebSocket) — gated na wave 2a (splneno).
- [ ] **Wave 2c:** Produkční deploy (Fly infra + secrets, build image, staging → produkce) + advisory hardening z wave 2a (A1/A2/W1-W3/SEC-1-3/EXT-1) — gated na wave 2b.
- [ ] **Produkcni deploy (wave 2c):** Fly infra + secrets, build image (vlastni verzovany),
      staging → produkce. Vedome odlozeno z wave `runtime-lifecycle`, zafazeno do wave 2c.
- [ ] **Advisory hardening (impl-time, neblokujici):** security — dev-token fail-fast guard,
      constant-time compare; code-quality — type anotace (mypy strict), test-helper dedup,
      healthz 503 v OpenAPI (W3); perf — lock-dict GC, perf acceptance targets formalizovat.
- [ ] **Motor-extrakce (koordinovany L3, vyzaduje vyslovne potvrzeni):** 1) vendor kontraktu
      do dream-team-app · 2) presun agent+lifecycle+image do runtime · 3) app → tenke
      contract-klienty · 4) live acceptance (I1-I11 harness) pres kontrakt · 5) retire dvoji
      implementace. Kazdy krok = L3 ve vice repech.
- [ ] Vendoring mechanika kontraktu (submodul vs copy + drift-check v CI obou repu).
- [ ] **Advisory hardening kontraktu (heimdall):** `phase` (volny string) a `Error.detail`
      (additionalProperties:true) jsou potencialni leak kanaly → impl MUSI scrubovat proti
      §7 noun-blacklistu + contract-test fixture.
