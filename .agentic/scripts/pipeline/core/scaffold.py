#!/usr/bin/env python3
"""scaffold.py — deterministicky resolvne scaffold(y) z manifestu (ze scaffold.sh).

Scaffold-passing: hlavní agent zjistí, který scaffold subagent potřebuje, a předá ho jako
typovaný artefakt `scaffold`. Místo aby AI hádala strukturu, dostane hotovou kostru.

CLI:   python3 scaffold.py [--backend X] [--frontend X] [--platform X] [--deploy X] [--agent] [--all]
Exit:  0 = nalezeno | 1 = nic nevyhovuje | 2 = chyba.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import find_agentic, yaml


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--backend", default="")
    ap.add_argument("--frontend", default="")
    ap.add_argument("--platform", default="")
    ap.add_argument("--deploy", default="")
    ap.add_argument("--agent", action="store_true")
    ap.add_argument("--all", dest="show_all", action="store_true")
    args = ap.parse_args(argv)

    manifest = find_agentic("templates/scaffolds/manifest.yaml")
    if not manifest:
        common.die("CHYBA: nenalezen templates/scaffolds/manifest.yaml.")

    man = yaml.safe_load(open(manifest, encoding="utf-8")) or {}
    scaffolds = man.get("scaffolds", {}) or {}
    bk, fe, pl, dp, ag = args.backend, args.frontend, args.platform, args.deploy, args.agent
    any_filter = any([bk, fe, pl, dp, ag])

    def matches(e):
        axis = e.get("axis")
        stack = e.get("stack")
        platforms = e.get("platforms") or []
        if bk and axis == "backend" and stack == bk:
            return True
        if fe and axis == "frontend" and stack == fe:
            return True
        if dp and axis == "deploy" and stack == dp:
            return True
        if ag and axis == "agent":
            return True
        if pl and (pl in platforms or (axis == "platform" and stack == pl)):
            return True
        return False

    hits = []
    for sid, e in scaffolds.items():
        ok = matches(e) if any_filter else True
        if ok and (args.show_all or e.get("status") == "ready"):
            hits.append((sid, e))

    if not hits:
        print("(žádný scaffold nevyhovuje" + (" — zkus --all pro planned)" if not args.show_all else ")"))
        sys.exit(1)

    for sid, e in hits:
        produces = ", ".join(e.get("produces") or []) or "-"
        docker = "docker-dev" if e.get("docker_dev") else "no-docker"
        print(f"{sid}  [{e.get('axis')}/{e.get('stack')}]  status:{e.get('status')}  {docker}")
        print(f"  path:     {e.get('path')}")
        print(f"  produces: {produces}")
        if e.get("newest"):
            print(f"  newest:   {e['newest']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
