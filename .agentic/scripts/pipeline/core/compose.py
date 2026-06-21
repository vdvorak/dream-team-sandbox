#!/usr/bin/env python3
"""compose.py — founding APPLY engine (z compose.sh).

Deterministicky složí projekt: copy scaffold + přepis base_package (cesta i obsah +
rootProject.name) + apply vybraných features (volá apply_feature). Tohle je dřív chybějící
APPLY vrstva foundingu (init-determinism.md). Stejné vstupy → byte-identický projekt.

CLI:   python3 compose.py --into <proj> --scaffold java-quarkus --name tasktracker \
                          [--package com.acme.tasks] [--feature auth --variant base --option jwt]
Exit:  0 = ok | 2 = chyba.
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import apply_feature
from common import find_agentic


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--into", default="")
    ap.add_argument("--scaffold", default="")
    ap.add_argument("--package", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--feature", default="")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--option", default="")
    args = ap.parse_args(argv)

    into, scaffold, pkg, name = args.into, args.scaffold, args.package, args.name
    if not (into and scaffold and name):
        common.die("CHYBA: vyžaduje --into --scaffold --name (volitelně --package --feature "
                   "--variant --option).")

    # base_package = f(název): bez --package odvoď deterministicky ze slugu názvu.
    if not pkg:
        slug = re.sub(r"[^a-z0-9]", "", name.lower())
        pkg = f"com.{slug}"

    sc_root = find_agentic(os.path.join("templates", "scaffolds", scaffold))
    if not sc_root:
        common.die(f"CHYBA: scaffold '{scaffold}' nenalezen.")

    # 1) copy scaffold s deterministickým přepisem package + rootProject.name
    pkg_from, path_from = "com.example.app", "com/example/app"
    pkg_path = pkg.replace(".", "/")
    count = 0
    for dirpath, dirnames, filenames in os.walk(sc_root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            s = os.path.join(dirpath, fn)
            rel = os.path.relpath(s, sc_root)
            dest_rel = rel.replace(path_from, pkg_path)
            dest = os.path.join(into, dest_rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                txt = open(s, encoding="utf-8").read()
            except (UnicodeDecodeError, ValueError):
                shutil.copyfile(s, dest)
                count += 1
                continue
            txt = txt.replace(pkg_from, pkg).replace(path_from, pkg_path)
            if fn == "settings.gradle":
                txt = re.sub(r"rootProject\.name\s*=\s*'[^']*'",
                             f"rootProject.name = '{name}-server'", txt)
            if fn == "application.properties":
                txt = re.sub(r"(?m)^(mp\.jwt\.verify\.issuer\s*=\s*).*$", r"\g<1>" + name, txt)
                txt = re.sub(r"(?m)^(smallrye\.jwt\.new-token\.issuer\s*=\s*).*$", r"\g<1>" + name, txt)
            open(dest, "w", encoding="utf-8").write(txt)
            count += 1
    print(f"compose: scaffold '{os.path.basename(sc_root)}' → {into}  "
          f"({count} souborů, package {pkg_from}→{pkg}, rootProject.name={name}-server)")

    # 2) apply vybrané feature (RESOLVE/APPLY split — volá apply_feature přímo)
    if args.feature:
        apply_feature.main(["--feature", args.feature, "--variant", args.variant,
                            "--stack", scaffold, "--option", args.option,
                            "--into", into, "--package", pkg])


if __name__ == "__main__":
    main()
