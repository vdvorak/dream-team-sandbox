# dream-team-sandbox — Project Constitution

> Projektová ústava (CO projekt je). Doplňuje universal `.agentic/constitution.md`
> (JAK agenti fungují). Změna = L3.

## Vize a mise

`dream-team-sandbox` je **out-of-band bezpečnostní klec (containment cage)**, do které
se při deploy zabalí nasazená `dream-team-app`. `dream-team-app` je platforma, která pouští
`claude` CLI uvnitř workspace-containeru jménem uživatelů (interaktivní PTY, git, spawn
subprocesů) — tahle agentická smyčka je **threat actor**. Klec ji zabrání škodit:
default-deny egress, allowlist jen explicitně, žádné SSH ven, žádná exfiltrace.

**Posture:** vše zakázáno, allowlist jen explicitně. Klec je **neprůhledná zevnitř** —
zaklecovaná AI o ní nesmí vědět, číst ji, ani ji obejít. Definice klece žije jen v tomhle
repu; do repa appky se nikdy nedostane.

## Cílová skupina

Vlastník/provozovatel `dream-team-app` — interní bezpečnostní infrastruktura. Není to
produkt pro koncové zákazníky.

## Co projekt JE / NENÍ

**JE:**
- Definice a applier bezpečnostní klece: Fly Network Policy, Smokescreen egress-proxy ACL,
  hardened workspace overlay, cage-deploy obálka.
- Overlay-at-deploy model — artefakty drží sandbox, přeloží přes kód appky při deploy.
- Substrát-agnostický design (Fly.io teď, vlastní VPS nftables later, stejný kontrakt).

**NENÍ:**
- Úprava business logiky `dream-team-app`.
- Dev-time sandbox (cílíme jen runtime/deploy klec).
- Garantované zabezpečení skrze pouhou opacitu (opacita ≠ záruka — nositelem je
  host-enforced firewall + chybějící `CAP_NET_ADMIN`).

## Hodnoty

- **Adversariální rigor:** předpokládej, že zaklecovaná AI se aktivně snaží uniknout.
- **Host-enforced garance:** primární vrstvy smí vynucovat jen entita mimo zaklecovaný
  proces (Fly control-plane, hypervisor host).
- **Opacita jako doplněk, ne základ:** pravidla nejsou čitelná zevnitř, ale reálnou
  garanci nesou invarianty 1/4/5, ne tajemství.
- **Minimální blast radius:** klec nesmí bránit legitimnímu provozu (GitHub API, CF Access).
- **Přenositelnost:** kontrakt musí být 1:1 přenositelný Fly → VPS bez přepisu logiky.

## Nefunkční požadavky (NFR) — Security Contract (Invarianty 1–11)

Toto jsou **acceptance criteria** klece. Gate PASS = všechny invarianty platí.

### Egress

**I1 — Default-deny egress na host-enforced vrstvě** (Fly Network Policy, ne in-VM).
Test: `curl https://example.com` i `nc -w3 1.1.1.1 22` selžou; SSH kamkoli selže.

**I2 — Doménový allowlist** jen `api.github.com:443`,
`<CF_ACCESS_TEAM_DOMAIN>/cdn-cgi/access/certs:443`, 6PN peers.
Test: `curl api.github.com` OK; `curl raw.githubusercontent.com` blokováno proxy.

**I3 — Build-time hosty nedosažitelné v runtime** (PyPI, npmjs, cloudflared releases,
gh apt).
Test: `pip install`/`npm i -g`/`apt update` v runtime selžou.

### Tamper-resistance

**I4 — Zaklecovaný proces nikdy nemá `CAP_NET_ADMIN`.**
Test: `capsh --print` bez `net_admin`; `nft list ruleset` → EPERM.

**I5 — Ruleset/policy nečitelný a neměnný zevnitř.**
Test: `nft flush` selže; Smokescreen ACL nečitelný; AI allowlist nevyjmenuje.

**I6 — `no_new_privs=1`, žádný setuid-root binář** dávající net config.

### Ingress / izolace

**I7 — Nula veřejného ingressu do workspace** (žádný `[http_service]`, žádné public IP;
jen 6PN z app).
Test: workspace `*.fly.dev` z internetu = connection refused.

**I8 — App↔AI oddělené microVM/hypervisor hranicí** (dvě Fly apps, dva kernely, žádný
sdílený volume/netns).

### Secrets

**I9 — High-value secrets nikdy v env/volume workspace** (`CLOUDFLARE_TUNNEL_TOKEN`,
`CF_ACCESS_AUD`, `GH_TOKEN`, `ADMIN_BOOTSTRAP_TOKEN`).
Test: `env` + `grep -r` přes volume = nic.

**I10 — `gh`/GitHub write credential jen v app**, nikdy injektnuté do workspace.

### Opacita

**I11 — Definice klece nedohledatelná zevnitř** — žádný firewall rule/seccomp/
hardened-init/deploy-wrapper z `dream-team-sandbox` není přítomen/čitelný ve workspace
FS ani env.

## Doménová security pravidla

- **Vrstva 2 (Network Policy) je load-bearing enforcer.** Granularita je port/protokol;
  sama o sobě garantuje jen `:443` deny-all mimo approved. Nikdy nespoléhej pouze na
  in-VM firewall — root v microVM má `CAP_NET_ADMIN` a smaže in-VM pravidla.
- **Proxy (Smokescreen) je advisory vrstva — granularita doménová/SNI.** Přímé spojení
  na `:443` obejde proxy, pokud host povolí `:443` kamkoli. Proto host pouští `:443`
  **jen na proxy/approved CIDR**.
- **De-root workspace je defense-in-depth.** Root-init nainstaluje in-VM nftables →
  drop `CAP_NET_ADMIN` z bounding setu + `no_new_privs` → exec agenta jako non-root.
  Pořadí je závazné.
- **gVisor/Kata se nepřidávají** — Fly Machine to neumožňuje a je to redundantní vůči
  hardware-VM hranici (dvě Fly apps = dva kernely).
- **Fly-proxy bypass:** `[http_service]` obchází Network Policy (fly-proxy traffic
  nepodléhá policy). Workspace musí být 6PN-only bez `[http_service]`.
- **Exfil přes povolené kanály** (git push na útočníkův GitHub): workspace credential
  musí být scoped na konkrétní repo (deploy key / fine-grained PAT na 1 repo).
- **DNS/metadata side-channel:** DNS jen přes allowlisted resolver (deny `:53` jinam
  na hostu); blackhole link-local/metadata (`169.254.0.0/16`) v host policy.

## Delivery topologie

### 3-vrstvý enforcement (přenositelný Fly → VPS)

```
claude  (NON-root, bez CAP_NET_ADMIN, no_new_privs)
  │  HTTP(S) přes $http_proxy=http://127.0.0.1:4750   (env injektnuté)
  ▼
[vrstva 1] Smokescreen  (in-VM sidecar, vlastní non-root uid)
           domain allowlist ──► api.github.com:443
                                <team>.cloudflareaccess.com:443
                                6PN peers
  │  veškerý egress z machine
  ▼
[vrstva 2] Fly Network Policy  (HOST-enforced, default-deny)
           allow tcp/443 jen na proxy/approved CIDR + 6PN
           DENY :22 a vše ostatní (untamperable z microVM)
  │
[vrstva 3] (budoucí VPS) = nftables na hypervisor hostu
           STEJNÝ kontrakt, jiný enforcer
```

**Dělba:** host-enforced vrstva nese garanci; proxy nese granularitu doménovou.

### Overlay-at-deploy model

Artefakty (`Dockerfile.workspace`, `entrypoint.sh`, Smokescreen ACL, Network Policy
applier) žijí v `dream-team-sandbox`. Cage-deploy build je **přeloží přes** kód appky
při deploy. Repo appky zůstane čisté — AI nevidí enforcement. Trade-off: udržuje se
"shadow build" workspace image (finální podobu rozhodne ted/heimdall u T2 gate).

### Substrát-agnostický kontrakt

Fly Network Policy applier (`POST /v1/apps/dream-team-workspace/network_policies`) a
Smokescreen ACL jsou navrženy tak, aby byly přenositelné 1:1 na VPS (nftables na
hypervisor hostu, stejný doménový allowlist). Změna substrátu = změna enforceru,
ne logiky klece.
