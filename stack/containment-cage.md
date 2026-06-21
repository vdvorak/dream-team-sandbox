---
feature-id: containment-cage
type: stack
---
# Stack — containment-cage

Technologické volby pro implementaci bezpečnostní klece. Spec (`specs/containment-cage.md`)
popisuje chování agnosticky; tento soubor zachycuje konkrétní nástroje a jejich zdůvodnění.

## Host-enforced síťová politika

- **Fly.io:** Fly Network Policy (6PN, default-deny egress). Na VPS substrátu: nftables na hypervisor hostu (1:1 přenositelná logika).
- **6PN:** privátní síť mezi app a workspace machine (Fly private networking).
- **Konfigurace:** `fly.workspace.toml` — `[http_service]` sekce musí být odstraněna.

## Egress proxy sidecar

- **Smokescreen** (Stripe open-source) — doménový/SNI CONNECT proxy.
- Port: `4750` (localhost, interní).
- ACL allowlist: `api.github.com`, `<CF_ACCESS_TEAM>.cloudflareaccess.com`.

## Hardened workspace overlay artefakty

- `Dockerfile.workspace` — hardened build (non-root, capability drop).
- `entrypoint.sh` — non-root init sekvence, `no_new_privs=1`, proxy env inject.
- Smokescreen ACL soubor.
- Network Policy applier skript (volá Fly API).

Tyto artefakty žijí výhradně v `dream-team-sandbox`; do workspace image se dostanou
přes cage-deploy, ne přes repo appky.

## In-VM defense-in-depth

- `nftables` jako sekundární firewall (po `CAP_NET_ADMIN` dropu z bounding setu).

## Proxy env injekt

- `$http_proxy=http://127.0.0.1:4750` — injektuje entrypoint klece před execem agenta.

## Extraction Candidates

> Sleduje opakovatelné patterny, které jsou dnes feature-local, ale mají potenciál stát se
> sdíleným modulem (per constitution §Reuse policy). Aktualizuje ted-architect při decision pass.

| pattern | stav | trigger pro extract-shared |
|---|---|---|
| **host-policy applier** (`ruleset H1–H7 → enforcer adapter`) | feature-local (cage) | při přidání druhého enforceru (VPS nftables na hypervisor hostu) → extract-shared modul s ruleset abstrakcí; Fly Network Policy a VPS nftables se stanou dvěma adaptéry nad stejným rulesetem. Substrát-agnostika (constitution §Přenositelnost) tento extract předpokládá. |
| **fail-closed deploy guard** (abort wrapper kolem každého enforcement kroku) | feature-local (cage-deploy) | pokud vznikne druhá deploy obálka se stejnou fail-closed sémantikou → extract. Dnes 1 výskyt = ponechat lokální. |

Pozn.: žádný extract teď neprovádět (1 substrát, 1 deploy cesta). Záznam je tracker pro fázi VPS.
