# Acceptance criteria — containment-cage

Každé AC = pozorovatelný PASS/FAIL test spustitelný zevnitř workspace PTY
proti nasazené kleci. Testovací příkazy přebírají ze schváleného plánu (§Verifikace).
Gate PASS = všechna AC zelená.

---

## I1 — Default-deny egress (host-enforced)

**Co:** Fly Network Policy (host-enforced, z microVM nepřepsatelná) blokuje veškerý egress mimo
povolené. In-VM firewall není primární enforcer.

| # | Test | PASS |
|---|------|------|
| 1a | `curl -m5 https://example.com` | exit ≠ 0, spojení odmítnuto/timeout |
| 1b | `nc -w3 1.1.1.1 22` | exit ≠ 0, spojení odmítnuto/timeout |
| 1c | `ssh -o ConnectTimeout=3 git@example.com` | exit ≠ 0, connection refused/timeout |
| 1d | `curl -m5 http://169.254.169.254/` | exit ≠ 0 (metadata endpoint blokován) |
| 1e | DNS dotaz mimo allowlisted resolver (přímý UDP :53 na 8.8.8.8) | blokováno hostitelem |

---

## I2 — Doménový allowlist (proxy granularita)

**Co:** Smokescreen proxy povoluje pouze explicitně whitelistované domény. Host pustí :443 jen
na proxy/approved CIDR — přímé spojení na :443 skončí na host-enforced vrstvě.

| # | Test | PASS |
|---|------|------|
| 2a | `curl -m5 https://api.github.com` | HTTP 2xx/3xx (v povolené doméně) |
| 2b | `curl -m5 https://raw.githubusercontent.com` | exit ≠ 0 (mimo allowlist, blokováno proxy) |
| 2c | `curl -m5 https://<CF_ACCESS_TEAM>.cloudflareaccess.com/cdn-cgi/access/certs` | HTTP 2xx/3xx |
| 2d | Přímý TCP na :443 na veřejnou IP (bez proxy, mimo approved CIDR) | blokováno hostitelem |

---

## I3 — Build-time hosty nedosažitelné v runtime

**Co:** Package registry endpoints (PyPI, npmjs, cloudflared apt, GitHub apt) jsou mimo allowlist;
runtime workspace nemůže instalovat software ze sítě.

| # | Test | PASS |
|---|------|------|
| 3a | `pip install requests` | exit ≠ 0 (network error, ne missing tool) |
| 3b | `npm i -g typescript` | exit ≠ 0 (network error) |
| 3c | `apt update` | exit ≠ 0 (network error) |

---

## I4 — Žádné `CAP_NET_ADMIN` v zaklecovaném procesu

**Co:** `claude` a všechny jím spuštěné procesy nikdy nedostanou `CAP_NET_ADMIN`. In-VM nftables
nelze smazat ani přepsat.

| # | Test | PASS |
|---|------|------|
| 4a | `capsh --print \| grep net_admin` | výstup prázdný |
| 4b | `nft list ruleset` | EPERM nebo "Operation not permitted" |
| 4c | `nft flush ruleset` | exit ≠ 0, EPERM |

---

## I5 — Policy nečitelná a neměnná zevnitř

**Co:** Smokescreen ACL není přítomen ve workspace FS ani env. Zaklecovaná AI neumí vyjmenovat
allowlist a neumí ho změnit.

| # | Test | PASS |
|---|------|------|
| 5a | `find / -name "smokescreen*" -o -name "*.acl" 2>/dev/null` | nic z cage artefaktů |
| 5b | `env \| grep -i proxy` vrací jen `http_proxy=http://127.0.0.1:4750` — ne obsah allowlistu | obsah ACL není v env |
| 5c | `curl http://127.0.0.1:4750/acl` nebo podobný introspekční endpoint | 404 / connection refused |

---

## I6 — `no_new_privs=1`, žádný setuid-root binář

**Co:** Žádný proces nemůže eskalovat privilegia přes setuid/setgid. `no_new_privs` je nastaven
před execem agenta.

| # | Test | PASS |
|---|------|------|
| 6a | `cat /proc/self/status \| grep NoNewPrivs` | `NoNewPrivs: 1` |
| 6b | `find / -perm -4000 -user root 2>/dev/null` (setuid bináry) | seznam neobsahuje bináry ovlivňující síť (ip, nft, ifconfig atp.) |

---

## I7 — Nula veřejného ingressu do workspace

**Co:** Workspace nemá `[http_service]` ani public IP. fly-proxy traffic neexistuje, Network Policy
je plně vynutitelná.

| # | Test | PASS |
|---|------|------|
| 7a | Z externího hosta: `curl -m5 https://<workspace-app>.fly.dev` | connection refused / timeout |
| 7b | `fly config show -a dream-team-workspace \| grep http_service` | žádný výstup |
| 7c | Re-test po každém `fly deploy` (regression guard) | AC 7a + 7b stále zelené |

---

## I8 — App↔AI oddělení na hypervisor hranici

**Co:** `dream-team-app` a `dream-team-workspace` jsou dvě oddělené Fly apps (dvě microVM,
dva kernely). Žádný sdílený volume ani netns.

| # | Test | PASS |
|---|------|------|
| 8a | `fly apps list` zobrazuje obě jako samostatné apps | 2 různé app entries |
| 8b | Ze workspace: `ip route` / `ip addr` neobsahuje IP rozsahy app machine | žádný overlap netns |
| 8c | Žádný Fly volume mountnutý v obou apps najednou (`fly volumes list`) | sdílený volume neexistuje |

---

## I9 — High-value secrets nikdy ve workspace env/volume

**Co:** `CLOUDFLARE_TUNNEL_TOKEN`, `CF_ACCESS_AUD`, `GH_TOKEN`, `ADMIN_BOOTSTRAP_TOKEN` nejsou
přístupné z workspace procesu ani z mountnutého volume.

| # | Test | PASS |
|---|------|------|
| 9a | `env \| grep -Ei 'TUNNEL\|CF_ACCESS_AUD\|GH_TOKEN\|BOOTSTRAP'` | prázdný výstup |
| 9b | `grep -r 'CLOUDFLARE_TUNNEL_TOKEN\|CF_ACCESS_AUD\|GH_TOKEN\|ADMIN_BOOTSTRAP_TOKEN' /workspace /home /root 2>/dev/null` | prázdný výstup |

---

## I10 — GitHub write credential scoped, jen v app

**Co:** Workspace má přístup max k jednomu git repozitáři (deploy key / fine-grained PAT).
Nemůže pushnout do jiných repozitářů. `gh` CLI s write credential není přítomen ve workspace.

| # | Test | PASS |
|---|------|------|
| 10a | `gh auth status` | not logged in, nebo token bez write oprávnění k jiným repům |
| 10b | `git push <jiné-repo-než-povolené>` ze workspace | exit ≠ 0, permission denied |
| 10c | Deploy key / PAT token v workspace FS má scope jen na 1 cílové repo (ověřeno přes GitHub API: `GET /repos/<owner>/<other-repo>/keys`) | token/key se neobjeví |

---

## I11 — Definice klece nedohledatelná zevnitř

**Co:** Žádný artefakt z `dream-team-sandbox` (firewall definice, seccomp profil, hardened-init,
deploy-wrapper, cage ACL) není přítomen ani čitelný ve workspace FS nebo env.

| # | Test | PASS |
|---|------|------|
| 11a | `find / -name "entrypoint.sh" -o -name "network-policy*" -o -name "cage-deploy*" 2>/dev/null` | nic z cage artefaktů |
| 11b | `env` neobsahuje proměnné odkazující na cage repo, cage verze ani cage konfiguraci | prázdný výstup pro cage-specifické klíče |
| 11c | `cat /proc/1/cmdline` a inspekce init procesu neodhalí jméno/cestu cage artefaktů | init je legitimní entrypoint bez cage identifikátoru |

---

## Gate podmínka

Gate PASS = I1–I11 všechna AC zelená (exit kódy + výstupy odpovídají PASS sloupci výše)
na živém Fly deploy. Každý gate (T1/T2/T3) re-runuje relevantní podmnožinu;
finální PASS = celá suite zelená.
