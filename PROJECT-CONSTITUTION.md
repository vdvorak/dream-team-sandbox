# dream-team-sandbox — Project Constitution

> Projektová ústava (CO projekt je). Doplňuje universal `.agentic/constitution.md`
> (JAK agenti fungují). Změna = L3.

## North Star — JEDEN systém ze TŘÍ repů

Tři samostatné vrstvy, každá s jasnou identitou a hranicí:

**FRAMEWORK (`dream-team`)** — definuje CO se dělá: orchestrace, agenti, pravidla, engine core.
Neutrální. Neví, na čem běží ani kdo ho používá.

**RUNTIME/SANDBOX (`dream-team-sandbox` = TENHLE repo)** — definuje KDE a JAK AI bezpečně
běží. Dvě podsložky:
- **MOTOR:** container image, agent uvnitř, lifecycle (start / uspi / najdi / zruš),
  klonování repa, připojení PTY terminálu, čtení souborů.
- **ZEĎ:** default-deny allowlist, git brána (vratné/nevratné), věci mimo dosah AI.

„Na čem běží" (Fly / AWS / Docker / vlastní server) = výhradně starost tohoto repa.
Použitelný i bez aplikace — standalone.

**APLIKACE (`dream-team-app`)** — řídící a zobrazovací vrstva: UI, výběr projektu, dispatch,
schvalování u gates, živý stav. ODBĚRATEL frameworku a runtime. Mluví jen přes kontrakt.

### Železná pravidla hranic

- App se **nikdy** nedívá runtimu dovnitř — zná jen kontrakt.
- Runtime **nezná** aplikaci — vystavuje jen kontrakt, jede i bez ní.
- Framework neví o runtime ani o cloudu.
- „Na čem běží" = výhradně runtime → app je cloud-agnostic automaticky.
- AI běží na tokenech uživatele (BYOK); app je řídící, ne počítací vrstva.
- Soubory = jediný zdroj pravdy per projekt; DB = jen globální index / cache.
- Kontrakt na hranici app↔runtime je společně vlastněný a stabilní; změna = koordinovaný L3
  ve více repech.

---

## Identita TOHOTO repa

**JE:**
- Runtime prostředí pro AI = MOTOR + ZEĎ + vše „na čem běží".
- Vystavuje stabilní kontrakt konzumovaný aplikací (detail viz `contracts/runtime-contract.md`,
  vznikne v navazující wave).
- Použitelný standalone bez aplikace (curl / CLI drive přes kontrakt).

**NENÍ:**
- Žádná znalost konkrétní appky.
- Žádné UI, dispatch, produktová data.
- Žádné flow ani agenti frameworku.

**Vnitřní dělba (drž oddělené):**
- **ZEĎ** — enforcement: co AI smí/nesmí, jak se vynucuje, garance invariantů.
- **MOTOR** — lifecycle a běh: image, agent, start/stop, clone, PTY, file-read.

**Opacita platí vůči zaklecované AI uvnitř** (workspace AI) — ta nezná kontrakt ani ZEĎ,
nesmí je číst ani obejít. Aplikace zná kontrakt (ne vnitřek); zaklecovaná AI nezná ani jedno.

---

## ZEĎ — enforcement spec

### Nefunkční požadavky (Invarianty I1–I11)

Toto jsou **acceptance criteria** ZDI. Gate PASS = všechny invarianty platí.
Zaklecovaná AI nesmí žádný z nich přečíst ani obejít.

#### Egress

**I1 — Default-deny egress na host-enforced vrstvě** (Fly Network Policy, ne in-VM).
Test: `curl https://example.com` i `nc -w3 1.1.1.1 22` selžou; SSH kamkoli selže.

**I2 — Doménový allowlist** jen `api.github.com:443`,
`<CF_ACCESS_TEAM_DOMAIN>/cdn-cgi/access/certs:443`, 6PN peers.
Test: `curl api.github.com` OK; `curl raw.githubusercontent.com` blokováno proxy.

**I3 — Build-time hosty nedosažitelné v runtime** (PyPI, npmjs, cloudflared releases, gh apt).
Test: `pip install` / `npm i -g` / `apt update` v runtime selžou.

#### Tamper-resistance

**I4 — Zaklecovaný proces nikdy nemá `CAP_NET_ADMIN`.**
Test: `capsh --print` bez `net_admin`; `nft list ruleset` → EPERM.

**I5 — Ruleset / policy nečitelný a neměnný zevnitř.**
Test: `nft flush` selže; Smokescreen ACL nečitelný; AI allowlist nevyjmenuje.

**I6 — `no_new_privs=1`, žádný setuid-root binár** dávající net config.

#### Ingress / izolace

**I7 — Nula veřejného ingressu do workspace** (žádný `[http_service]`, žádné public IP;
jen 6PN z app).
Test: workspace `*.fly.dev` z internetu = connection refused.

**I8 — App↔AI oddělené microVM / hypervisor hranicí** (dvě Fly apps, dva kernely, žádný
sdílený volume / netns).

#### Secrets

**I9 — High-value secrets nikdy v env / volume workspace** (`CLOUDFLARE_TUNNEL_TOKEN`,
`CF_ACCESS_AUD`, `GH_TOKEN`, `ADMIN_BOOTSTRAP_TOKEN`).
Test: `env` + `grep -r` přes volume = nic.

**I10 — `gh` / GitHub write credential jen v app**, nikdy injektnuté do workspace.

#### Opacita

**I11 — Definice ZDI nedohledatelná zevnitř** — žádný firewall rule / seccomp /
hardened-init / deploy-wrapper z `dream-team-sandbox` není přítomen ani čitelný ve workspace
FS ani env.

### Doménová security pravidla

- **Vrstva 2 (Network Policy) je load-bearing enforcer.** Granularita je port / protokol;
  sama o sobě garantuje jen `:443` deny-all mimo approved. Nikdy nespoléhej pouze na
  in-VM firewall — root v microVM má `CAP_NET_ADMIN` a smaže in-VM pravidla.
- **Proxy (Smokescreen) je advisory vrstva — granularita doménová / SNI.** Přímé spojení
  na `:443` obejde proxy, pokud host povolí `:443` kamkoli. Proto host pouští `:443`
  jen na proxy / approved CIDR.
- **De-root workspace je defense-in-depth.** Root-init nainstaluje in-VM nftables →
  drop `CAP_NET_ADMIN` z bounding setu + `no_new_privs` → exec agenta jako non-root.
  Pořadí je závazné.
- **gVisor / Kata se nepřidávají** — Fly Machine to neumožňuje a je to redundantní vůči
  hardware-VM hranici (dvě Fly apps = dva kernely).
- **Fly-proxy bypass:** `[http_service]` obchází Network Policy (fly-proxy traffic
  nepodléhá policy). Workspace musí být 6PN-only bez `[http_service]`.
- **Exfil přes povolené kanály** (git push na útočníkův GitHub): workspace credential
  musí být scoped na konkrétní repo (deploy key / fine-grained PAT na 1 repo).
- **DNS / metadata side-channel:** DNS jen přes allowlisted resolver (deny `:53` jinam
  na hostu); blackhole link-local / metadata (`169.254.0.0/16`) v host policy.

### Delivery topologie ZDI

#### 3-vrstvý enforcement (přenositelný Fly → VPS)

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

#### Overlay-at-deploy model

Artefakty (`Dockerfile.workspace`, `entrypoint.sh`, Smokescreen ACL, Network Policy
applier) žijí v `dream-team-sandbox`. Cage-deploy build je přeloží přes kód appky
při deploy. Repo appky zůstane čisté — AI nevidí enforcement.

#### Substrát-agnostický kontrakt ZDI

Fly Network Policy applier a Smokescreen ACL jsou navrženy tak, aby byly přenositelné
1:1 na VPS (nftables na hypervisor hostu, stejný doménový allowlist). Změna substrátu =
změna enforceru, ne logiky ZDI.

---

## MOTOR — náčrt schopností

MOTOR zajišťuje runtime životní cyklus AI agenta. Schopnosti:

- **Image:** verzovaný base image (hardened, non-root, cage-ready).
- **Agent:** Claude CLI uvnitř kontejneru, lifecycle-managed.
- **Lifecycle:** start / uspi / najdi / zruš prostředí per projekt.
- **Clone:** naklonování / sync repa projektu do workspace.
- **PTY / terminál:** připojení obousměrného terminálu (binární PTY stream).
- **File-read:** čtení souborů z workspace pro řídící vrstvu.

Detail schopností, stavový automat a transport jsou specifikovány v kontraktu
(`contracts/runtime-contract.md`) — ten vznikne v navazující wave. Watson ho nepíše.

---

## Kontrakt app↔runtime

Runtime vystavuje stabilní kontrakt konzumovaný aplikací. Kontrakt fyzicky žije
v `dream-team-sandbox/contracts/`; do `dream-team-app` se vendoruje / submoduluje
read-only. Aplikace mluví výhradně přes tento kontrakt — nikdy se nedívá runtimu dovnitř.

Klíčová garance: **runtime NIKDY nevrátí `ready` bez aktivní ZDI** (fail-closed →
provisioning fail / `ERR_RUNTIME_UNAVAILABLE`). ZEĎ je vlastnost prostředí, ne parametr —
kontrakt nemá žádnou operaci ani pole, které by ZDI zmírňovalo.

Změna kontraktu = koordinovaný L3 ve více repech. Non-breaking rozšíření (přidání optional
pole / operace / error kódu) = bez koordinace. Breaking = MAJOR verze, obě strany se
koordinují před nasazením.

Detail (`contracts/runtime-contract.md`, `contracts/api/runtime.openapi.yaml`) vznikne
v navazující wave (vision-po → ted-architect → heimdall-security → sheldon-spec).

---

## Hodnoty

- **Adversariální rigor:** předpokládej, že zaklecovaná AI se aktivně snaží uniknout.
- **Host-enforced garance:** primární vrstvy smí vynucovat jen entita mimo zaklecovaný
  proces (Fly control-plane, hypervisor host).
- **Opacita jako doplněk, ne základ:** pravidla nejsou čitelná zevnitř, ale reálnou
  garanci nesou invarianty I1 / I4 / I5, ne tajemství.
- **Minimální blast radius:** ZEĎ nesmí bránit legitimnímu provozu (GitHub API, CF Access).
- **Přenositelnost:** kontrakt musí být 1:1 přenositelný Fly → VPS bez přepisu logiky.
- **Standalone-first:** runtime funguje bez aplikace; kontrakt je curl-ovatelný.
- **Fail-closed everywhere:** nelze-li enforcement aplikovat → runtime nic nespustí.
