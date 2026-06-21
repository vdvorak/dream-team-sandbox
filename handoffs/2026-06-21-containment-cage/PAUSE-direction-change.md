# HANDOFF — PAUZA: zmena smeru aplikace

**Wave:** `2026-06-21-containment-cage`
**Datum:** 2026-06-21
**Duvod pauzy:** Uzivatel meni smer dream-team-app. Wave zastaven v T3 pred dokoncenim
zbylych auditu a deploye. **Nic nenasazeno** (zamerne). Vse commitnute + pushnute.

> **Vstupni bod pro resume.** Strojovy stav: `current-run.md` (qa inflight) + `STATE.md`.
> QA detail: `handoffs/2026-06-21-containment-cage/T3-qa-handoff.md`.
> Plan: `~/.claude/plans/logical-churning-shore.md`. Ustava: `PROJECT-CONSTITUTION.md`.

## Co je klec (kontext pro resume)

`dream-team-sandbox` = **out-of-band bezpecnostni klec** pro `../dream-team-app`. Threat
actor = **workspace-container AI** (app pousti `claude` CLI v PTY jmenem uzivatelu: git,
spawn procesu, sit). Klec: default-deny egress, allowlist-only, neviditelna zevnitr,
neprepisovatelna zaklecovanym procesem. Aplikuje se jako obalka pri deploy; do repa appky
se nikdy nezapisuje (opacita I11).

## ⚠️ Dopad zmeny smeru appky na klec

Klec je navrzena proti **konkretni** mechanice dream-team-app (workspace microVM, 6PN,
cloudflared tunel, `gh` na app machine, /pty WebSocket). **Pokud zmena smeru meni:**
- workspace runtime / jak se pousti AI → revize threat modelu + de-root sekvence
- sit/egress potreby appky → revize doménového allowlistu (contracts/)
- deploy substrat (uz ne Fly?) → enforcer adapter uz je substrat-agnosticky, ale overit
- credential model → I9/I10 zavisle na tom, ze secrets jsou jen na app machine

→ **PRVNI KROK PRI RESUME:** projit zmenu smeru appky vs `specs/` + `contracts/` +
invarianty I1-I11; rozhodnout co plati / co prepracovat. Az pak pokracovat T3.

## Stav pipeline (run `2026-06-21-containment-cage`)

| faze | uzel | vysledek |
|---|---|---|
| T1 | intake | PASS (class: feature) |
| T1 | product (vision-po) | PASS — spec+acceptance, I1-I11 otagovane (2x spec-gate FAIL na agnostiku → opraveno) |
| T1 | spec-gate (sheldon) | PASS |
| T1 | feasibility (tony) | PASS — obe diry potvrzeny v kodu; I8/I9 uz drzi |
| T2 | architecture (ted) | PASS — 3-vrstvy H1-H7, de-root 0-4, overlay+drift, 11 error codes |
| T2 | backend (bob) | PASS — `server/cage/**` + overlay, 58 unit testu |
| T2 | code-lint (vitek) | PASS — F401 fixnuto (423 advisory → code-quality node) |
| T3 | qa (joey) | INFLIGHT — 128/128 statickych PASS; 32 zivych AC BLOCKED na deploy |
| T3 | security (heimdall) | **PENDING** — kriticke: adversarialni audit + Fly spike |
| T3 | code-quality (vitek) | PENDING — posoudit 423 advisory |
| T3 | performance (optimus) | PENDING |
| T4 | devops (alfred) | PENDING — wire fly/docker do cage-deploy injection pointu |
| T4 | deploy-approve (L3) → production → live acceptance | PENDING |

## Vytvorene artefakty (vse v dream-team-sandbox)

- `specs/containment-cage.md`, `acceptance/containment-cage.md` (I1-I11 otagovane)
- `contracts/containment-cage.md` (architektura), `contracts/error-codes.md` (11 kodu)
- `rules/cage-enforcement.md` (CE-1..CE-9), `stack/containment-cage.md`
- `server/cage/**` — Python logika (ruleset/enforcer adapter/acl/drift/lint/cage_deploy/errors)
- `server/cage/overlay/**` — Dockerfile.workspace, entrypoint.sh (de-root 0-4), nftables.cage.conf, fly.workspace.toml (6PN-only)
- `tests/server/unit/**` (58), `tests/integration/**` (55), `tests/acceptance/**` (harness I1-I11 + regression plan), `pytest.ini`

## Zname mezery / otevrene body (od bob + tony + joey)

1. **Fly spike nezbehl** — capsh CAP_NET_ADMIN drop v microVM, Network Policy API tvar,
   DNS resolver IP, metadata CIDR jsou zatim PREDPOKLADY (parametry s TODO-spike). Heimdall.
2. **Build/deploy/smoke runnery** = injektnutelne callable (nikoli realne `fly`/`docker`
   volani) — alfred doména (devops node).
3. **Spike-param duplikace** ruleset.py + nftables.cage.conf — drift mezi nimi nehlidan.
4. **Live AC (32 bodu)** neoverene — vyzaduji nasazenou klec; harness pripraven.
5. **I10-D** (rotace PAT) `[deferred]` — neresit dokud workspace nema git write credential.

## Pozn. k frameworku

`bob-backend` + `has_server: true` byly aktivovany v `project-config.md` (puvodni Watson
seed mel oboje off — graf ale vyzaduje implementacni uzel produkujici auditovatelny
server-code pred deployem). Pokud se klec prepracuje, znovu zvazit aktivni profil.
