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

Provozovatel spustí cage-deploy z `dream-team-sandbox` → klec aplikuje host-enforced síťovou
politiku (default-deny egress), doménový egress proxy (sidecar) s doménovým allowlistem
a hardened workspace overlay (non-root exec, capability drop, no_new_privs) přes kód appky
při deploy → appka zůstane čistá, klec se nestane součástí jejího repa → `claude` uvnitř
workspace komunikuje jen s povolenými doménami přes proxy, nemůže proxy obejít (host pouští
:443 jen na proxy/approved CIDR), nemůže smazat host-enforced policy (CAP_NET_ADMIN chybí)
→ test-suite (invarianty I1–I11) ověří každý gate.

## Scope

**In:**
- Host-enforced síťová politika (default-deny egress, deny SSH, allowlist :443 na proxy/approved CIDR + privátní síť mezi app a workspace) — nepřepsatelná zevnitř microVM.
- Doménový egress proxy sidecar (doménový/SNI allowlist: `api.github.com`, `<CF_ACCESS_TEAM>.cloudflareaccess.com`).
- Hardened workspace overlay: non-root init sekvence, `CAP_NET_ADMIN` drop z bounding setu, `no_new_privs=1`, in-VM firewall jako defense-in-depth (po capability drop).
- Oprava dvou akutních děr: (a) agent.py běží jako root → musí exec jako non-root; (b) workspace má veřejný http ingress → musí být odstraněn, workspace privátní-síť-only.
- Overlay-at-deploy model: hardened workspace overlay artefakty žijí jen v `dream-team-sandbox`; cage-deploy je přeloží přes kód appky.
- Applier host-enforced politiky (skript/CI, který politiku aplikuje); substrát-agnostický kontrakt (host-level enforcement stejnou logikou i mimo primární infrastrukturu).
- Opacita: definice klece nedostupná z workspace FS ani env.
- Secrets: `CLOUDFLARE_TUNNEL_TOKEN`, `CF_ACCESS_AUD`, `GH_TOKEN`, `ADMIN_BOOTSTRAP_TOKEN` zůstanou pouze na app machine, nikdy workspace.
- Scoping workspace git credential na jedno repo (deploy key / fine-grained PAT).

**Out:**
- Dev-time sandbox (lokální Docker omezení, pre-commit hooky atp.).
- Úprava business logiky `dream-team-app`.
- Hypervisor-level izolace (gVisor/Kata) — redundantní vůči stávající hypervisor hranici.
- Auditní log PTY sessionů (možný navazující feature, mimo tento scope).
- Monitoring/alerting na cage breach (navazující).

## Edge cases & otevřené otázky

- **Proxy advisory risk:** pokud by host omylem povolil :443 kamkoli (chyba konfigurace), AI proxy obejde. Mitigace: host-level pravidlo, že :443 jde jen na proxy CIDR — součást Network Policy appliera, ověřeno v I2.
- **DNS/metadata side-channel:** deny :53 jinam než na allowlisted resolver + blackhole `169.254.0.0/16` musí být explicitně v host policy (zahrnuto v I1/I2).
- **Exfil přes git:** workspace credential scoped na 1 repo nestačí, pokud appka dynamicky rotuje PAT — `[deferred]` (viz AC-I10 v acceptance).
- **Shadow build maintenance:** klec udržuje "stínový" workspace image; při každé změně workspace Dockerfile v appce je potřeba sync — model řeší navazující fáze.
- **Regression po deploy:** invariant I7 (žádný veřejný ingress) se musí re-testovat po každém deployi, protože konfigurace může být obnovena na výchozí hodnotu.

Konkrétní technologický stack (host-level enforcement implementace, proxy nástroj, firewall backend) je zdokumentován v `stack/containment-cage.md`. Technický rozhraní kontrakt (env, porty, secret jména) je v `contracts/containment-cage.md`.
