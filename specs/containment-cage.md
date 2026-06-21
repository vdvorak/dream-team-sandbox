---
feature-id: containment-cage
flags: has_ui: false · touches_db: false · has_deploy: true
acceptance: acceptance/containment-cage.md
---
# Bezpecnostni klec (containment cage) pro dream-team-app

## Cíl

Zabalit nasazenou `dream-team-app` do out-of-band bezpecnostni klece, která zabrání
workspace-container AI (primary threat actor) v exfiltraci dat, pivotování na síť nebo
obcházení kredenciálových hranic. Klec je neviditelná zevnitř a nepozmenitelná zaklecovaným
procesem. Posture: vše zakázáno, allowlist jen explicitne.

## Aktér a cíl

Provozovatel `dream-team-app` (interní bezpecnostní role) chce mít záruky, že AI agent
spušteny ve workspace microVM nemůže opustit preddefinovaný síťový perimetr, eskalovat
privilegia ani odhalit existenci klece — a to i pri aktivním pokusu o útěk.

## Hlavní scenár

Provozovatel spustí nasazení klece z `dream-team-sandbox` → klec aplikuje host-enforced síťovou
politiku (default-deny egress), doménový egress proxy (sidecar) s doménovým allowlistem
a hardened workspace overlay (non-root exec, drop síťové capability správy, no-new-privileges)
pres kód appky pri deploy → appka zůstane cistá, klec se nestane soucástí jejího repa →
AI agent uvnitř workspace komunikuje jen s povolenými doménami pres proxy, nemůže proxy
obejít (host povoluje odchozí HTTPS jen na proxy nebo schválené CIDR), nemůže smazat
host-enforced policy (capability síťové správy chybí) → test-suite (invarianty I1–I11)
overí každý gate.

## Scope

**In:**
- Host-enforced síťová politika (default-deny egress, blokování správy hostitelů, allowlist
  odchozího HTTPS na proxy nebo schválené privátní CIDR) — neprepísatelná zevnitř microVM.
- Doménový egress proxy sidecar s doménovým/SNI allowlistem (konkrétní domény viz
  `contracts/containment-cage.md`).
- Hardened workspace overlay: non-root init sekvence, drop capability síťové správy z
  bounding setu, no-new-privileges, in-VM firewall jako defense-in-depth (po capability dropu).
- Oprava dvou akutních der: (a) workspace agent bežel jako root → musí exec jako non-root;
  (b) workspace má verejný HTTP ingress → musí být odstranen, workspace privátní-síť-only.
- Overlay-at-deploy model: hardened workspace overlay artefakty žijí jen v `dream-team-sandbox`;
  nasazení klece je prelozi pres kód appky.
- Applier host-enforced politiky (skript/CI, který politiku aplikuje); substrát-agnostický
  kontrakt (host-level enforcement stejnou logikou i mimo primární infrastrukturu).
- Opacita: definice klece nedostupná z workspace FS ani env.
- Secrets (viz `contracts/containment-cage.md`): klícové tokeny/secrets zůstanou pouze na
  app machine, nikdy workspace.
- Scoping workspace git credential na jedno repo (deploy key nebo omezený PAT).

**Out:**
- Dev-time sandbox (lokální kontejnerová omezení, pre-commit hooky atp.).
- Úprava business logiky `dream-team-app`.
- Hypervisor-level izolace (gVisor/Kata) — redundantní vůci stávající hypervisor hranici.
- Auditní log PTY sessionu (možný navazující feature, mimo tento scope).
- Monitoring/alerting na cage breach (navazující).

## Edge cases & otevréné otázky

- **Proxy advisory risk:** pokud by host omylem povolil odchozí HTTPS kamkoli (chyba
  konfigurace), AI proxy obejde. Mitigace: host-level pravidlo, že HTTPS jde jen na proxy
  CIDR — soucást host-enforced policy appliera, overeno v I2.
- **DNS/metadata side-channel:** blokování DNS dotazů jinam než na allowlisted resolver
  a blackhole cloud metadata endpointu musí být explicitne v host policy (zahrnuto v I1/I2);
  konkrétní adresy viz `contracts/containment-cage.md`.
- **Exfil pres git:** workspace credential scoped na 1 repo nestací, pokud appka dynamicky
  rotuje PAT — `[deferred]` (viz AC-I10 v acceptance).
- **Shadow build maintenance:** klec udržuje "stínový" workspace image; pri každé zmene
  workspace image definition v appce je potreba sync — model reší navazující fáze.
- **Regression po deploy:** invariant I7 (žádný verejný ingress) se musí re-testovat po každém
  deployi, protože konfigurace může být obnovena na výchozí hodnotu.

Konkrétní technologický stack (host-level enforcement implementace, proxy nástroj, firewall
backend) je zdokumentován v `stack/containment-cage.md`. Technický rozhraní kontrakt (env,
porty, secret jména) je v `contracts/containment-cage.md`.
