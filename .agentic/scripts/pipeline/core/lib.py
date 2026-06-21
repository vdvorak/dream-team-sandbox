#!/usr/bin/env python3
"""lib.py — doporučená knihovna pro schopnost + stack (vetted) (z lib.sh).

Než agent zvolí knihovnu, zeptá se SEM (templates/stacks/recommended-libs.yaml). Schopnost
mimo list → není vetted → nová závislost přes Tony (stack) + Heimdall (security).

CLI:   python3 lib.py --stack <stack> [--capability <cap>]
Exit:  0 = nalezeno | 1 = stack/capability mimo list | 2 = chyba.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import find_agentic, yaml


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--stack", default="")
    ap.add_argument("--capability", default="")
    args = ap.parse_args(argv)
    if not args.stack:
        common.die("Usage: lib.py --stack <stack> [--capability <cap>]")

    reg_path = find_agentic("templates/stacks/recommended-libs.yaml")
    if not reg_path:
        common.die("CHYBA: nenalezen templates/stacks/recommended-libs.yaml.")

    reg = yaml.safe_load(open(reg_path, encoding="utf-8")) or {}
    stacks = reg.get("stacks", {}) or {}
    stack, cap = args.stack, args.capability

    s = stacks.get(stack)
    if not s:
        print(f"stack '{stack}' není v recommended-libs. Dostupné: {', '.join(stacks)}", file=sys.stderr)
        sys.exit(1)

    def line(item):
        return f"  - {item.get('lib')}  — {item.get('what', '')}"

    if cap:
        caps = s.get("capabilities", {}) or {}
        hit = caps.get(cap) or next((v for k, v in caps.items() if cap.lower() in k.lower()), None)
        if not hit:
            print(f"'{cap}' není mezi vetted capabilities stacku {stack}.")
            print("  → není to vetted volba: nová závislost přes Tony (stack) + Heimdall (security).")
            print(f"  dostupné capabilities: {', '.join(caps) or '-'}")
            sys.exit(1)
        print(f"[{stack}] {cap}:")
        print(line(hit))
        if hit.get("note"):
            print(f"    pozn.: {hit['note']}")
        sys.exit(0)

    if s.get("styling"):
        print(f"styling:     {s['styling']}")
    if s.get("data_access"):
        print(f"data_access: {s['data_access']}")
    for sec in ("core", "dev"):
        if s.get(sec):
            print(f"\n{sec}:")
            for it in s[sec]:
                print(line(it))
    caps = s.get("capabilities", {}) or {}
    if caps:
        print("\ncapabilities (vetted optional):")
        for k, v in caps.items():
            print(f"  {k}: {v.get('lib')} — {v.get('what', '')}")
    sys.exit(0)


if __name__ == "__main__":
    main()
