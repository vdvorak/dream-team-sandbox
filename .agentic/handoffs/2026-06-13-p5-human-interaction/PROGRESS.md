---
wave: 2026-06-13-p5-human-interaction
run: 2026-06-13-p5-human-interaction
type: progress (živý — aktualizováno po každém uzlu)
status: DONE
---

# PROGRESS: P5 Human-interaction registry (první self-hosted flow run)

**Resume pointer (po ztrátě kontextu):** přečti tenhle soubor (TODO + Step log = kde jsme),
pak `bash scripts/pipeline/run.sh status` (stav stroje) → `run.sh drive` (další uzel). Stav
stroje = `current-run.md`; cost/čas = `runs/2026-06-13-p5-human-interaction/ledger.yaml`.

---

## Zadání

První reálný běh flow **na frameworku samotném** (self-hosting). Issue:
`backlog/human-interaction-registry.md` (= VISION roadmap P5).

**Co dodat:** rozšířit `pipeline/interactions.yaml` z 3 ad-hoc interakcí na **typovaný registr** —
úplná typologie (`choice/approval/ack/upload/text` + **`delegate-vs-provide`**: upload vlastního
HTML XOR spustit Denisu), typované I/O (`produces` napojené na `artifacts.yaml`), schéma (kind → UI
control → I/O) aby app uměla render bez per-gate kódu. Volitelně zpřísnit `check.py` C10.

**Acceptance:**
- [ ] `check.sh` C1–C15 OK (zejm. C10)
- [ ] `selftest.sh` 57/57 (+ mypy/pytest pokud se sáhne na core/)
- [ ] typologie pokrývá `delegate-vs-provide` (vlajkový případ vize)
- [ ] I/O schéma zdokumentované; interakce produkují typovaný artefakt/outcome

**Scope boundary:** NEstavíme app UI — jen deterministická definice (registr + schéma). Live-session
escape hatch = pozdějc.

**Dvojí cíl:** dodat P5 **+** dogfood (kde flow na self-hostingu drhne → backlog issue).

---

## TODO — uzly flow (živý checklist)

- [x] `intake` — klasifikuj (router) → class: **feature** · PASS
- [x] `product` (Vision, T1) — spec → `specs/p5-human-interaction-registry.md`, flags `has_ui:false touches_db:false` · PASS
- [x] `feasibility` (Tony, T1 gate) — PASS
- [x] `architecture` (Ted, T2) — kontrakt `contracts/p5-interaction-typology.md`; reuse-existing (design_source) · PASS
- [~] `web` (Peter) — **SKIPPED** (judged-skip: P5 nemá UI; dogfood nález — viz níže)
- [x] `backend` (Bob, T2) — `interactions.yaml` v2 + `check.py` C10 produces-validace + 8 unit testů · PASS
- [x] `qa` (Joey, T3 gate) — acceptance 1–6 OK · PASS
- [x] audit fan-out: `spec-audit` PASS ∥ `code-quality` PASS ∥ `security` **FAIL/advisory** (bez re-flow)
- [x] `audit-join` — PASS (performance/design-audit inactive → join je nepočítá)
- [x] `l2-review` (human) — ACK · (skip `devops` — engine se nedeployuje)
- [x] `done` — **terminál dosažen** ✓

**Acceptance:** [x] check C1–C15 · [x] selftest 57/57 + pytest 83 + mypy clean · [x] delegate-or-provide · [x] typové I/O schéma

---

## Step log

- **intake** → PASS, `class: feature`. (router, bez artefaktu)
- **product** (Vision) → PASS. Spec `specs/p5-human-interaction-registry.md` (Cíl/Scope/Acceptance/
  Edge/Decided; brevity-first). Flagy `has_ui:false touches_db:false` → routing přeskočí UI/DB roli.
- **feasibility** (Tony) → PASS. Malé rozšíření registru, žádná nová závislost.
- **architecture** (Ted) → PASS. Kontrakt typologie `contracts/p5-interaction-typology.md`
  (schéma interakce + 6 kindů → UI control → I/O). Reuse-existing: `delegate-or-provide` stojí na
  `design_source` flagu, žádný nový routing.
- **web** → **SKIPPED** (dogfood — viz Dogfood nálezy). Doplnil jsem chybějící project flagy
  (`has_server`/`has_db`) do project-config, aby backend edge firnul.
- **backend** (Bob) → PASS. `pipeline/interactions.yaml` v2 (typovaný registr + schéma header +
  `design-source` překlopen na `delegate-or-provide` s `delegate_to: ux-design`); `check.py` C10
  rozšířen o `delegate-or-provide` kind + **produces-validaci** (typované I/O, I7); 8 unit testů
  (`test_check_interactions.py`). Gate: check OK, selftest 57/57, pytest 83, mypy clean.
- **qa** (Joey) → PASS. Acceptance 1–6 ověřeno (check C10, selftest, pytest).
- **spec-audit/code-quality/security** → PASS/PASS/**FAIL-advisory**. Heimdall advisory na budoucí
  upload validaci (E1 severity gating: zaznamenáno do `findings`, BEZ re-flow, uzel zůstal completed).
- **audit-join → l2-review → done** → ACK → terminál. (skip `devops`; `has_deploy:false` → l2-review→done)

**Výsledek:** P5 dodáno reálně přes celý flow. Produkt: `pipeline/interactions.yaml` v2 (typovaný
registr), `scripts/pipeline/core/check.py` C10 produces-validace, 8 unit testů, spec + kontrakt.

---

## Dogfood nálezy

Backlog issue: `backlog/flow-self-host-gaps.md`. Nalezeno během P5 běhu:

1. **project-config postrádal project flagy** (`has_server`/`has_db`) — deklaroval jsem jen
   `active_targets`/`active_roles`, ale `backend` edge je gated `project.has_server`. Bez flagu →
   backend edge UNKNOWN → uzel se nedispatchne. **Fix:** doplněn `## Project flags` blok do project-config.
2. **Klient fan-out není gated `has_ui`** — edge `architecture → [web,mobile,desktop]` nemá `when`;
   `web` uzel je gated jen `project.targets.web`. → no-UI feature (has_ui:false) na projektu s web
   targetem **spustí web**. Workaround: `run.sh skip web`. **Fix (graf):** web uzel by měl být
   `when: project.targets.web && spec.has_ui` (nebo edge gated has_ui).
3. **(meta) Graf modeluje app-delivery, ne framework registry/meta práci** — P5 (edit engine
   registru) sedí na „backend" jen volně (engine ≈ server-side logika). Větší téma: rozšířit graf
   o meta-role, nebo druhý graf pro práci na frameworku. (Souvisí s `backlog/watson-self-host-mode`.)
4. **`skip` na už-dispatchnutý (inflight) uzel ho nevyřadí z `frontier`** → běh visí čekáním na něj
   (web zůstal inflight i po skip). **Fix (engine):** `mutate_state("skip")` / `run.sh skip` má taky
   `state.remove_inflight(node)`. Workaround: ručně vyřadit z `frontier` v current-run.
5. **Feature-vs-projekt flag tension** — `has_deploy`/`has_ui` jsou projekt-level, ale jestli
   KONKRÉTNÍ feature deployuje/má UI je feature-level. Engine feature (P5) na projektu s deploy/web
   targetem chce skip. Souvisí s #1/#2 (project flagy) — možná feature-level override flagů.
