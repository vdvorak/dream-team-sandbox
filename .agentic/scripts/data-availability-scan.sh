#!/usr/bin/env bash
# data-availability-scan.sh — raná (ADVISORY) kontrola dostupnosti dat (N2).
#
# CÍL (engine-flow-hardening N2): chytit scope-creep „AC jmenuje datové pole k zobrazení, které
# kontrakt/typ nemá" v JEDNOM průchodu na rané bráně (spec-gate), místo iterativně po dávkách v T3.
# Root cause vlny re-skin: AC chtěla zobrazit data (run-status/počty na dlaždicích, tokeny/časy/
# last_output, kategorie agenta), která appka v kontraktech neměla → spec-gate se zacyklil 5 kol.
#
# ADVISORY (NEblokuje — L3 PO 2026-06-19 rozhodl start nezávazně): skript dá PRIOR (kandidáti na
# nepokrytá pole); Sheldon/Vision soudí HRANICI (odvozené / přejmenované / agregované pole NENÍ
# díra). Constitution §Filozofie #7: mechanika (sken polí + průnik) skriptem, úsudek (je to reálná
# díra?) u LLM. Skript NIKDY nevrací exit 1 jako blocker — vrací 0 (čisto) i při nálezech reportuje
# přes stdout marker `data-availability: MISSING`; preflight ho pouští jako advisory linter.
#
# MECHANIKA — robustní vůči OpenAPI $ref/allOf (NE křehký grep):
#   1) z acceptance/<feature>.md vytáhne JMENOVANÁ datová pole — backtick `identifikátory`
#      (snake_case / camelCase), které vypadají jako field names (filtruje HTTP slovesa, literály).
#   2) sesbírá GLOBÁLNÍ množinu krytí: VŠECHNY `properties:` klíče napříč contracts/api/*.openapi.yaml
#      (přes PyYAML — rekurzivní sken, takže $ref/allOf vnořené schémata se započítají jejich
#      vlastními properties) + VŠECHNA pole interface/type v clients/web/src/types/*.ts.
#      Pole je KRYTÉ, pokud je v této globální množině (konzervativní prior — radši false-OK
#      než false-MISSING; hranici dořeší Sheldon).
#   3) nahlásí AC pole, která v krytí nejsou → kandidáti na „pole bez krytí v kontraktu/typu".
#
# DELTA SCOPE (FIX #1): --files FILE omezí sken AC souborů na PRŮNIK (delta ∩ acceptance/**).
# Bez --files = full-scan všech acceptance/**. Skener git NEČTE — delta resolvuje preflight.sh.
#
# Usage: bash scripts/data-availability-scan.sh [--root DIR] [--files LISTFILE]
# Exit:  0 vždy při úspěšném běhu (advisory; nálezy v stdout). 2 = chyba spuštění.
set -uo pipefail

ROOT="$PWD"; FILES_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)  ROOT="$2"; shift 2;;
    --files) FILES_LIST="$2"; shift 2;;
    -h|--help) sed -n '2,38p' "$0"; exit 0;;
    *) echo "data-availability-scan: neznámý argument: $1" >&2; exit 2;;
  esac
done

PY="python3"
command -v "$PY" >/dev/null 2>&1 || { echo "data-availability-scan: python3 není dostupný — SKIP (advisory)."; exit 0; }

ROOT="$ROOT" FILES_LIST="$FILES_LIST" "$PY" - <<'PYEOF'
import glob
import os
import re
import sys

ROOT = os.environ.get("ROOT", ".")
FILES_LIST = os.environ.get("FILES_LIST", "")

try:
    import yaml
except ImportError:
    print("data-availability-scan: PyYAML nedostupný — SKIP (advisory).")
    sys.exit(0)

ACC_DIR = os.path.join(ROOT, "acceptance")
CONTRACTS_GLOB = os.path.join(ROOT, "contracts", "api", "*.openapi.yaml")
TYPES_GLOB = os.path.join(ROOT, "clients", "web", "src", "types", "*.ts")

# ── 1) vyber acceptance soubory (delta ∩ acceptance/** nebo full-scan) ────────────
def delta_acc_files():
    if not FILES_LIST:
        return sorted(glob.glob(os.path.join(ACC_DIR, "*.md")))
    if not os.path.isfile(FILES_LIST):
        print(f"data-availability-scan: --files seznam neexistuje: {FILES_LIST}", file=sys.stderr)
        sys.exit(2)
    out = []
    with open(FILES_LIST, encoding="utf-8") as fh:
        for line in fh:
            f = line.strip().lstrip("./")
            if not f or not f.endswith(".md"):
                continue
            # acceptance/** v deltě (cesta může být relativní ke kořeni)
            if f.startswith("acceptance/") or f.startswith(os.path.join("acceptance", "")):
                p = os.path.join(ROOT, f)
                if os.path.isfile(p):
                    out.append(p)
    return sorted(set(out))

acc_files = delta_acc_files()
if not acc_files:
    print("data-availability-scan: žádné acceptance/** ke skenu (delta prázdný nebo bez acceptance) — OK.")
    print("data-availability: OK")
    sys.exit(0)

# ── 2) extrakce jmenovaných DATOVÝCH polí k zobrazení z AC (backtick identifikátory) ──
# Cílíme DATA POLE (response field names), ne každý backtick token. Heuristika (prior — hranici
# soudí Sheldon): pole k zobrazení je lowercase-initial identifikátor (snake_case / camelCase).
# VYŘAZUJEME jako šum (nejsou to data k zobrazení):
#   • UPPERCASE_CONSTANTS — error kódy (ERR_*), env vary (DATABASE_URL), engine konstanty (STATE_BLOCK_RE)
#   • PascalCase — názvy komponent / typů / schémat (StatusBadge, Avatar, AgentDetailResponse)
#   • test_* / *_RE — testy a regex konstanty (test_resolve…, STATE_BLOCK_RE)
#   • HTTP slovesa, literály, příliš obecná krátká slova
# Tím zůstanou reálná data pole (category, last_output, assignee, markerEnd), šum vypadne.
NON_FIELD = {
    "null", "true", "false", "get", "post", "put", "delete", "patch", "head", "options",
    "id", "ok", "in", "out", "url", "uri", "ui", "api", "and", "or", "not", "core",
}
BACKTICK = re.compile(r"`([A-Za-z][A-Za-z0-9_]*)`")
CAMEL = re.compile(r"[a-z][A-Z]")

def field_like(tok: str) -> bool:
    low = tok.lower()
    if low in NON_FIELD or len(tok) < 2:
        return False
    if tok.startswith("test_") or tok.endswith("_RE"):
        return False                       # testy / regex konstanty
    if tok.isupper() or "_" in tok and tok.upper() == tok:
        return False                       # UPPERCASE_CONSTANT (error kód / env var / enum konstanta)
    if tok[0].isupper():
        return False                       # PascalCase = název komponenty / typu / schématu, ne pole
    # zbývá lowercase-initial identifikátor → data field signál:
    if "_" in tok:
        return True                        # snake_case (last_output, retest_pending)
    if CAMEL.search(tok):
        return True                        # camelCase (markerEnd, lastOutput)
    # jednoslovné lowercase: pustíme jen >=4 znaky (category, name, model…) — kratší = šum.
    return len(tok) >= 4

# per-soubor mapa: feature -> {pole: prvni_radek}
ac_fields = {}   # feature -> { field: lineno }
for path in acc_files:
    feature = os.path.splitext(os.path.basename(path))[0]
    fields = {}
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for m in BACKTICK.finditer(line):
                tok = m.group(1)
                if field_like(tok) and tok not in fields:
                    fields[tok] = i
    if fields:
        ac_fields[feature] = fields

# ── 3) globální množina krytí: OpenAPI properties (rekurzivně) + TS pole ──────────
covered = set()

def collect_props(node):
    """Rekurzivně posbírej VŠECHNY 'properties:' klíče (vč. vnořených allOf/oneOf/items/$ref-cílů,
    které jsou v témže nebo jiném souboru reprezentované jako properties bloky). $ref necháváme —
    cílové schéma má vlastní properties blok, který sken stejně navštíví (globální množina)."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for k in props:
                covered.add(k)
        for v in node.values():
            collect_props(v)
    elif isinstance(node, list):
        for v in node:
            collect_props(v)

for cf in sorted(glob.glob(CONTRACTS_GLOB)):
    try:
        with open(cf, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        collect_props(doc)
    except (OSError, yaml.YAMLError):
        continue   # nečitelný kontrakt → advisory, neshazuj

# TS interface/type pole: `  fieldName: ...` nebo `  fieldName?: ...` uvnitř interface/type bloku.
TS_FIELD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:")
for tf in sorted(glob.glob(TYPES_GLOB)):
    try:
        with open(tf, encoding="utf-8") as fh:
            for line in fh:
                m = TS_FIELD.match(line)
                if m:
                    covered.add(m.group(1))
    except OSError:
        continue

# ── 4) report: AC pole bez krytí ─────────────────────────────────────────────────
missing = []   # (feature, field, lineno)
for feature, fields in sorted(ac_fields.items()):
    for field, lineno in sorted(fields.items(), key=lambda kv: kv[1]):
        if field not in covered:
            missing.append((feature, field, lineno))

scanned = len(acc_files)
if not missing:
    print(f"data-availability-scan: {scanned} acceptance souborů skenováno; všechna jmenovaná pole "
          f"mají krytí v kontraktu/typu (nebo nejsou field-like).")
    print("data-availability: OK")
    sys.exit(0)

print(f"data-availability-scan: {scanned} acceptance souborů; {len(missing)} kandidátů na pole bez "
      f"krytí v kontraktu/typu (ADVISORY — Sheldon/Vision soudí, zda je to reálná díra nebo "
      f"odvozené/přejmenované pole):")
for feature, field, lineno in missing:
    print(f"  · acceptance/{feature}.md:{lineno}  `{field}` — bez krytí v contracts/api/*.openapi.yaml ani types/*.ts")
miss_list = ", ".join(f"{f}.{fld}" for f, fld, _ in missing)
print(f"data-availability: MISSING — {miss_list}")
# ADVISORY: vždy exit 0 (neblokuje). preflight ho pouští jako advisory linter.
sys.exit(0)
PYEOF
