---
feature-id: containment-cage
flags: has_ui: false · touches_db: false · has_deploy: true
acceptance: acceptance/containment-cage.md
---
# Bezpečnostní klec (containment cage) pro dream-team-app

## Cíl

Zabalit nasazenou `dream-team-app` do out-of-band bezpečnostní klece, která zabrání
workspace-container AI (primary threat actor) v exfiltraci dat, pivotování na síť nebo
obcházení kredenciálových hranic. Klec je neviditelná zevnitř a nepozměnitelná zaklecovaným
procesem. Posture: vše zakázáno, allowlist jen explicitně.

## Aktér a cíl

Provozovatel `dream-team-app` (interní bezpečnostní role) chce mít záruky, že `claude` CLI
spuštěné ve workspace microVM nemůže opustit předdefinovaný síťový perimetr, eskalovat
privilegia ani odhalit existenci klece — a to i při aktivním pokusu o útěk.

## Hlavní scénář

Provozovatel spustí cage-deploy z `dream-team-sandbox` → klec aplikuje Fly Network Policy
(default-deny egress na host vrstvě), Smokescreen sidecar s doménovým allowlistem a hardened
workspace overlay (non-root exec, capability drop, no_new_privs) přes kód appky při deploy →
appka zůstane čistá, klec se nestane součástí jejího repa → `claude` uvnitř workspace ptý
komunikuje jen s povolenými doménami přes proxy, nemůže proxy obejít (host pouští :443 jen
na proxy/approved CIDR), nemůže smazat host-enforced policy (`CAP_NET_ADMIN` chybí) → test-suite
(invarianty I1–I11) ověří každý gate.

## Scope

**In:**
- Fly Network Policy (default-deny egress, deny SSH, allowlist :443 na proxy/approved CIDR + 6PN) — host-enforced.
- Smokescreen egress-proxy sidecar (doménový/SNI allowlist: `api.github.com`, `<CF_ACCESS_TEAM>.cloudflareaccess.com`).
- Hardened workspace overlay: non-root init sekvence, `CAP_NET_ADMIN` drop z bounding setu, `no_new_privs=1`, in-VM nftables jako defense-in-depth (po capability drop).
- Oprava dvou akutních děr: (a) agent.py běží jako root → musí exec jako non-root; (b) `[http_service]` v fly.workspace.toml → musí být odstraněn, workspace 6PN-only.
- Overlay-at-deploy model: artefakty (`Dockerfile.workspace`, `entrypoint.sh`, Smokescreen ACL, Network Policy applier) žijí jen v `dream-team-sandbox`; cage-deploy je přeloží přes kód appky.
- Network Policy applier (skript/CI, který volá Fly API a aplikuje policy); substrát-agnostický kontrakt (vrstva 3 = nftables na VPS, stejná logika).
- Opacita: definice klece nedostupná z workspace FS ani env.
- Secrets: `CLOUDFLARE_TUNNEL_TOKEN`, `CF_ACCESS_AUD`, `GH_TOKEN`, `ADMIN_BOOTSTRAP_TOKEN` zůstanou pouze na app machine, nikdy workspace.
- Scoping workspace git credential na jedno repo (deploy key / fine-grained PAT).

**Out:**
- Dev-time sandbox (lokální Docker omezení, pre-commit hooky atp.).
- Úprava business logiky `dream-team-app`.
- gVisor/Kata (není dostupné na Fly Machine; redundantní vůči hypervisor hranici).
- Auditní log PTY sessionů (možný navazující feature, mimo tento scope).
- Monitoring/alerting na cage breach (navazující).

## Rozhraní klec ↔ appka

- **Overlay-at-deploy:** cage-deploy build ignoruje `Dockerfile.workspace` z repo appky a nahradí ho hardened verzí z `dream-team-sandbox`. Repo appky není modifikováno.
- **Síťový kontrakt:** workspace komunikuje ven výhradně přes `$http_proxy=http://127.0.0.1:4750` (env injektnutý entrypointem klece). Proxy je jediná brána doménové granularity.
- **Izolace app↔AI:** dvě oddělené Fly apps, žádný sdílený volume ani netns; komunikace jen 6PN.
- **Přenositelnost substrátu:** Fly Network Policy applier a Smokescreen ACL musí být 1:1 přenositelné na VPS (nftables na hypervisor hostu) bez přepisu logiky klece.

## Edge cases & otevřené otázky

- **Proxy advisory risk:** pokud by host omylem povolil :443 kamkoli (chyba konfigurace), AI proxy obejde. Mitigace je host-level pravidlo, že :443 jde jen na proxy CIDR — toto musí být součástí Network Policy appliera a ověřeno v I2.
- **DNS/metadata side-channel:** deny :53 jinam než na allowlisted resolver + blackhole `169.254.0.0/16` musí být explicitně v host policy (zahrnuto v I1/I2 rozšíření — viz acceptance).
- **Exfil přes git:** workspace credential scoped na 1 repo nestačí, pokud appka dynamicky rotuje PAT — koordinace s alfred/ted u T2.
- **Shadow build maintenance:** klec udržuje "stínový" workspace image; při každé změně `Dockerfile.workspace` v appce je potřeba sync — finální model řeší ted u T2 gate.
- **fly-proxy bypass po každém deploy:** invariant I7 se musí re-testovat po každém `fly deploy` (fly.workspace.toml může být obnoven s `[http_service]`).
