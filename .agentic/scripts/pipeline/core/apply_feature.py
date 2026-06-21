#!/usr/bin/env python3
"""apply_feature.py — APPLY engine feature knihovny (z apply-feature.sh).

Deterministicky overlayne vetted feature impl: copy dle manifestu (feature.yaml `apply:`) +
přepis base_package + číslování migrací na další volné V. Audit-once: byte-věrná kopie +
jen deterministický rename → Heimdallův audit zůstává platný.

CLI:   python3 apply_feature.py --feature auth --variant base --stack java-quarkus \
                                --option jwt --into <dir> --package com.acme.app
Importovatelné: `main(argv)` vrátí na úspěch (compose.py ho volá). Exit: 1/2 = chyba.
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import find_agentic, yaml


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--feature", default="")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--stack", default="")
    ap.add_argument("--option", default="")
    ap.add_argument("--into", default="")
    ap.add_argument("--package", default="")
    args = ap.parse_args(argv)

    feat, variant, stack = args.feature, args.variant, args.stack
    option, into, pkg_to = args.option, args.into, args.package
    if not (feat and stack and into):
        common.die("CHYBA: vyžaduje --feature --stack --into (--package u stacků s package_root; "
                   "+--variant --option).")

    root = find_agentic("templates/features")
    if not root:
        common.die("CHYBA: nenalezen templates/features/.")

    fpath = os.path.join(root, feat, "feature.yaml")
    if not os.path.isfile(fpath):
        print(f"Feature '{feat}' nenalezena ({fpath}).", file=sys.stderr)
        sys.exit(1)
    spec = yaml.safe_load(open(fpath, encoding="utf-8"))

    v = (spec.get("variants") or {}).get(variant)
    if not v:
        print(f"Varianta '{variant}' není v '{feat}'.", file=sys.stderr)
        sys.exit(1)
    apply = (v.get("apply") or {}).get(stack)
    if not apply:
        print(f"Stack '{stack}' nemá apply manifest (feature.yaml apply.{stack}). "
              f"Pro tenhle stack zatím není APPLY engine — generuj ze spec.", file=sys.stderr)
        sys.exit(1)

    impl_root = os.path.join(root, feat, "impl", stack)
    if not os.path.isdir(impl_root):
        print(f"Impl root nenalezen: {impl_root}", file=sys.stderr)
        sys.exit(1)

    pkg_from = apply.get("package_root")
    if pkg_from and not pkg_to:
        print(f"CHYBA: stack '{stack}' má package_root '{pkg_from}' → vyžaduje --package.", file=sys.stderr)
        sys.exit(2)
    pkg_path_from = pkg_from.replace(".", "/") if pkg_from else None
    pkg_path_to = pkg_to.replace(".", "/") if pkg_from else None
    wiring = apply.get("wiring", "none")

    common_blk = apply.get("common") or {}
    files = list(common_blk.get("files") or [])
    migs = list(common_blk.get("migrations") or [])
    if option:
        opt = (apply.get("options") or {}).get(option)
        if opt is None:
            print(f"Option '{option}' není v apply.{stack}.options.", file=sys.stderr)
            sys.exit(1)
        files += list(opt.get("files") or [])
        migs += list(opt.get("migrations") or [])

    written, placed = [], []

    for rel in files:
        src = os.path.join(impl_root, rel)
        if not os.path.isfile(src):
            print(f"CHYBA: chybí zdroj {src}", file=sys.stderr)
            sys.exit(2)
        content = open(src, encoding="utf-8").read()
        if pkg_from:
            content = content.replace(pkg_from, pkg_to)
        dest_rel = rel.replace(pkg_path_from, pkg_path_to) if pkg_from else rel
        dest = os.path.join(into, dest_rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(content)
        written.append(dest_rel)

    mig_dir = os.path.join(into, "contracts", "db", "migrations")
    os.makedirs(mig_dir, exist_ok=True)
    existing_nums = []
    for f in os.listdir(mig_dir):
        m = re.match(r"V(\d+)__", f)
        if m:
            existing_nums.append(int(m.group(1)))
    maxn = max(existing_nums, default=0)
    for rel in migs:
        src = os.path.join(impl_root, rel)
        if not os.path.isfile(src):
            print(f"CHYBA: chybí migrace {src}", file=sys.stderr)
            sys.exit(2)
        desc = re.sub(r"^V\d+__", "", os.path.basename(rel))
        maxn += 1
        name = f"V{maxn}__{desc}"
        shutil.copyfile(src, os.path.join(mig_dir, name))
        placed.append(name)

    print(f"apply-feature: {feat}/{variant} [{stack}] option={option or '-'} → {into}")
    print(f"  package: {pkg_from} → {pkg_to}" if pkg_from else "  package: generic (bez rename)")
    print(f"  soubory ({len(written)}):")
    for w in written:
        print(f"    + {w}")
    print(f"  migrace ({len(placed)}): {', '.join(placed) or '-'}")
    if wiring and wiring != "none":
        print(f"  ⚠ wiring='{wiring}' — tenhle stack vyžaduje wiring krok (není auto): viz impl README")


if __name__ == "__main__":
    main()
