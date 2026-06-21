---
wave: 2026-06-21-cage-setup
from: watson-interviewer
to: vision-po
type: setup-handoff
returns_to: null
timestamp: 2026-06-21T00:00:00+02:00
---

# Setup handoff — 2026-06-21

Watson dokoncil seeding projektu dream-team-sandbox. Vsechny setup artefakty jsou
zapsany; status SKELETON_NEEDS_WATSON odstranen. Projekt je pripraven na prvni spec wave.

## Co bylo udelano

- `PROJECT-CONSTITUTION.md` naseedovan: vize (containment cage), cil. skupina, co JE/NENI,
  hodnoty, NFR invarianty I1-I11 (security contract / acceptance criteria), domenova
  security pravidla, delivery topologie (3-vrstvy + overlay-at-deploy).
- `project-config.md` aktualizovan: status READY_FOR_SPEC, project_type greenfield,
  vision, stage, targets (infra/fly, has_ui/db/server false), aktivni agenti
  (vision-po, tony-cto, ted-architect, sheldon-spec, heimdall-security, alfred-devops,
  joey-qa, optimus-perf, vitek-quality), neaktivni (peter-web, chandler-db, leonard-ui,
  denisa-ux, edna-design, mob-mobile, winny-desktop, bob-backend, eywa-meta).
- `STATE.md` zalozeno s open items.
- `handoffs/LATEST` pointer nastaven.

## Kontext pro vision-po

Threat model je v plánu `/home/vitek/.claude/plans/logical-churning-shore.md`.
Klice: 2 akutni diry v soucasnem stavu (AI bezi jako root -> CAP_NET_ADMIN ->
in-VM firewall iluzorni; [http_service] v fly.workspace.toml -> Network Policy bypass).
Architektura: 3-vrstvy (Smokescreen + Fly Network Policy + budouci VPS nftables).
Invarianty I1-I11 v PROJECT-CONSTITUTION.md jsou primo acceptance criteria — spec
je ma prevest na testovatelne AC s konkretnimi prikazy verifikace.

## Doporuceny next step

Dispatch `vision-po` (sheldon-spec muze pracovat paralelne ci sekvencne dle grafu):
spec klece + acceptance criteria ze invariantu I1-I11.
Po T1 gate: heimdall-security Fly spike + ted-architect architektura.
