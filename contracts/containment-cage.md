---
feature-id: containment-cage
type: contract
architect: ted-architect
phase: T2
---
# Kontrakt — containment-cage (klec ↔ appka rozhraní)

Technický kontrakt definující rozhraní mezi bezpečnostní klecí (`dream-team-sandbox`) a
workspace aplikací (`dream-team-app`). Kontrakt SMÍ být konkrétní (tech názvy, porty, env) —
to je záměr, oddělené od agnostické spec.

> **Architektonická osa (závazná, neměnit bez L3):** *host-enforced vrstva nese GARANCI,
> proxy nese GRANULARITU, de-root je defense-in-depth.* Žádná vrstva nesmí být jediným
> nositelem garance. Vše **fail-closed**: nelze-li enforcement aplikovat → deploy se NEDOKONČÍ.

---

## 1. Tři vrstvy enforcementu — konkrétní tvar

### Vrstva 2 — Host-enforced default-deny egress (LOAD-BEARING garance)

Enforcer **mimo** zaklecovaný proces (Fly control-plane / hypervisor host). Guest root tuto
politiku **nepřečte ani nezmění** (mitiguje I4/I5). Granularita = směr/port/protokol/CIDR.

**Tvar pravidel** (substrát-agnostický model; konkrétní enforcer dle §3):

| # | směr | protokol/port | cíl (CIDR) | akce | invariant |
|---|------|---------------|------------|------|-----------|
| H1 | egress | tcp/443 | `PROXY_CIDR` (loopback/proxy sidecar) | ALLOW | I2 |
| H2 | egress | tcp/443 | `APPROVED_PRIVATE_CIDR` (6PN peers / privátní síť) | ALLOW | I2, I8 |
| H3 | egress | udp/53 + tcp/53 | `DNS_RESOLVER_IP/32` | ALLOW | I1e (spike-to-confirm §6) |
| H4 | egress | tcp/22 (SSH) | `*` | DENY | I1b, I1c |
| H5 | egress | any | `METADATA_CIDR` (link-local/metadata) | DROP (blackhole) | I1d |
| H6 | egress | any | `*` (vše ostatní, default) | DENY | I1a |
| H7 | ingress | any | `*` (žádný veřejný ingress) | DENY (jen privátní síť) | I7 |

- **Pořadí semantiky:** explicit ALLOW (H1–H3) → explicit DENY/DROP (H4–H5) → default-deny (H6–H7).
- **`PROXY_CIDR`** je loopback (`127.0.0.1/32`) pokud proxy běží in-VM jako sidecar — pak H1
  reálně reguluje, že proxy proces (vlastní non-root uid) smí ven; viz §1 proxy.
- **6PN-only:** H7 = workspace nemá public IP ani fly-proxy ingress (viz §3 mapping). To je
  podmínka vynutitelnosti H1–H6: `[http_service]` traffic obchází host policy (viz `rules/cage-enforcement.md §FP-1`).

### Vrstva 1 — Doménový egress proxy (GRANULARITA, advisory)

In-VM sidecar (Smokescreen) na `127.0.0.1:4750`, vlastní non-root uid. SNI/CONNECT doménový
allowlist. **Advisory** — sama o sobě obejitelná přímým spojením; garanci nese H1 (host pustí
:443 jen na proxy).

**Jak se route přes proxy VYNUTÍ (dvojitý zámek):**
1. **Env injekt** (entrypoint klece, před exec agenta): `http_proxy` / `https_proxy` / `HTTP_PROXY`
   / `HTTPS_PROXY` = `http://127.0.0.1:4750`. To je "měkký" mechanismus (klient ho může ignorovat).
2. **Host pravidlo H1** = "tvrdý" zámek: přímé tcp/443 mimo `PROXY_CIDR`/`APPROVED_PRIVATE_CIDR`
   skončí na vrstvě 2 (DENY). Proto i agent, který env ignoruje a connectne přímo, neprojde.

**ACL formát** (žije jen v `dream-team-sandbox`, nikdy ve workspace FS — I5/I11):
```yaml
# smokescreen-acl.yaml — šablona; CF doména injektnuta z env při deploy (rozhodnutí (d))
version: 1
default: deny
allow:
  - domain: api.github.com                              # I2: 2a PASS
  - domain: "${CF_ACCESS_TEAM_DOMAIN}.cloudflareaccess.com"   # I2: 2c PASS; šablonováno z env
# raw.githubusercontent.com, PyPI, npmjs, apt = NENÍ v allow → deny (I2: 2b, I3)
```
- **`CF_ACCESS_TEAM_DOMAIN`** se NEHARDCODUJE — injektuje se při deploy z env (rozhodnutí (d)),
  ACL je render-time šablona. Vyrenderovaný ACL existuje jen v runtime proxy procesu, ne na FS
  čitelném agentem (proxy běží pod jiným uid; ACL soubor mode `0400 root:root` nebo v proxy-only
  namespace) → I5a/I5b.
- Proxy management/introspekční endpoint NESMÍ být dostupný z agentova kontextu → I5c (bind jen
  na loopback, management off / 404).

### Vrstva 3 — In-VM firewall (DEFENSE-IN-DEPTH, ne primární)

`nftables` default-DROP uvnitř microVM. **Sekundární** — instaluje root PŘED de-root, pak se stane
neměnným (agent nemá `CAP_NET_ADMIN` → `nft flush` → EPERM, I4b/I4c). Nikdy jediný nositel garance.

### De-root workspace init sekvence (ZÁVAZNÉ pořadí)

Entrypoint klece (`entrypoint.sh` overlay) běží jako root a provede **přesně** toto pořadí:

```
[krok 0] (root) přípravy: symlink Claude login persistence (viz regrese níže), git safe.directory,
         render proxy env, start Smokescreen sidecar pod dedikovaným non-root uid.
[krok 1] (root) nainstaluje in-VM nftables default-DROP ruleset (vrstva 3).        # potřebuje CAP_NET_ADMIN
[krok 2] (root) DROP CAP_NET_ADMIN (a příbuzné net-mgmt caps) z BOUNDING setu.     # I4a
[krok 3] (root) nastaví no_new_privs=1.                                            # I6a
[krok 4] exec workspace agent jako NON-root uid (setuid/setgid na non-root).       # I6, root nikdy nedědí agent
```

- **Pořadí je závazné** (per PROJECT-CONSTITUTION §Doménová security pravidla): nftables MUSÍ být
  nainstaleno PŘED dropem `CAP_NET_ADMIN`, jinak by ho nešlo nainstalovat; `no_new_privs` až po
  capability dropu, ale PŘED exec agenta.
- **Drop CAP_NET_ADMIN z bounding setu** (ne jen z effective): zaručí, že žádný potomek (ani přes
  setuid binár) cap znovu nezíská → I4a, společně s `no_new_privs` (I6a) a auditem setuid binárů (I6b).

#### REGRESE-GUARD: Claude login token persistence vs no_new_privs (rozhodnutí (1), pozor)

Současný `entrypoint.sh` appky dělá `ln -s /data/claude-config /root/.claude` a `claude` běží
jako root. Po de-root agent běží jako **non-root uid** (např. `claude:claude`, uid 10001) →

- **Login persistence cesta se mění** z `/root/.claude` na `$HOME` non-root usera (např.
  `/home/claude/.claude`); symlink na perzistentní volume subdir musí směřovat tam a být
  **vlastněn non-root uid** (volume subdir `chown claude:claude`). Jinak `claude /login` token
  neuloží → regrese (po restartu vyžaduje re-login).
- **`no_new_privs=1` NESMÍ rozbít zápis tokenu:** `no_new_privs` blokuje jen privilege *escalation*
  (setuid/setgid/file caps), NIKOLI normální zápis souboru pod vlastním uid. Token persistence je
  prostý write do `$HOME/.claude` — **funguje i s `no_new_privs`**. Riziko je jen vlastnictví
  cesty (viz výše), ne `no_new_privs`. Kontrakt to fixuje: volume subdir pre-chown na agent uid
  v kroku 0, symlink relativní k `$HOME`.
- **Verifikace regrese:** po deploy `claude /login` → token zapsán do volume → restart machine →
  login přežil (manuální/poloautomatický check; alfred zařadí do post-deploy smoke).

---

## 2. Overlay-at-deploy build model

Hardened overlay artefakty žijí výhradně v `dream-team-sandbox`. Cage-deploy je **přeloží přes**
kód appky při deploy, BEZ zápisu do repa appky (I11).

### Overlay mapping (co cage-deploy nahrazuje/přidává)

| artefakt appky (původní) | overlay z `dream-team-sandbox` | mechanismus |
|---|---|---|
| `Dockerfile.workspace` (naivní, root, EXPOSE 8081) | `overlay/Dockerfile.workspace` (Smokescreen binár, non-root user `claude`, build/runtime split) | build-context substituce (viz níže) |
| `poc/workspace-container/entrypoint.sh` | `overlay/entrypoint.sh` (de-root sekvence §1) | COPY v overlay Dockerfile |
| — (neexistuje) | `overlay/smokescreen-acl.yaml` (render z env) | injekt při deploy; NEcopy do image čitelně |
| `fly.workspace.toml` (má `[http_service]`) | `overlay/fly.workspace.toml` (BEZ `[http_service]`, 6PN-only) | deploy s overlay config souborem (`fly deploy -c`) |
| `poc/workspace-container/agent.py` | **beze změny** (jen běží pod non-root) | re-use as-is |
| `managed-settings.json`, `deny-secrets.sh` | **beze změny** (re-use, viz §5) | re-use as-is |

**Build mechanismus (substrát-agnostický princip):** cage-deploy provádí build z **kombinovaného
build kontextu** = repo appky (zdroj `agent.py`, `managed-settings.json`, `deny-secrets.sh`) +
overlay adresář sandboxu (hardened Dockerfile/entrypoint/ACL). Overlay Dockerfile referencuje
appkové soubory přes build-context, hardened soubory přes overlay-context. Repo appky se NEMODIFIKUJE
(žádný `git write` do appky — overlay je read-only čtený, výstup je image). Toto je čistě
build-time operace; výsledek je workspace image, kterou cage-deploy nasadí.

### Drift-detekce (rozhodnutí (a)) — fail-closed, viditelná

Cage-deploy je **JEDINÁ legitimní cesta** nasazení `dream-team-workspace` (přímý `fly deploy`
workspace je zakázán provozní disciplínou — nevynutitelné kódem, ale dokumentované v `rules/`).

```
WORKSPACE_DEF_HASH = sha256( appkové soubory, na které overlay sedí )
                   = hash( Dockerfile.workspace-base-vrstva ∪ agent.py ∪ managed-settings.json
                           ∪ deny-secrets.sh ∪ fly.workspace.toml struktura )
```

- Cage-deploy si při úspěšném nasazení **uloží `WORKSPACE_DEF_HASH`** (pinned, např.
  `cage-deploy.lock` v sandboxu).
- Při dalším deploy znovu spočítá hash z aktuálních appkových souborů.
- **Neshoda → deploy FAILne** s explicitním upozorněním (`ERR_CAGE_DRIFT`, viz error-codes):
  "Workspace image definice appky se změnila od posledního cage-deploy (drift) — overlay nemusí
  sedět. Re-review overlay vůči nové definici, pak `--accept-drift` (re-pin hash)." **Viditelná
  drift detekce, NE tichý sync.** Operátor vědomě re-pinuje.
- **Fail-closed:** drift bez explicitního re-pinu = deploy se NEDOKONČÍ.

---

## 3. cage ↔ app kontrakt (rozhraní + garance)

### Co cage-deploy OČEKÁVÁ od appky (vstupní rozhraní)

- Workspace agent (`agent.py`) běží jako foreground proces, který lze spustit pod **non-root uid**
  (žádná hard závislost na root — ověřeno: agent.py nepotřebuje root, jen bind na :8081 < 1024? NE,
  8081 > 1024 → non-root bind OK).
- Workspace image build context obsahuje `agent.py`, `managed-settings.json`, `deny-secrets.sh` na
  známých cestách (`poc/workspace-container/`).
- App machine drží VŠECHNY high-value secrets (`GH_TOKEN`, `CLOUDFLARE_TUNNEL_TOKEN`, `CF_ACCESS_AUD`,
  `ADMIN_BOOTSTRAP_TOKEN`) a NIKDY je nepředává workspace machine (I9 — už drží dnes, kontrakt to fixuje).
- Komunikace app→workspace výhradně přes privátní síť (`dream-team-workspace.internal:8081`, 6PN).

### Co cage-deploy GARANTUJE appce (výstupní garance)

- Workspace nasazen jako samostatná microVM (I8), 6PN-only, bez `[http_service]` (I7).
- Workspace agent běží non-root, bez `CAP_NET_ADMIN`, `no_new_privs=1` (I4/I6).
- Veškerý egress přes 3-vrstvý enforcement (I1/I2/I3).
- Appkové repo nemodifikováno (I11) — appka zůstane čistá, AI nevidí enforcement.
- **Git write model (rozhodnutí (b)):** workspace NIKDY nedostane git write credential. I10 se
  reinterpretuje jako silnější invariant: **"žádný git write credential ve workspace, nikdy."**
  Push deleguje app machine přes server-side `gh` (app drží `GH_TOKEN`). Workspace umí jen clone/fetch
  read (přes proxy na `api.github.com`) nebo dostane read-only/scoped credential, NIKDY write.
  I10-D (rotace PAT) zůstává `[deferred]` — kontrakt scoping/rotaci PAT NENAVRHUJE.

### Substrát-agnostický bod přenosu (Fly → VPS)

**Jediný bod, kde se mění enforcer, NE logika:** vrstva 2 (host-enforced policy applier).

| substrát | vrstva 2 enforcer | applier kontrakt |
|---|---|---|
| Fly.io (dnes) | Fly Network Policy (control-plane) | `POST /v1/apps/dream-team-workspace/network_policies` s ruleset H1–H7 |
| VPS (později) | nftables na hypervisor hostu | render H1–H7 do nft ruleset, apply na host (mimo guest) |

- **Stejný vstup** = abstraktní ruleset H1–H7 (§1). Applier je adaptér: `ruleset → enforcer-specific call`.
- Vrstva 1 (Smokescreen ACL) a vrstva 3 (in-VM nftables) jsou **identické** na obou substrátech.
- Přenositelnost = výměna jen "host applier" modulu. Logika klece (allowlist, pořadí, fail-closed)
  beze změny. → naplňuje PROJECT-CONSTITUTION §Přenositelnost.

---

## 4. Error / edge handling — fail-closed všude

| situace | chování | error code | invariant důsledek |
|---|---|---|---|
| Host-enforced policy API (vrstva 2) selže při apply | **deploy ABORT**, žádné nasazení workspace bez aktivní policy | `ERR_POLICY_APPLY_FAILED` | I1 (bez policy = žádná garance) |
| Deploy bez platné/kompletní policy (chybí ruleset H1–H7) | **deploy ABORT** před spuštěním machine | `ERR_NO_POLICY` | I1 |
| Drift detekován (rozhodnutí (a)) | **deploy FAIL** + viditelné upozornění, vyžaduje `--accept-drift` re-pin | `ERR_CAGE_DRIFT` | I11 (overlay nemusí sedět) |
| Proxy (Smokescreen) spadne za runtime | **fail-CLOSED**: H1 pustí :443 jen na proxy → mrtvá proxy = žádný egress (ne fallback na přímý ven). Workspace ztratí GitHub/CF, ALE neunikne. | `ERR_PROXY_DOWN` (observability) | I2 (radši deny než bypass) |
| In-VM nftables (vrstva 3) selže při instalaci v kroku 1 | **entrypoint ABORT** před de-root → machine se nespustí jako klec | `ERR_INVM_FW_FAILED` | I4 (sekundární vrstva chybí) |
| Capability drop (krok 2) selže | **entrypoint ABORT**, NIKDY neexec agenta s root/CAP_NET_ADMIN | `ERR_CAP_DROP_FAILED` | I4 (kritické) |
| `[http_service]` znovu objeven v overlay config (regrese I7) | **deploy ABORT** (pre-deploy lint na overlay `fly.workspace.toml`) | `ERR_INGRESS_LEAK` | I7 (re-test po každém deploy) |
| Secret nalezen v workspace env/volume při pre-deploy scan | **deploy ABORT** | `ERR_SECRET_LEAK` | I9 |
| Git write credential nalezen ve workspace (regrese rozhodnutí (b)) | **deploy ABORT** | `ERR_GIT_WRITE_CRED` | I10 |

**Princip fail-closed (závazný):** kdykoli enforcement NELZE aplikovat nebo ověřit → deploy se NESMÍ
dokončit / runtime fallbackuje na DENY, NIKDY na "pust to ven". Žádný "best-effort" egress.

---

## 5. Reuse decision pass (per constitution §Reuse policy)

| pattern | klasifikace | reuse decision | zdůvodnění |
|---|---|---|---|
| `managed-settings.json` (Claude deny perms) | server-side guard | **reuse-existing** | už vynucuje I9 vrstvu (deny `Read(.env/.pem/...)`); funguje as-is pod non-root |
| `deny-secrets.sh` (PreToolUse hook) | server-side guard | **reuse-existing** | záložní secret-read guard; přebírá se beze změny do overlay image |
| `fly.toml` (app) vzor bez `[http_service]` | deploy config pattern | **reuse-existing (jako vzor)** | app `fly.toml` JIŽ je 6PN-only bez `[http_service]` — overlay `fly.workspace.toml` kopíruje tento osvědčený vzor (zavře I7 díru) |
| `agent.py` | server proces | **reuse-existing** | běží non-root beze změny; bind :8081 (>1024) OK; jen kontext spuštění se mění |
| `entrypoint.sh` (appky) | init sekvence | **feature-local (nahradit overlayem)** | naivní (root, ln /root/.claude); cage dodá hardened verzi s de-root sekvencí §1 |
| `Dockerfile.workspace` | build def | **feature-local (nahradit overlayem)** | naivní (root, EXPOSE, bez proxy); cage dodá hardened |
| Smokescreen egress proxy | egress sidecar | **scaffold-only (nový artefakt)** | nový, žije v sandboxu; ACL šablonovaný |
| Host-enforced policy applier | deploy tooling | **scaffold-only (nový artefakt)** | nový; substrát-agnostický adaptér (§3) |
| cage-deploy obálka + drift-lock | deploy tooling | **scaffold-only (nový artefakt)** | nový; jediná legitimní deploy cesta (a) |

**Extraction candidate:** "host-enforced policy applier (ruleset H1–H7 → enforcer adapter)" je
kandidát na sdílený modul (Fly + VPS implementace sdílí ruleset abstrakci). Dnes feature-local
v cage; při přidání VPS enforceru = extract-shared. Viz `stack/containment-cage.md §Extraction Candidates`.

---

## 6. Sekvencování implementace pro alfred + diagnostika domén vad

### Pořadí implementace (alfred-devops)

1. **Overlay artefakty v sandboxu** (autorské): `overlay/Dockerfile.workspace`, `overlay/entrypoint.sh`
   (de-root sekvence §1), `overlay/smokescreen-acl.yaml` (šablona), `overlay/fly.workspace.toml`
   (bez `[http_service]`).
2. **Host-enforced policy applier** (ruleset H1–H7 → Fly Network Policy API call); substrát-agnostický
   adaptér (§3). Fail-closed (§4).
3. **Smokescreen sidecar integrace** v overlay Dockerfile + entrypoint (non-root uid, loopback bind,
   management off).
4. **cage-deploy obálka**: kombinovaný build context (§2) → drift-detekce (§2, `cage-deploy.lock`) →
   apply host policy (krok 2) → deploy workspace s overlay config. Fail-closed na každém kroku (§4).
5. **Pre-deploy lint/scan**: `[http_service]` leak (I7), secret leak (I9), git-write-cred (I10).
6. **Post-deploy smoke**: Claude login persistence regrese-guard (§1), acceptance subset.

### Diagnostika domén vad (`fault` mapování pro re-flow)

Když přijde funkční selhání (failure signature od joey/optimus/heimdall), mapuj příznak → doménu:

| failure signature | doména (`fault`) | proč |
|---|---|---|
| Egress projde tam, kam nemá (I1/I2 FAIL); :443 přímo ven funguje | `server-logic` (applier/ruleset) | host ruleset H1/H6 chybný nebo policy neaplikovaná → applier/cage-deploy logika |
| `nft flush` projde / `CAP_NET_ADMIN` přítomen (I4 FAIL) | `server-logic` (entrypoint de-root sekvence) | pořadí kroků §1 porušeno nebo cap drop selhal tiše |
| `no_new_privs: 0` (I6 FAIL) | `server-logic` (entrypoint krok 3) | krok 3 neproveden před exec |
| ACL/policy čitelná zevnitř (I5/I11 FAIL) | `server-logic` (overlay perms / ACL placement) | ACL soubor s špatným uid/mode nebo zkopírovaný do image |
| `[http_service]` stále present, workspace veřejně dosažitelný (I7 FAIL) | `server-logic` (overlay fly config) NEBO `spec` pokud nejasné | overlay `fly.workspace.toml` špatný |
| Drift se neodhalil / tichý sync místo FAIL | `server-logic` (cage-deploy drift logika) | drift-detekce nedrží fail-closed |
| Secret leaknut do workspace (I9 FAIL) | `server-logic` (deploy scan) NEBO appka předala secret | ověř řetěz: kdo secret injektnul |
| Claude login persistence rozbita po de-root | `server-logic` (entrypoint regrese-guard §1) | symlink/chown na non-root $HOME chybný |
| AC test sám je vágní / netestovatelný | `spec` | acceptance kritérium nejde pozorovat |
| Kontrakt (tento dokument) má chybu — špatný ruleset tvar, špatné error code, chybný overlay mapping | **(moje doména)** — re-emit kontraktu, NE `fault` | architektonická vada = opravím sám |

- `db-schema` = **N/A** (projekt nemá DB; `touches_db: false`). Žádná vada se sem nemapuje.
- `fault: contract` NENÍ routovací — kontraktovou vadu opravuji sám (re-emit), pošlu `PASS` dopředu.

---

## 7. Otevřené body pro heimdall spike (spike-to-confirm, rozhodnutí (c))

Architektura tyto předpokládá; heimdall ověří reálné hodnoty, NE strukturu pravidel:

- **`DNS_RESOLVER_IP` (H3):** předpoklad = Fly interní resolver (`fdaa::3` / `169.254.x` interní);
  heimdall potvrdí konkrétní IP a zda DNS jde tcp i udp.
- **`METADATA_CIDR` (H5):** předpoklad = blackhole link-local/metadata rozsah (`169.254.0.0/16`);
  heimdall potvrdí, zda Fly metadata používá jiný rozsah.
- **Fly Network Policy API tvar** (`network_policies` endpoint): potvrdit, že podporuje per-port/CIDR
  egress rules H1–H7 (zejm. že umí ALLOW jen na proxy/approved CIDR a default-deny).
- **Capability drop v Fly microVM:** potvrdit, že lze dropnout `CAP_NET_ADMIN` z bounding setu po
  instalaci nftables (kernel/init podpora).

Hodnoty se dosadí do ruleset H1–H7 jako parametry; struktura pravidel se NEMĚNÍ.
