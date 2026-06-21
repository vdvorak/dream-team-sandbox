---
cache_key: template-scaffolds-readme-v1.0
type: documentation
last_updated: 2026-06-10
---

# `templates/scaffolds/` — scaffold systém v2

Scaffold = **hotová kostra kódu**, ať AI vymýšlí co nejméně sama. To je hlavní páka
na **konzistenci zdrojáků**: dvě aplikace na stejném stacku vypadají a fungují
strukturálně stejně. Stack `_base/` fragment (v `templates/stacks/`) nese *co* za
nástroj; scaffold nese *kostru* (shared infra + 1 ukázkový vertical slice).

## Taxonomie (3 osy + agent + deploy)

Strojový index: `manifest.yaml`. Osa (`axis`) každého scaffoldu:

| axis | příklad | produces (typed I/O) |
|---|---|---|
| **backend** | python-fastapi, java-quarkus | server-code, unit-tests |
| **frontend** | **solidjs (web — CSR, primární)**, **flutter (mobile, iOS+Android)** | web-code, mobile-code, ui-components, unit-tests |
| **platform** | **electron (desktop — SolidJS renderer)** | desktop-code |
| **deploy** | fly, docker-compose | build, staging/production-deploy |
| **agent** | `agent-template.md` | — (jednotná struktura agentů) |

Projekt = kombinace os: např. `platform=web × backend=python-fastapi × frontend=solidjs`.

## Politiky (vynucené napříč scaffoldy)

- **Docker dev-run** — lokální běh **vždy v kontejneru**, pokud to platforma dovolí
  (nezávislost na hostu = deterministické prostředí). Pole `docker_dev` v manifestu.
- **Newest-stack** — scaffoldy drží **nejnovější stabilní** verze (Java → nejnovější
  LTS apod.); konkrétní piny žijí v build souborech scaffoldu (package.json, build.gradle,
  pyproject), ne v manifestu (verze stárnou).

## Scaffold-passing (delegace)

Při delegaci hlavní agent **neposílá subagenta hádat strukturu** — resolvne scaffold
z manifestu a předá ho jako **typovaný artefakt** `scaffold` (cesta + `produces` typy):

```sh
scripts/pipeline/scaffold.sh --backend python-fastapi   # → path + produces
scripts/pipeline/scaffold.sh --frontend solidjs --platform web
```

Subagent (Bob/Peter/…) dostane v handoffu `scaffold` artefakt → kopíruje/rozšiřuje
kostru, nevymýšlí ji. (Bob to už má ve `Vstupy`: „scaffold path" z Ted decision pass.)

## Agent scaffold

`templates/agent-template.md` = kanonická struktura definice agenta. Všichni agenti
ji sdílejí → konzistence + podklad pro budoucí „vytvoř si vlastního agenta". Spravuje
Eywa; `scripts/pipeline/check.sh §C4` ověří, že uzly grafu odkazují jen na existující agenty.

## Status a další kroky

`manifest.yaml` značí `status: ready | planned`. **Ready (všechny osy pokryté):**
python-fastapi, java-quarkus (backend), solidjs (web/CSR), **flutter (mobile, iOS+Android)**,
**electron (desktop)**, deploy (fly/compose), agent. Per-scaffold detaily v jejich
vlastních README (`templates/scaffolds/<stack>/README.md`).

> Build-ověřeno v CI/lokálně: python (pytest), solidjs (vitest), java (gradle codegen+test).
> Flutter/electron jsou strukturálně + syntakticky ověřené (dart format / TS), reálný
> `flutter test` / `electron-builder` vyžaduje SDK/GUI toolchain na hostu.
