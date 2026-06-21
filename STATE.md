# STATE.md — dream-team-sandbox

<!-- ENGINE:STATE START -->
closed_waves: []
<!-- ENGINE:STATE END -->

## Aktualni fokus

✅ **Re-charter (L3) + contract wave HOTOVO (2026-06-21).** Repo povysen z „klec obalujici
appku" na **samostatnou RUNTIME/SANDBOX vrstvu (MOTOR + ZEĎ), ktera vystavuje kontrakt**.
Ustava prepsana (North Star + identita), kontrakt napsan, boundary audit hotov. Vsechny
gates PASS. Nic se nepresouvalo mezi repy (L3 — extrakce motoru je budouci krok).

### Wave `2026-06-21-runtime-contract` — completed (7 nodes, vsechny PASS)
- intake · product (spec+acceptance runtime; 1x spec-gate FAIL agnostika → fix) · spec-gate ·
  feasibility (z minule wave) · **architecture = KONTRAKT** (ted) · **security** (heimdall) ·
  **spec-audit** (sheldon). Implementacni/deploy uzly (qa/perf/code-quality/devops/deploy)
  jsou pro docs-only wave N/A — graf je nedosahne (nema kod); to je ocekavane, ne chyba.

### Deliverables (vse v tomto repu, committed)
- `PROJECT-CONSTITUTION.md` — re-charter: North Star (3 vrstvy + zelezna pravidla), identita
  RUNTIME, I1-I11 jako spec ZDI, MOTOR nacrt, kontrakt sekce. (commit `bae4948`)
- `specs/runtime-contract.md` + `acceptance/runtime-contract.md` (AC-1..14, agnosticke).
- **`contracts/runtime-contract.md`** (189 r) + **`contracts/api/runtime.openapi.yaml`** (452 r,
  8 ops, Environment schema, x-websocket) — KONTRAKT. App-facing error registr (10 kodu)
  disjunktni od interniho cage registru.
- `audit/runtime-boundary.md` — hranicni prestupky (motor v appce) + standalone mezery +
  endpoint→kontrakt mapovani + extrakce roadmapa.

### Gate verdikty
- heimdall (security) PASS: ZEĎ-disjunktnost strukturalne (`additionalProperties:false`),
  fail-closed („ready jen s aktivni ZDI"), zadny leak internich kodu, BYOK jen v PTY, auth oddelena.
- sheldon (spec-audit) PASS: konzistence + plocha-agnostika + AC-1..14 namapovane, 0 orphanu.

### Cage wave (`2026-06-21-containment-cage`) = ZEĎ (zachovana, paused/superseded framing)
T1+T2 hotovo, T3 qa staticky (128/128); zive AC + deploy = budouci motor-extrakce L3.
`server/cage/**`, `contracts/{containment-cage,error-codes}.md`, `rules/cage-enforcement.md`, I1-I11.

## Open Items (budouci, gated)

- [ ] **Motor-extrakce (koordinovany L3, vyzaduje vyslovne potvrzeni):** 1) vendor kontraktu
      do dream-team-app · 2) presun agent+lifecycle+image do runtime (vlastni verzovany image) ·
      3) app → tenke contract-klienty · 4) live acceptance (I1-I11 harness) pres kontrakt ·
      5) retire dvoji implementace. Kazdy krok = L3 ve vice repech.
- [ ] **Advisory hardening kontraktu (impl-time, heimdall):** `phase` (volny string) a
      `Error.detail` (additionalProperties:true) jsou potencialni leak kanaly → implementace
      MUSI scrubovat proti §7 noun-blacklistu + contract-test fixture.
- [ ] Vendoring mechanika kontraktu (submodul vs copy + drift-check v CI obou repu).
- [ ] Standalone mezery (contract-server, vlastni image, lifecycle service, CLI) — viz audit §C.
