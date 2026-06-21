#!/usr/bin/env bash
# catalog-conformance.sh — mechanický back-align reuse (constitution §Reuse §Operační
# mechanismus). Jakmile komponenta v katalogu existuje, raw inline varianta téhož je drift.
# Deterministický grep anti-pattern signatur z `catalog-conformance.yaml`. MECHANISMUS
# (nástroj dolů); judgment (reálný drift vs legitimní výjimka) dělá Vitek nad výstupem.
#
# Najde všechny catalog-conformance.yaml v projektu (mimo framework snapshot + build dirs)
# a pro každý grepne `meta.scan_globs` na `signatures[].antipattern` mimo `allow`.
#
# Usage: bash .agentic/scripts/catalog-conformance.sh [--root DIR]
# Exit:  0 = čisto / jen WARN | 1 = blocker nález (gate-friendly) | 2 = chyba
set -uo pipefail
ROOT="$PWD"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    *) echo "Neznámý argument: $1" >&2; exit 2;;
  esac
done

CC_ROOT="$ROOT" python3 <<'PY'
import os, re, sys, fnmatch, glob
try:
    import yaml
except ImportError:
    print("CHYBA: chybí PyYAML.", file=sys.stderr); sys.exit(2)

root = os.environ["CC_ROOT"]
EXCL = {".agentic", ".claude", "node_modules", "build", "dist", ".git", ".venv", "__pycache__"}

catalogs = []
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d not in EXCL]
    if "catalog-conformance.yaml" in fns:
        catalogs.append(os.path.join(dp, "catalog-conformance.yaml"))
catalogs.sort()

if not catalogs:
    print("catalog-conformance: žádný catalog-conformance.yaml (nic ke kontrole)."); sys.exit(0)

blocker = warn = 0
for cat in catalogs:
    base = os.path.dirname(cat)
    spec = yaml.safe_load(open(cat, encoding="utf-8")) or {}
    scan_globs = (spec.get("meta") or {}).get("scan_globs") or ["src/**/*"]
    files = []
    for g in scan_globs:
        files += glob.glob(os.path.join(base, g), recursive=True)
    files = sorted({f for f in files if os.path.isfile(f)})
    for sig in spec.get("signatures") or []:
        try:
            rx = re.compile(sig["antipattern"])
        except (KeyError, re.error) as e:
            print(f"  [CHYBA signatury] {os.path.relpath(cat, root)}: {e}", file=sys.stderr); continue
        allow = sig.get("allow") or []
        sev = (sig.get("severity") or "blocker").lower()
        comp, why = sig.get("component", "?"), sig.get("why", "")
        for f in files:
            rel = os.path.relpath(f, base)
            if any(fnmatch.fnmatch(rel, a) or fnmatch.fnmatch(f, a) for a in allow):
                continue
            try:
                lines = open(f, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for i, ln in enumerate(lines, 1):
                if rx.search(ln):
                    tag = "BLOCKER" if sev == "blocker" else "WARN"
                    print(f"  [{tag}] {os.path.relpath(f, root)}:{i}  {comp} — {why}")
                    if sev == "blocker": blocker += 1
                    else: warn += 1

print(f"catalog-conformance: blocker={blocker} warn={warn} (katalogů: {len(catalogs)})")
sys.exit(1 if blocker else 0)
PY
