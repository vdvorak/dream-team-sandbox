---
cache_key: project-config-dream-team-v1.0
framework_version: self
last_updated: 2026-06-13
spec_language: cs
code_language: en
status: ACTIVE
---

# Project Config — dream-team

Self-hostovaný projekt: framework je svým vlastním projektem. TOOL vrstva (agenti, engine,
pipeline, templates, constitution, flow) je na rootu, protože **tenhle repo JE zdroj `.agentic/`**;
PRODUCT vrstva (tahle config, PROJECT-CONSTITUTION, STATE, backlog) z něj dělá projekt.

## Projekt
```yaml
project_name: dream-team
project_type: self-host        # framework budovaný vlastním frameworkem
vision: >
  Deterministický agentní engine (z issue → stabilní výsledek), jehož dlouhodobý cíl je
  platforma pro tvorbu agentních flow (node editor + AI-callable issue/todo systém, vzor vtodo).
stage: engine-mature           # engine hotový (selftest 57/57); platforma (app) je greenfield
audience: internal             # solo dev; výstup = software projekty stejného tvaru
```

## Targets
```yaml
# Engine (jádro, hotové) = Python3 + tenké POSIX sh, file-based, bez client targetu.
# Platforma (cíl) = web app konzumující engine:
active_targets:
  web:
    backend: python-fastapi    # FastAPI (konzumuje engine přes /done-style přechody nad souborovým stavem)
    frontend: solidjs          # SolidJS node editor + live view + in-app human-interakce
    db: postgres               # issues board + flow stav (až bude app); engine sám je file-based
    deploy: docker-compose     # lokální run vždy v kontejneru (determinismus prostředí)
```

## Project flags
```yaml
# has_server/has_db se ODVOZUJÍ automaticky z active_targets (web má backend+db) — viz
# frontier.load_project_config (#1 fix). Feature-level flagy (has_ui, touches_db) nastaví Vision ve spec.
flags:
  has_deploy: false     # OVERRIDE: active_targets.web.deploy by odvodil true, ale framework/engine se
                        # NEdeployuje (distribuce přes git/agentic-sync, ne CI/CD). App deploy = budoucí projekt.
```

## Active roles
```yaml
# Keyed by ROLE (node-id v pipeline/delivery.yaml). Persona binding viz pipeline/delivery.yaml `agent:`.
# Vypnuto = NEsmazáno; lze kdykoli zapnout per-need. Target-gating: no mobile/desktop → off.
active_roles:
  product: active          # Vision — feature specs
  feasibility: active      # Tony — stack/feasibility
  architecture: active     # Ted — kontrakty, rules
  db-schema: active        # Chandler — app DB (issues board)
  backend: active          # Bob — Python engine + FastAPI
  web: active              # Peter — SolidJS frontend
  ux-design: active        # Denisa — node editor je UX-heavy
  ui-system: active        # Leonard — komponenty
  design-intake: active    # design-source gate (UI flow)
  mobile: inactive         # žádný mobile target (target-gating)
  desktop: inactive        # žádný desktop target (target-gating)
  qa: active               # Joey
  performance: inactive    # ad-hoc; zapni při perf práci na enginu/appce
  spec-audit: active       # Sheldon
  security: active         # Heimdall — token-gating, scope
  code-quality: active     # Vitek
  design-audit: active     # Edna — node editor visual
  devops: active           # Alfred — Docker Compose
# Meta (mimo graf): eywa active (framework reálně mění agenty), monk inactive (na vyžádání),
# watson done (setup hotov).
```

## Fyzické cesty (logical → physical)
```yaml
project_constitution: PROJECT-CONSTITUTION.md
project_state: STATE.md
backlog: backlog/
handoffs: handoffs/
rules: rules/                 # POZN: ve frameworku je rules/ universal zdroj (dual-role TOOL+PRODUCT)
specs: specs/                 # zatím neexistuje — vzniká s první app feature
stack: stack/                 # zatím neexistuje — vzniká při app feasibility (Tony)
graph: pipeline/delivery.yaml
engine: scripts/pipeline/core/
```

## Klíčové invarianty (load-bearing, z VISION §2)
```yaml
load_bearing:
  - strict_spec_driven: "každý artefakt vychází ze spec; kód je odvozenina (check C7)"
  - state_in_files: "stav + handoffy v souborech; session naváže po výpadku"
  - tool_agnostic: "nic nespoléhá na paměť/feature konkrétního toolu"
  - script_scaffold_first: "mechanická práce scriptem/scaffoldem; LLM jen kde je úsudek"
  - typed_io: "uzly spojí jen kompatibilní výstup→vstup (artifacts.yaml)"
  - cost_time_per_issue: "run ledger per issue (ledger.py)"
  - determinism_consistency: "akceptační kritérium celého systému"
  - token_gated_transitions: "app vrstva: scoped token + optimistic concurrency (vzor vtodo)"
```

## Git
```yaml
versioned_repo: dream-team (tenhle repo)
working_dir: /home/vitek/dev/AI/dream-team
note: "TOOL vrstva (constitution/flow/agents/pipeline/scripts/templates) se distribuuje jako .agentic/ do jiných projektů (agentic-sync)."
```
