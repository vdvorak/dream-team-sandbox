---
cache_key: project-config-dream-team-sandbox-v1.0
framework_version: "0.37.0"
last_updated: 2026-06-21
spec_language: cs
code_language: en
status: READY_FOR_SPEC
---

# Project Config — dream-team-sandbox

## Projekt
```yaml
project_name: dream-team-sandbox
project_type: greenfield
vision: "Out-of-band bezpečnostní klec (containment cage) pro dream-team-app — default-deny egress, Smokescreen doménový allowlist, host-enforced Fly Network Policy, overlay-at-deploy model."
stage: setup/design
```

## Targets
```yaml
active_targets:
  infra:
    deploy: fly          # Fly.io teď; VPS (nftables) later — substrát-agnostický design
    containerized: true
flags:
  has_ui: false
  has_db: false
  has_server: true       # cage = server/deploy kód (applier, de-root entrypoint, cage-deploy skript) → musí být implementován a proauditován před deploy
  has_deploy: true       # cage-deploy applier (Network Policy, Smokescreen ACL, overlay)
  design_source: derive  # žádné UI
```

## Active agents
```yaml
profile: standard
agents:
  vision-po: active
  tony-cto: active
  ted-architect: active
  sheldon-spec: active
  heimdall-security: active
  alfred-devops: active
  joey-qa: active
  optimus-perf: active
  vitek-quality: active
  watson-interviewer: done
  bob-backend: active        # producent server/deploy kódu klece (applier, entrypoint, cage-deploy) — node `backend`
  # inactive — projekt nemá UI/DB/mobile/desktop/web target:
  peter-web: inactive
  chandler-db: inactive
  leonard-ui: inactive
  denisa-ux: inactive
  edna-design: inactive
  mob-mobile: inactive
  winny-desktop: inactive
  eywa-meta: inactive
```

## Fyzické cesty (logical → physical)
```yaml
project_constitution: PROJECT-CONSTITUTION.md
specs: specs/
contracts: contracts/
rules: rules/
stack: stack/
backlog: backlog/
acceptance: acceptance/
design: design/
improvements: improvements/
status: status/
handoffs: handoffs/
audit: audit/
project_state: STATE.md
runs: runs/
```
