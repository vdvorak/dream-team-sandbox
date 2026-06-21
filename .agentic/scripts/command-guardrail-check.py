#!/usr/bin/env python3
"""command-guardrail-check.py — SEKUNDÁRNÍ příkazový denylist checker (tool-agnostický).

Návrh: backlog/agent-command-guardrails.md §3d + §5 (vrstva 3, redundantní pojistka).

Vstup: command string (celá řádka, vč. pipe/&&/;/subshell). Výstup: allow | deny + reason.
Čte `policy/command-guardrails.yaml §deny_commands` + `§allow_through`. Chytá úzkou rodinu
stavově-destruktivních příkazů (git stash/reset/clean/checkout/rebase/cherry-pick/revert/
commit/force-push, přepis/rm engine stavu), kterou FS write-protection nepokrývá (operace
nad soubory, které agent vlastní legitimně, ale mutují celý tree/historii).

Deterministické jádro — stejný vstup → stejný výstup, žádný úsudek (constitution §Filozofie #7).
Žádná závislost na enginu. Žádné CLI-tool specifikum (nezná hook/settings.json/PreToolUse).

Rozhodovací pořadí (nad CELÝM stringem, ne jen jménem příkazu):
  1. allow_through — pokud kterýkoli vzor matchne → ALLOW (read-only / engine vstupní bod;
     přebíjí deny, aby `git stash list`, `cat current-run.md`, `run.sh done` prošly).
  2. deny_commands — pro každé pravidlo: pokud `match` matchne A `except` (je-li) NEmatchne
     → DENY + reason. První matchnuvší deny rozhoduje.
  3. jinak ALLOW.

FAIL-SAFE: vstup, který nelze bezpečně vyhodnotit (prázdný/nečitelný), je defaultně bezpečný
(ALLOW jen pokud žádné deny nematchne); chyba politiky → exit 1 (NEpovolit naslepo).
Pozn.: rozhodujeme nad celým stringem najednou — vzory v politice mají kotvy na hranice
příkazů (`^|[;&|(]`), takže `foo && git stash` se chytne i v řetězci.

Usage:
  command-guardrail-check.py --cmd "<command string>" [--policy <yaml>] [--json]
  command-guardrail-check.py "<command string>"          # cmd lze i poziční
  echo "<command>" | command-guardrail-check.py --stdin
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


def load_policy(policy_path: str | os.PathLike | None = None) -> dict:
    path = Path(policy_path) if policy_path else DEFAULT_POLICY
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"policy {path} není mapping")
    return data


def _compile_allow(policy: dict) -> list[re.Pattern]:
    return [re.compile(p) for p in (policy.get("allow_through") or [])]


def check_command(command: str, policy: dict) -> dict:
    """Rozhodne, zda je `command` povolen.

    Vrací dict: {allow: bool, rule: str|None, reason: str}.
    """
    cmd = command or ""

    # 1) allow_through přebíjí deny (read-only / engine vstupní bod)
    for pat in _compile_allow(policy):
        if pat.search(cmd):
            return {"allow": True, "rule": "allow_through",
                    "reason": "read-only / engine vstupní bod (allow_through)"}

    # 2) deny_commands — první matchnuvší (a except nematchnoucí) rozhoduje
    for rule in policy.get("deny_commands") or []:
        match_re = rule.get("match")
        if not match_re:
            continue
        if not re.search(match_re, cmd):
            continue
        except_re = rule.get("except")
        if except_re and re.search(except_re, cmd):
            continue  # výjimka (read-only varianta) → toto pravidlo neblokuje
        return {"allow": False, "rule": rule.get("id"),
                "reason": rule.get("reason") or f"zakázáno pravidlem {rule.get('id')}"}

    # 3) nic nematchlo → povoleno
    return {"allow": True, "rule": None, "reason": "neodpovídá žádnému deny vzoru"}


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SEKUNDÁRNÍ příkazový denylist checker.")
    ap.add_argument("cmd_pos", nargs="?", default=None, help="command string (poziční)")
    ap.add_argument("--cmd", default=None, help="command string")
    ap.add_argument("--stdin", action="store_true", help="načti command ze stdin")
    ap.add_argument("--policy", default=None, help=f"policy yaml (default: {DEFAULT_POLICY})")
    ap.add_argument("--json", action="store_true", help="výstup jako JSON")
    args = ap.parse_args(argv)

    if args.stdin:
        command = sys.stdin.read()
    else:
        command = args.cmd if args.cmd is not None else args.cmd_pos
    if command is None:
        print("ERROR: chybí command (--cmd / poziční / --stdin)", file=sys.stderr)
        return 1

    try:
        policy = load_policy(args.policy)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: nelze načíst politiku: {e}", file=sys.stderr)
        return 1
    try:
        result = check_command(command, policy)
    except re.error as e:
        # vadný regex v politice → fail-safe: neotvírat naslepo
        print(f"ERROR: vadný vzor v politice: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        verdict = "ALLOW" if result["allow"] else "DENY"
        print(f"{verdict}: {command.strip()}")
        print(f"  reason: {result['reason']}")
    return 0 if result["allow"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
