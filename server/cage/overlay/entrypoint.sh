#!/bin/sh
# =============================================================================
# entrypoint.sh — HARDENED overlay init klece (vrstva 3 + de-root sekvence).
#
# Tento soubor NAHRAZUJE naivní appkový entrypoint (reuse decision: feature-local).
# Běží jako ROOT a provede PŘESNĚ závaznou de-root sekvenci (contracts §1 / CE-3 /
# PROJECT-CONSTITUTION §Doménová security pravidla).
#
# FAIL-CLOSED (CE-2): každý bezpečnostní krok, který selže, ABORTuje entrypoint
# s konkrétním error kódem (contracts/error-codes.md) — machine se NESPUSTÍ jako klec.
# NIKDY se neexecne agent s rootem / CAP_NET_ADMIN / bez no_new_privs.
#
# Opacita (CE-4/I11): tento soubor je overlay artefakt; do appkového repa se nikdy
# nezapíše. Žádná zmínka o "cage"/repu v runtime prostředí dosažitelném agentem.
# =============================================================================
set -eu

# --- Konfigurace (env, s rozumnými defaulty) ---------------------------------
# Non-root agent uid/gid a domov. Musí odpovídat user created v overlay Dockerfile.
CAGE_AGENT_USER="${CAGE_AGENT_USER:-claude}"
CAGE_AGENT_UID="${CAGE_AGENT_UID:-10001}"
CAGE_AGENT_GID="${CAGE_AGENT_GID:-10001}"
CAGE_AGENT_HOME="${CAGE_AGENT_HOME:-/home/${CAGE_AGENT_USER}}"
# Proxy sidecar (vrstva 1). Loopback bind, vlastní non-root uid (contracts §1).
CAGE_PROXY_ADDR="${CAGE_PROXY_ADDR:-127.0.0.1:4750}"
CAGE_PROXY_USER="${CAGE_PROXY_USER:-smokescreen}"
CAGE_ACL_PATH="${CAGE_ACL_PATH:-/etc/smokescreen/acl.yaml}"

# Error-code helper: vytiskni kód + důvod a ABORT (fail-closed).
cage_abort() {
  code="$1"; shift
  echo "[cage-entrypoint] ABORT ${code}: $*" >&2
  exit 1
}

# =============================================================================
# KROK 0 (root): přípravy — login persistence, git, proxy env, start Smokescreen.
# =============================================================================
# WHY: vše, co potřebuje root NEBO musí být hotové PŘED dropem caps / de-root.

# --- 0a) Claude login token persistence (REGRESE-GUARD, contracts §1 rozhodnutí (1)) ---
# Appka dělala `ln -s /data/claude-config /root/.claude` a běžela jako root. Po de-root
# běží agent jako NON-root → login persistence se přesouvá z /root/.claude na $HOME
# non-root usera. Volume subdir MUSÍ být pre-chown na agent uid PŘED de-root, jinak
# agent (non-root) nezapíše token → po restartu re-login (regrese).
#
# no_new_privs (krok 3) tohle NEROZBÍJÍ: blokuje jen privilege escalation (setuid/file
# caps), NE běžný write souboru pod vlastním uid. Token = prostý write do $HOME/.claude.
if [ -d /data ]; then
  mkdir -p /data/claude-config /data/workspace
  # KRITICKÉ: pre-chown volume subdir na agent uid (jinak non-root agent nezapíše token).
  chown -R "${CAGE_AGENT_UID}:${CAGE_AGENT_GID}" /data/claude-config /data/workspace \
    || cage_abort ERR_LOGIN_PERSIST "pre-chown /data/claude-config na agent uid selhal"
  # Symlink relativní k $HOME non-root usera (NE /root/.claude).
  mkdir -p "${CAGE_AGENT_HOME}"
  if [ ! -e "${CAGE_AGENT_HOME}/.claude" ]; then
    ln -s /data/claude-config "${CAGE_AGENT_HOME}/.claude" \
      || cage_abort ERR_LOGIN_PERSIST "symlink \$HOME/.claude → volume selhal"
  fi
  # Symlink samotný musí patřit agentovi (link ownership).
  chown -h "${CAGE_AGENT_UID}:${CAGE_AGENT_GID}" "${CAGE_AGENT_HOME}/.claude" || true
  export WORKSPACE_DIR=/data/workspace
fi
# Vlastnictví celého $HOME na agenta (managed-settings zůstává systémové v /etc, viz Dockerfile).
chown -R "${CAGE_AGENT_UID}:${CAGE_AGENT_GID}" "${CAGE_AGENT_HOME}" || true

# --- 0b) git config (přebráno z appky, beze změny logiky) ---
git config --system --add safe.directory '*' || true
git config --system user.name "${GIT_AUTHOR_NAME:-Dream Team Agent}" || true
git config --system user.email "${GIT_AUTHOR_EMAIL:-agent@dream-team.local}" || true

# --- 0c) render proxy env (dvojitý zámek vrstva 1, contracts §1) ---
# "Měkký" mechanismus: klient SDE může env ignorovat — tvrdý zámek je host pravidlo H1.
PROXY_URL="http://${CAGE_PROXY_ADDR}"
export http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}"
export HTTP_PROXY="${PROXY_URL}" HTTPS_PROXY="${PROXY_URL}"
# localhost/6PN nesmí jít přes proxy (interní komunikace app→workspace na :8081).
export no_proxy="localhost,127.0.0.1,::1,.internal"
export NO_PROXY="${no_proxy}"

# --- 0d) start Smokescreen sidecar pod dedikovaným non-root uid (loopback, mgmt off) ---
# WHY (I5c): management/introspekční endpoint NESMÍ být dostupný agentovi → bind jen
# loopback, žádný management listen. ACL soubor je mode 0400 root:root (I5a/I5b) —
# proxy ho čte při startu jako root-spawned proces, agent ho nepřečte.
if [ -f "${CAGE_ACL_PATH}" ]; then
  chmod 0400 "${CAGE_ACL_PATH}" || true
  chown root:root "${CAGE_ACL_PATH}" || true
  # `setpriv`/`su` spustí proxy jako non-root uid; loopback bind; bez management API.
  setpriv --reuid "${CAGE_PROXY_USER}" --regid "${CAGE_PROXY_USER}" --init-groups \
    smokescreen --listen-ip 127.0.0.1 --listen-port "${CAGE_PROXY_ADDR##*:}" \
                --egress-acl-file "${CAGE_ACL_PATH}" \
                >/var/log/smokescreen.log 2>&1 &
  CAGE_PROXY_PID=$!
  # WHY (ERR_PROXY_DOWN / fail-CLOSED, contracts §4): když proxy nenaběhne, NEpokračuj
  # s "přímým ven". H1 stejně pustí :443 jen na proxy CIDR → mrtvá proxy = žádný egress.
  sleep 1
  if ! kill -0 "${CAGE_PROXY_PID}" 2>/dev/null; then
    cage_abort ERR_PROXY_DOWN "Smokescreen sidecar nenaběhl (fail-CLOSED: žádný egress)"
  fi
else
  cage_abort ERR_PROXY_DOWN "Smokescreen ACL chybí (${CAGE_ACL_PATH}) — nelze startovat proxy (fail-closed)"
fi

# =============================================================================
# KROK 1 (root): instalace in-VM nftables default-DROP ruleset (vrstva 3).
# =============================================================================
# WHY: MUSÍ být PŘED dropem CAP_NET_ADMIN (krok 2) — jinak by ho nešlo nainstalovat.
# Vrstva 3 je DEFENSE-IN-DEPTH (sekundární), nikdy jediný nositel garance (CE-1).
# Po dropu caps se stane neměnným (agent: `nft flush` → EPERM, I4b/I4c).
if ! command -v nft >/dev/null 2>&1; then
  cage_abort ERR_INVM_FW_FAILED "nft binár chybí v image (vrstva 3 nelze nainstalovat)"
fi
nft -f /etc/nftables.cage.conf \
  || cage_abort ERR_INVM_FW_FAILED "in-VM nftables default-DROP instalace selhala (krok 1)"

# =============================================================================
# KROK 2 (root): DROP CAP_NET_ADMIN (+ net-mgmt caps) z BOUNDING setu.
# =============================================================================
# WHY (I4a): drop z BOUNDING setu (ne jen effective) → žádný potomek (ani přes setuid
# binár) cap znovu nezíská. Společně s no_new_privs (krok 3) zavírá re-gain.
# Toto je defense-in-depth zámek vrstvy 3: po dropu agent NEMŮŽE `nft flush`.
#
# Použijeme `capsh` k execu zbytku jako non-root s dropnutým bounding setem + no_new_privs
# (kroky 2+3+4 jdou jednou capsh invokací — capsh umí --drop-bounding, --secbits/no-setuid-fixup
# a --user v jednom; tím je pořadí atomické a auditovatelné).
if ! command -v capsh >/dev/null 2>&1; then
  cage_abort ERR_CAP_DROP_FAILED "capsh chybí — nelze dropnout CAP_NET_ADMIN z bounding setu"
fi

# WHY: ověř, že nft už agent NEsmí měnit — pre-flight, že vrstva 3 je usazená před de-root.
# (Reálný test EPERM proběhne až po dropu; zde jen sanity, že ruleset je aktivní.)
nft list ruleset >/dev/null 2>&1 || cage_abort ERR_INVM_FW_FAILED "nftables ruleset není aktivní před de-root"

# =============================================================================
# KROK 3 + 4 (root → non-root): no_new_privs=1, pak exec agenta jako NON-root.
# =============================================================================
# capsh provede atomicky:
#   --drop=cap_net_admin,cap_net_raw,cap_net_bind_service  (z bounding setu, I4a)  [krok 2]
#   --secbits=... / --no-new-privs                          (no_new_privs=1, I6a)  [krok 3]
#   --user=<agent>                                          (setuid non-root)      [krok 4]
#   -- exec agent
#
# WHY pořadí (CE-3, ZÁVAZNÉ): cap drop PŘED no_new_privs PŘED exec. capsh --drop dropuje
# z bounding setu; --no-new-privs nastaví PR_SET_NO_NEW_PRIVS; --user setuidne na agenta;
# `--` exec běží už jako non-root, bez CAP_NET_ADMIN, s no_new_privs → agent nikdy nedědí root.
#
# Selhání capsh (jakýkoli z kroků 2/3/4) = celý exec selže → fail-closed: agent se NESPUSTÍ.
exec capsh \
  --drop=cap_net_admin,cap_net_raw,cap_net_bind_service \
  --secbits=0x2f \
  --no-new-privs \
  --user="${CAGE_AGENT_USER}" \
  --addamb= \
  -- -c 'exec python3 /opt/agent/agent.py' \
  || cage_abort ERR_CAP_DROP_FAILED "de-root exec (cap drop / no_new_privs / setuid) selhal — agent NEspuštěn jako klec"
