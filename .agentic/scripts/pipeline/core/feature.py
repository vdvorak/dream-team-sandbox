#!/usr/bin/env python3
"""feature.py — resolver feature knihovny (P7: cross-project moduly) (z feature.sh).

Feature = znovupoužitelná schopnost se stack-agnostic spec (vždy) + volitelným per-stack impl.
RESOLVE (co/kam); APPLY dělá apply_feature.py.

CLI:   python3 feature.py --list | --feature <f> [--variant <v>] [--stack <s>]
Exit:  0 = ok | 1 = nenalezeno | 2 = chyba.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import find_agentic, yaml


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--list", dest="do_list", action="store_true")
    ap.add_argument("--feature", default="")
    ap.add_argument("--variant", default="")
    ap.add_argument("--stack", default="")
    args = ap.parse_args(argv)

    root = find_agentic("templates/features")
    if not root:
        common.die("CHYBA: nenalezen templates/features/.")

    feat, variant, stack = args.feature, args.variant, args.stack

    def load(fid):
        p = os.path.join(root, fid, "feature.yaml")
        return yaml.safe_load(open(p, encoding="utf-8")) if os.path.isfile(p) else None

    features = sorted(os.path.basename(os.path.dirname(p))
                      for p in glob.glob(os.path.join(root, "*", "feature.yaml")))

    if args.do_list or not feat:
        print("Feature library:")
        for fid in features:
            f = load(fid) or {}
            sec = " [security-critical]" if f.get("security_critical") else ""
            print(f"  {fid}{sec} — {f.get('description', '')}")
            for vid, v in (f.get("variants") or {}).items():
                st = v.get("status", "ready")
                impls = ", ".join((v.get("impl") or {}).keys()) or "spec-only"
                print(f"    · {vid}: {v.get('label', '')}  [{st}; impl: {impls}]")
        sys.exit(0)

    f = load(feat)
    if not f:
        print(f"Feature '{feat}' nenalezena. Dostupné: {', '.join(features)}", file=sys.stderr)
        sys.exit(1)

    print(f"feature: {feat}  {'[security-critical → audit-once Heimdall]' if f.get('security_critical') else ''}")
    print(f"  spec:  {f.get('spec')}")
    variants = f.get("variants") or {}
    if not variant:
        print("  varianty:")
        for vid, v in variants.items():
            print(f"    - {vid}: {v.get('label')}  [{v.get('status', 'ready')}]")
        print("  Watson:", (f.get("watson") or {}).get("question", "-"))
        sys.exit(0)

    v = variants.get(variant)
    if not v:
        print(f"Varianta '{variant}' není v '{feat}'. Dostupné: {', '.join(variants)}", file=sys.stderr)
        sys.exit(1)
    print(f"  variant: {variant} — {v.get('label')}  [{v.get('status', 'ready')}]")
    req = v.get("requires") or []
    if req:
        print(f"  requires: {', '.join(req)}")
    print(f"  produces: {', '.join(v.get('produces') or []) or '-'}")
    for oid, o in (v.get("options") or {}).items():
        print(f"  option {oid}: {o.get('question')} → {'/'.join(o.get('choices') or [])} (default: {o.get('default')})")
    impl = (v.get("impl") or {})
    if stack:
        path = impl.get(stack)
        if path:
            print(f"  impl[{stack}]: {path}")
        else:
            print(f"  impl[{stack}]: — (spec-only pro tenhle stack; vygeneruj z spec.md)")
    else:
        print(f"  impl: {', '.join(impl.keys()) or 'spec-only'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
