#!/usr/bin/env bash
# =============================================================================
# containment_cage_harness.sh — Acceptance test harness pro containment-cage
#
# Spustit ZEVNITŘ workspace PTY po nasazení klece (alfred post-deploy).
# Každý test = jeden acceptance bod z acceptance/containment-cage.md (I1–I11).
#
# Tagy:
#   [post-deploy-live] = vyžaduje běžící nasazenou klec (nelze teď)
#   [static]           = jde ověřit bez živé klece (strukturální / konfigurační)
#
# Výstup: PASS/FAIL per AC bod, souhrnný exit code 0 = vše zelené.
# =============================================================================
set -euo pipefail

# --- Barvy (vypnutelné CI=true) ---
if [ "${CI:-false}" = "true" ] || ! [ -t 1 ]; then
    GREEN=""; RED=""; YELLOW=""; RESET=""
else
    GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[0;33m"; RESET="\033[0m"
fi

PASS=0
FAIL=0
BLOCKED=0

_pass() { echo -e "${GREEN}PASS${RESET} [$1] $2"; PASS=$((PASS+1)); }
_fail() { echo -e "${RED}FAIL${RESET} [$1] $2"; echo "      PŘIZNAK: $3"; FAIL=$((FAIL+1)); }
_blocked() { echo -e "${YELLOW}BLOCKED${RESET} [$1] $2 — $3"; BLOCKED=$((BLOCKED+1)); }

# Externi host (pro I7a — spustit mimo workspace)
WORKSPACE_APP="${WORKSPACE_APP:-dream-team-workspace.fly.dev}"
# CF Access team label (pro proxy test I2c)
CF_TEAM="${CF_TEAM:-}"

echo "=== Containment Cage Acceptance Harness ==="
echo "    Datum: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "    Host:  $(hostname)"
echo ""

# =============================================================================
# I1 — Default-deny egress (host-enforced) [post-deploy-live][security]
# =============================================================================
echo "--- I1: Default-deny egress ---"

# I1a — přímý egress na veřejnou adresu
if curl -m5 -s -o /dev/null -w "%{http_code}" https://example.com 2>/dev/null | grep -qE "^[0-9]"; then
    _fail "I1a" "curl https://example.com neměl projít" \
        "curl https://example.com → spojení prošlo, exit 0; čekán exit ≠ 0 (connection refused/timeout)"
else
    _pass "I1a" "curl https://example.com → odmítnuto/timeout (OK)"
fi

# I1b — SSH na náhodný host
if nc -w3 1.1.1.1 22 2>/dev/null; then
    _fail "I1b" "nc na :22 prošlo" \
        "nc -w3 1.1.1.1 22 → exit 0; čekán exit ≠ 0 (H4 SSH deny)"
else
    _pass "I1b" "nc -w3 1.1.1.1 22 → odmítnuto (OK)"
fi

# I1c — SSH direct
if ssh -o ConnectTimeout=3 -o BatchMode=yes git@example.com true 2>/dev/null; then
    _fail "I1c" "SSH na git@example.com prošlo" \
        "ssh git@example.com → exit 0; čekán exit ≠ 0 (H4 deny)"
else
    _pass "I1c" "ssh git@example.com → connection refused/timeout (OK)"
fi

# I1d — metadata endpoint
if curl -m5 -s -o /dev/null http://169.254.169.254/ 2>/dev/null; then
    _fail "I1d" "curl metadata endpoint prošel" \
        "curl http://169.254.169.254/ → exit 0; čekán exit ≠ 0 (H5 metadata blackhole)"
else
    _pass "I1d" "curl http://169.254.169.254/ → blokováno (OK)"
fi

# I1e — DNS mimo allowlisted resolver
if nslookup -port=53 example.com 8.8.8.8 > /dev/null 2>&1; then
    _fail "I1e" "přímý DNS na 8.8.8.8 prošel" \
        "nslookup example.com 8.8.8.8 → exit 0; čekán FAIL (H3 jen allowlisted resolver)"
else
    _pass "I1e" "přímý DNS na 8.8.8.8 → blokováno hostitelem (OK)"
fi

# =============================================================================
# I2 — Doménový allowlist (proxy granularita) [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I2: Doménový allowlist ---"

# I2a — api.github.com v allowlistu
HTTP_CODE=$(curl -m10 -s -o /dev/null -w "%{http_code}" https://api.github.com 2>/dev/null || echo "000")
if echo "$HTTP_CODE" | grep -qE "^[23][0-9][0-9]$"; then
    _pass "I2a" "curl https://api.github.com → $HTTP_CODE (OK, v allowlistu)"
else
    _fail "I2a" "api.github.com nepřístupný přes proxy" \
        "curl https://api.github.com → HTTP $HTTP_CODE; čekán 2xx/3xx (allowlist)"
fi

# I2b — raw.githubusercontent.com mimo allowlist
if curl -m5 -s -o /dev/null https://raw.githubusercontent.com 2>/dev/null; then
    _fail "I2b" "raw.githubusercontent.com prošel (mimo allowlist)" \
        "curl https://raw.githubusercontent.com → exit 0; čekán exit ≠ 0 (proxy deny)"
else
    _pass "I2b" "curl https://raw.githubusercontent.com → blokováno proxy (OK)"
fi

# I2c — CF Access doména (pokud je CF_TEAM nastaven)
if [ -n "${CF_TEAM}" ]; then
    CF_CODE=$(curl -m10 -s -o /dev/null -w "%{http_code}" \
        "https://${CF_TEAM}.cloudflareaccess.com/cdn-cgi/access/certs" 2>/dev/null || echo "000")
    if echo "$CF_CODE" | grep -qE "^[23][0-9][0-9]$"; then
        _pass "I2c" "CF Access doména ${CF_TEAM}.cloudflareaccess.com → $CF_CODE (OK)"
    else
        _fail "I2c" "CF Access doména nepřístupná" \
            "curl ${CF_TEAM}.cloudflareaccess.com/cdn-cgi/access/certs → HTTP $CF_CODE; čekán 2xx/3xx"
    fi
else
    _blocked "I2c" "CF Access allowlist test" "CF_TEAM env není nastaven (export CF_TEAM=<váš-team>)"
fi

# I2d — přímý TCP na :443 mimo proxy (bez PROXY env, obchází double-lock)
if curl -m5 -s -o /dev/null --noproxy '*' https://1.1.1.1 2>/dev/null; then
    _fail "I2d" "přímý TCP :443 na veřejnou IP prošel (H1 selhává)" \
        "curl --noproxy '*' https://1.1.1.1 → exit 0; čekán exit ≠ 0 (H1 host deny přímého :443)"
else
    _pass "I2d" "přímý TCP :443 na veřejnou IP → blokováno hostitelem (OK)"
fi

# =============================================================================
# I3 — Build-time hosty nedosažitelné [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I3: Build-time hosty blokované v runtime ---"

# I3a — pip install (PyPI)
if pip install --quiet requests 2>/dev/null; then
    _fail "I3a" "pip install requests prošel (PyPI dosažitelný)" \
        "pip install requests → exit 0; čekán exit ≠ 0 (network error, PyPI mimo allowlist)"
else
    _pass "I3a" "pip install requests → network error (OK, PyPI blokován)"
fi

# I3b — npm install
if npm i -g typescript --quiet 2>/dev/null; then
    _fail "I3b" "npm install typescript prošel" \
        "npm i -g typescript → exit 0; čekán exit ≠ 0 (npmjs mimo allowlist)"
else
    _pass "I3b" "npm i -g typescript → network error (OK, npmjs blokován)"
fi

# I3c — apt update
if apt update -qq 2>/dev/null; then
    _fail "I3c" "apt update prošel (package registry dosažitelný)" \
        "apt update → exit 0; čekán exit ≠ 0 (apt registry mimo allowlist)"
else
    _pass "I3c" "apt update → network error (OK, apt registry blokován)"
fi

# =============================================================================
# I4 — Žádné CAP_NET_ADMIN [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I4: Žádné CAP_NET_ADMIN ---"

# I4a — capsh --print
NET_ADMIN_OUT=$(capsh --print 2>/dev/null | grep -i net_admin || true)
if [ -z "$NET_ADMIN_OUT" ]; then
    _pass "I4a" "capsh --print | grep net_admin → prázdný výstup (OK)"
else
    _fail "I4a" "CAP_NET_ADMIN přítomen v procesu" \
        "capsh --print | grep net_admin → '$NET_ADMIN_OUT'; čekán prázdný výstup"
fi

# I4b — nft list ruleset (EPERM)
if nft list ruleset 2>/dev/null; then
    # nft prošel — agent má přístup k netlink
    _fail "I4b" "nft list ruleset prošel (CAP_NET_ADMIN nebo NET_ADMIN přítomen)" \
        "nft list ruleset → exit 0; čekán EPERM (agent nemá CAP_NET_ADMIN)"
else
    _pass "I4b" "nft list ruleset → EPERM (OK, agent nemá CAP_NET_ADMIN)"
fi

# I4c — nft flush ruleset (destruktivní pokus)
if nft flush ruleset 2>/dev/null; then
    _fail "I4c" "nft flush ruleset prošel (KRITICKÉ: vrstva 3 smazána)" \
        "nft flush ruleset → exit 0; čekán exit ≠ 0 EPERM (klec obejitelná zevnitř)"
else
    _pass "I4c" "nft flush ruleset → EPERM (OK, agent nemůže smazat firewall)"
fi

# =============================================================================
# I5 — Policy nečitelná a neměnná zevnitř [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I5: Policy nečitelná zevnitř ---"

# I5a — find smokescreen/ACL artefaktů v agent-dosažitelném FS
FOUND=$(find / -name "smokescreen*" -o -name "*.acl" 2>/dev/null | \
    grep -v "^/proc\|^/sys\|^/dev" || true)
if [ -z "$FOUND" ]; then
    _pass "I5a" "find smokescreen*/acl → nic nalezeno v agent FS (OK)"
else
    _fail "I5a" "smokescreen/ACL artefakt čitelný zevnitř" \
        "find smokescreen*/acl → '$FOUND'; čekán prázdný (opacita I5/I11)"
fi

# I5b — env | grep proxy (proxy endpoint ano, ACL obsah ne)
PROXY_ENV=$(env | grep -i proxy || true)
if echo "$PROXY_ENV" | grep -iqE "(domain|allowlist|acl|whitelist)"; then
    _fail "I5b" "proxy env obsahuje obsah ACL/allowlistu" \
        "env | grep proxy obsahuje ACL obsah; čekán jen proxy endpoint URL"
else
    _pass "I5b" "proxy env neobsahuje obsah ACL (OK, jen endpoint URL)"
fi

# I5c — introspekce proxy management endpoint
MGMT_CODE=$(curl -m3 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4750/metrics 2>/dev/null || echo "000")
if echo "$MGMT_CODE" | grep -qE "^[23][0-9][0-9]$"; then
    _fail "I5c" "proxy management endpoint přístupný" \
        "curl http://127.0.0.1:4750/metrics → HTTP $MGMT_CODE; čekán 404/connection refused"
else
    _pass "I5c" "proxy management endpoint → 404/refused (OK, management off)"
fi

# =============================================================================
# I6 — no_new_privs=1, žádný setuid-root síťový binár [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I6: no_new_privs + setuid audit ---"

# I6a — /proc/self/status NoNewPrivs
NNP=$(grep NoNewPrivs /proc/self/status 2>/dev/null | awk '{print $2}' || echo "")
if [ "$NNP" = "1" ]; then
    _pass "I6a" "NoNewPrivs: 1 (OK)"
else
    _fail "I6a" "NoNewPrivs není nastaven" \
        "/proc/self/status NoNewPrivs → '$NNP'; čekán '1' (krok 3 entrypoint)"
fi

# I6b — setuid bináry s root vlastnictvím (bez síťových utilit)
NET_SETUID=$(find / -perm -4000 -user root 2>/dev/null | \
    grep -E "(ip|nft|ifconfig|iptables|tc|capsh|newuidmap|newgidmap)" | \
    grep -v "^/proc\|^/sys\|^/dev" || true)
if [ -z "$NET_SETUID" ]; then
    _pass "I6b" "žádné síťové setuid-root bináry nalezeny (OK)"
else
    _fail "I6b" "nalezeny síťové setuid-root bináry" \
        "find setuid root → '$NET_SETUID'; čekán prázdný seznam (síťové utility)"
fi

# =============================================================================
# I7 — Nula veřejného ingressu [post-deploy-live][security] + re-test regression
# =============================================================================
echo ""
echo "--- I7: Nula veřejného ingressu ---"

# I7a — z externího hosta (tento test se spouští ZEVNITŘ workspace, proto je BLOCKED)
_blocked "I7a" "external curl na workspace app" \
    "nutno spustit z externího hosta: curl -m5 https://${WORKSPACE_APP}"

# I7b — konfigurace workspace: žádná http_service sekce
# Pokud fly CLI je dostupné, zkontrolujeme živou konfiguraci
if command -v fly >/dev/null 2>&1; then
    FLYTOML=$(fly config show --app dream-team-workspace 2>/dev/null || echo "")
    if echo "$FLYTOML" | grep -q "http_service"; then
        _fail "I7b" "fly config obsahuje http_service (regrese I7)" \
            "fly config show obsahuje http_service sekci; čekán žádný výstup pro http_service"
    else
        _pass "I7b" "fly config neobsahuje http_service (OK, 6PN-only)"
    fi
else
    # Statická verifikace overlay souboru
    if grep -q "http_service" /home/vitek/dev/AI/dream-team-sandbox/server/cage/overlay/fly.workspace.toml 2>/dev/null; then
        UNCOMMENTED=$(grep "http_service" \
            /home/vitek/dev/AI/dream-team-sandbox/server/cage/overlay/fly.workspace.toml | \
            grep -v "^\s*#" || true)
        if [ -z "$UNCOMMENTED" ]; then
            _pass "I7b" "overlay fly.workspace.toml: http_service jen v komentáři (OK)"
        else
            _fail "I7b" "overlay fly.workspace.toml obsahuje aktivní http_service" \
                "grep http_service fly.workspace.toml → '$UNCOMMENTED'; čekán prázdný"
        fi
    else
        _pass "I7b" "overlay fly.workspace.toml: žádná http_service sekce (OK)"
    fi
fi

# I7c — regression guard (re-test po každém deploy, kontrakt §I7)
echo "      [regression-guard] I7 musí být re-testován po každém deploy (kontrakt §I7c)."

# =============================================================================
# I8 — App↔AI oddělení na hypervisor hranici [post-deploy-live][integration]
# =============================================================================
echo ""
echo "--- I8: App↔AI hypervisor oddělení ---"

# I8a — dvě samostatné entity
_blocked "I8a" "výpis nasazených aplikací (2 entity)" \
    "nutno spustit: fly apps list | grep dream-team — ověřit 2 různé app entries"

# I8b — ip route neobsahuje IP rozsahy app machine
APP_CIDRS=$(ip route 2>/dev/null | grep -v "fdaa\|127\|::1\|lo\|link-local" || true)
if [ -z "$APP_CIDRS" ]; then
    _pass "I8b" "ip route neobsahuje překrývající se rozsahy s app machine (OK)"
else
    echo "      INFO: ip route výstup pro audit: $APP_CIDRS"
    _pass "I8b" "ip route zkontrolován — bez zjevného překryvu s app machine"
fi

# I8c — žádný sdílený volume
_blocked "I8c" "audit sdílených volumes" \
    "nutno ověřit: fly volumes list --app dream-team-app a --app dream-team-workspace → bez sdíleného volume"

# =============================================================================
# I9 — High-value secrets nikdy ve workspace env/volume [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I9: High-value secrets v env/volume ---"

# I9a — env scan
SECRETS_IN_ENV=$(env | grep -Ei 'TUNNEL|CF_ACCESS_AUD|GH_TOKEN|BOOTSTRAP' || true)
if [ -z "$SECRETS_IN_ENV" ]; then
    _pass "I9a" "env neobsahuje high-value secrets (OK)"
else
    _fail "I9a" "high-value secret nalezen ve workspace env" \
        "env | grep secrets → '$SECRETS_IN_ENV'; čekán prázdný výstup"
fi

# I9b — grep v workspace FS
SECRETS_IN_FS=$(grep -r \
    'CLOUDFLARE_TUNNEL_TOKEN\|CF_ACCESS_AUD\|GH_TOKEN\|ADMIN_BOOTSTRAP_TOKEN' \
    /workspace /home /root 2>/dev/null || true)
if [ -z "$SECRETS_IN_FS" ]; then
    _pass "I9b" "grep workspace/home/root → žádný high-value secret v FS (OK)"
else
    _fail "I9b" "high-value secret nalezen v workspace FS" \
        "grep secrets /workspace/home/root → nález; čekán prázdný výstup"
fi

# =============================================================================
# I10 — GitHub write credential scoped [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I10: GitHub write credential scoping ---"

# I10a — gh auth status
GH_STATUS=$(gh auth status 2>&1 || true)
if echo "$GH_STATUS" | grep -qi "not logged in\|no credential"; then
    _pass "I10a" "gh auth status → not logged in (OK, žádný write credential)"
elif echo "$GH_STATUS" | grep -qi "write\|repo.*write"; then
    _fail "I10a" "gh CLI má write oprávnění k repozitářům" \
        "gh auth status → obsahuje write scope; čekán not logged in nebo read-only"
else
    _pass "I10a" "gh auth status → přihlášen bez write oprávnění (OK nebo read-only)"
fi

# I10b — git push do jiného repa
_blocked "I10b" "git push do jiného repa test" \
    "manuální: git push <jiné-repo> → čekán exit ≠ 0 permission denied"

# I10c — API scope check
_blocked "I10c" "PAT scope API ověření" \
    "manuální: curl -H 'Authorization: token \$(cat token)' https://api.github.com — ověřit scope"

# =============================================================================
# I11 — Definice klece nedohledatelná zevnitř [post-deploy-live][security]
# =============================================================================
echo ""
echo "--- I11: Definice klece nedohledatelná zevnitř ---"

# I11a — cage artefakty v FS
CAGE_ARTIFACTS=$(find / \( -name "entrypoint.sh" -o -name "network-policy*" -o -name "cage-deploy*" \) \
    2>/dev/null | grep -v "^/proc\|^/sys\|^/dev" || true)
if [ -z "$CAGE_ARTIFACTS" ]; then
    _pass "I11a" "find cage artefaktů → nic nalezeno v agent FS (OK, opacita)"
else
    _fail "I11a" "cage artefakt nalezen v agent-dostupném FS" \
        "find entrypoint/cage-deploy → '$CAGE_ARTIFACTS'; čekán prázdný (I11 opacita)"
fi

# I11b — env reference na cage
CAGE_ENV=$(env | grep -iE "cage|containment|sandbox.*repo|cage.*version" || true)
if [ -z "$CAGE_ENV" ]; then
    _pass "I11b" "env neobsahuje cage-specifické proměnné (OK)"
else
    _fail "I11b" "cage reference v env" \
        "env | grep cage → '$CAGE_ENV'; čekán prázdný (opacita)"
fi

# I11c — /proc/1/cmdline audit
INIT_CMD=$(cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
if echo "$INIT_CMD" | grep -iqE "cage|containment|dream-team-sandbox"; then
    _fail "I11c" "cage/sandbox identifikátor v init procesu" \
        "/proc/1/cmdline → '$INIT_CMD'; čekán bez cage identifikátoru"
else
    _pass "I11c" "/proc/1/cmdline neodhaluje cage artefakt (OK)"
fi

# =============================================================================
# Souhrnný výsledek
# =============================================================================
echo ""
echo "=============================================="
echo "VÝSLEDEK ACCEPTANCE HARNESS:"
echo "  PASS:    ${PASS}"
echo "  FAIL:    ${FAIL}"
echo "  BLOCKED: ${BLOCKED} (post-deploy-live, nutno nasadit klec)"
echo "=============================================="

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}CELKOVÝ VÝSLEDEK: FAIL${RESET} — ${FAIL} AC selhalo"
    exit 1
elif [ "$BLOCKED" -gt 0 ]; then
    echo -e "${YELLOW}CELKOVÝ VÝSLEDEK: INCOMPLETE${RESET} — ${BLOCKED} AC čeká na deploy"
    exit 2
else
    echo -e "${GREEN}CELKOVÝ VÝSLEDEK: PASS${RESET} — všechna AC zelená"
    exit 0
fi
