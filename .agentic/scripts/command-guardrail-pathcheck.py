#!/usr/bin/env python3
"""command-guardrail-pathcheck.py — PRIMÁRNÍ write-protection checker (tool-agnostický).

Návrh: backlog/agent-command-guardrails.md §3c + §5 (vrstva 2, primární linie).

Vstup: (agent-id, cílová write cesta). Výstup: allow | deny + reason.
Čte `policy/command-guardrails.yaml §write_protect`, vyhodnotí, zda daný agent smí
ZAPSAT do dané cesty. Toto je deterministické jádro path-blacklistu — stejný vstup →
stejný výstup, žádný úsudek (constitution §Filozofie #7).

POZICE V OBRANĚ: v kontejnerovém provozu je skutečné vynucení na FS (read-only mount/
práva); tenhle checker je tam reference/lint. V lokálním dev provozu (bez read-only mountu)
slouží jako podklad pro adaptérovou deny projekci / pre-write kontrolu. Žádná závislost na
enginu — čisté funkce + CLI vstup. Žádné CLI-tool specifikum (nezná hook/settings.json).

Sémantika:
  - skupiny write_protect se procházejí shora dolů; první skupina, jejíž `paths` matchnou
    cílovou cestu, ROZHODUJE (deterministicky, bez prolínání skupin).
  - matchnutá cesta je write-protected → zápis povolen JEN writeru skupiny:
      * writer == agent-id              → allow
      * writer == "engine" / "l3-maintainer" → deny pro KAŽDÉHO LLM agenta
        (engine = pseudo-agent jiného procesu; l3 = lidský maintainer přes gate)
      * writer == jiný agent-id         → deny
  - cesta, kterou nematchne žádná skupina → není chráněná → allow (mimo write-protection).

Glob: podporuje `**` (libovolný počet segmentů vč. nuly) a `*` (v rámci segmentu).
Cesty se normalizují (strip vedoucích `./`, sjednocení na `/`), porovnání case-sensitive.

Usage:
  command-guardrail-pathcheck.py --agent <id> --path <write-path> [--policy <yaml>] [--json]
  exit 0 = allow, exit 2 = deny, exit 1 = chyba vstupu/politiky.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
DEFAULT_POLICY = _HERE.parent / "policy" / "command-guardrails.yaml"

# writer, který reprezentuje lidský gate (L3 maintainer) — žádný automatizovaný caller
# (engine ani LLM agent) se mu nerovná → zápis projde jen přes lidský review, ne checkerem.
# Pozn.: `engine` NENÍ v této množině — engine-proces se identifikuje `--agent engine`
# a JE legitimní writer engine_runtime (§3c). LLM agent se nikdy nesmí identifikovat jako
# `engine`; to je hranice procesů (engine běží mimo agent-shell), ne věc tohoto checkeru.
_HUMAN_GATE_WRITERS = {"l3-maintainer"}


# ── glob → regex (deterministický překlad, žádný úsudek) ────────────────────────
def _glob_to_regex(pattern: str) -> re.Pattern:
    """Přeloží write_protect glob na regex. `**` = libovolné segmenty (vč. /),
    `*` = znaky kromě `/` v rámci segmentu. Ostatní znaky escapované doslovně."""
    pat = _norm_path(pattern)
    out = ["^"]
    i = 0
    while i < len(pat):
        c = pat[i]
        if c == "*":
            if pat[i:i + 2] == "**":
                # `**/` nebo `**` na konci → libovolný počet segmentů (i nula)
                if pat[i:i + 3] == "**/":
                    out.append(r"(?:.*/)?")
                    i += 3
                    continue
                out.append(r".*")
                i += 2
                continue
            out.append(r"[^/]*")
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    out.append("$")
    return re.compile("".join(out))


def _norm_path(p: str) -> str:
    """Normalizace cesty pro porovnání: sjednotit oddělovače, strip vedoucích ./ a /."""
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")
    return p


# ── load + core decision ────────────────────────────────────────────────────────
def load_policy(policy_path: str | os.PathLike | None = None) -> dict:
    path = Path(policy_path) if policy_path else DEFAULT_POLICY
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"policy {path} není mapping")
    return data


def _path_matches_group(target: str, paths: list[str]) -> bool:
    t = _norm_path(target)
    for pat in paths or []:
        if _glob_to_regex(pat).match(t):
            return True
    return False


def check_write(agent: str, target_path: str, policy: dict) -> dict:
    """Rozhodne, zda `agent` smí zapsat do `target_path`.

    Vrací dict: {allow: bool, group: str|None, writer: str|None, reason: str}.
    """
    wp = policy.get("write_protect") or {}
    for group_name, group in wp.items():
        if not isinstance(group, dict):
            continue
        if _path_matches_group(target_path, group.get("paths") or []):
            writer = group.get("writer")
            reason = group.get("reason") or f"cesta je write-protected ve skupině {group_name}"
            if writer in _HUMAN_GATE_WRITERS:
                # zápis jen přes lidský L3 review — žádný automatizovaný caller neprojde
                return {"allow": False, "group": group_name, "writer": writer,
                        "reason": f"{reason} (writer={writer} = lidský gate — '{agent}' read-only)"}
            if writer == agent:
                return {"allow": True, "group": group_name, "writer": writer,
                        "reason": f"'{agent}' je write-owner skupiny {group_name}"}
            return {"allow": False, "group": group_name, "writer": writer,
                    "reason": f"{reason} (write-owner={writer}, ne '{agent}')"}
    # žádná chráněná skupina nematchla → cesta není pod write-protection
    return {"allow": True, "group": None, "writer": None,
            "reason": "cesta není write-protected (mimo engine cesty)"}


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PRIMÁRNÍ write-protection checker (path-based).")
    ap.add_argument("--agent", required=True, help="agent-id, který chce zapisovat")
    ap.add_argument("--path", required=True, dest="target", help="cílová write cesta")
    ap.add_argument("--policy", default=None, help=f"policy yaml (default: {DEFAULT_POLICY})")
    ap.add_argument("--json", action="store_true", help="výstup jako JSON")
    args = ap.parse_args(argv)

    try:
        policy = load_policy(args.policy)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: nelze načíst politiku: {e}", file=sys.stderr)
        return 1

    result = check_write(args.agent, args.target, policy)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        verdict = "ALLOW" if result["allow"] else "DENY"
        print(f"{verdict}: {args.agent} write {args.target}")
        print(f"  reason: {result['reason']}")
    return 0 if result["allow"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
