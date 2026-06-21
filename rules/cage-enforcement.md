---
type: rules
layer: cage-enforcement
owner: ted-architect
normative: true
---
# Rules — cage enforcement (normativa klece)

Tech-agnostická architektonická pravidla klece. Normativní (MUST/MUST NOT). Doplňují
PROJECT-CONSTITUTION §Doménová security pravidla; tady jsou vynucovací invarianty pro
implementaci (alfred) a diagnostiku (ted/heimdall/joey).

## CE-1 — Dělba garance (load-bearing)

- **MUST:** host-enforced vrstva (vrstva 2) je JEDINÝ nositel egress garance. Proxy a in-VM
  firewall jsou doplňky.
- **MUST NOT:** spoléhat na in-VM firewall jako primární enforcer (root v guestu ho smaže,
  dokud nemá dropnutý `CAP_NET_ADMIN`).
- **MUST:** host pustí `:443` jen na proxy/approved CIDR (H1/H2), takže přímé spojení mimo proxy
  umře na hostu i bez doménové kontroly.

## CE-2 — Fail-closed (univerzální)

- **MUST:** nelze-li enforcement aplikovat NEBO ověřit → deploy se NEDOKONČÍ; runtime fallback = DENY.
- **MUST NOT:** žádný "best-effort" nebo "pust to ven, když nejde policy" fallback. Žádný silent sync.
- **MUST:** každá selhávací větev má error code (`contracts/error-codes.md`) a aborts.

## CE-3 — De-root sekvence (závazné pořadí)

- **MUST** přesné pořadí: (1) root instaluje in-VM nftables → (2) drop `CAP_NET_ADMIN` z **bounding**
  setu → (3) `no_new_privs=1` → (4) exec agenta jako non-root.
- **MUST NOT:** spustit agenta jako root; ponechat `CAP_NET_ADMIN` v effective/bounding setu agenta.
- **MUST:** drop z bounding setu (ne jen effective) — zabrání re-gain přes setuid.
- **REGRESE-GUARD:** `no_new_privs` NESMÍ rozbít Claude login persistence. `no_new_privs` blokuje
  jen privilege escalation (setuid/file caps), NE běžný write pod vlastním uid. Token persistence =
  write do `$HOME/.claude` → funguje. **MUST:** volume subdir pro login pre-chown na agent non-root
  uid; symlink relativní k `$HOME` non-root usera (NE `/root/.claude`).

## CE-4 — Opacita je doplněk, ne základ

- **MUST:** reálnou garanci nesou invarianty I1/I4/I5 (host enforcement + chybějící cap), NE utajení.
- **MUST NOT:** žádný cage artefakt (firewall rule, ACL, hardened-init, deploy-wrapper, cage verze/repo
  reference) přítomen ani čitelný ve workspace FS nebo env (I5/I11). Smokescreen ACL existuje jen
  v runtime proxy procesu pod jiným uid (mode `0400`), NE jako čitelný soubor v image.

## CE-5 — Overlay-at-deploy (čistota repa appky)

- **MUST:** hardened overlay artefakty žijí výhradně v `dream-team-sandbox`.
- **MUST NOT:** zapsat overlay do repa appky (žádný git write do appky; overlay se čte read-only,
  výstup je image).
- **MUST:** cage-deploy je JEDINÁ legitimní cesta nasazení `dream-team-workspace` (rozhodnutí (a)).
  Přímý `fly deploy` workspace je provozně zakázán.

## CE-6 — Drift detekce (viditelná, fail-closed)

- **MUST:** cage-deploy drží `WORKSPACE_DEF_HASH` appkové workspace definice, na kterou byl overlay
  aplikován. Neshoda → deploy FAIL (`ERR_CAGE_DRIFT`) + viditelné upozornění.
- **MUST NOT:** tichý auto-sync overlay na novou definici. Operátor vědomě re-pinuje (`--accept-drift`).

## CE-7 — Git write model (silnější I10, rozhodnutí (b))

- **MUST:** workspace NIKDY nedostane git write credential. Žádný `gh` s write tokenem ve workspace.
- **MUST:** push deleguje app machine přes server-side `gh` (app drží `GH_TOKEN`).
- **DEFERRED:** I10-D (dynamická rotace PAT) — NEnavrhovat scoping/rotaci PAT v této fázi.

## CE-8 — Ingress / izolace (vynutitelnost host policy)

- **MUST NOT:** `[http_service]` v workspace deploy config — obchází host-enforced policy (fly-proxy
  traffic nepodléhá Network Policy). Workspace MUSÍ být privátní-síť-only bez public IP (I7).
- **MUST:** re-test I7 po každém deploy (regression guard — konfigurace se může obnovit na default).
- **FP-1 (fly-proxy bypass):** `[http_service]` = fly-proxy ingress, který obchází vrstvu 2 →
  pre-deploy lint MUSÍ FAILnout (`ERR_INGRESS_LEAK`), pokud je přítomen.

## CE-9 — Substrát-agnostika (přenositelnost Fly → VPS)

- **MUST:** vrstva 2 enforcer je jediný měněný bod při změně substrátu. Logika klece (ruleset H1–H7,
  ACL, pořadí, fail-closed) MUST zůstat 1:1 přenositelná.
- **MUST:** host-policy applier je adaptér `ruleset → enforcer-specific call` (Fly Network Policy API
  dnes; nftables na hypervisor hostu na VPS). Vrstva 1 (Smokescreen ACL) a vrstva 3 (in-VM nftables)
  identické na obou substrátech.
