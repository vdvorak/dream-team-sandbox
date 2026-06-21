"""Regresní test agent-graph-check.sh §7 — tools ↔ write-scope konzistence (N7).

ROOT CAUSE (N6): read-only auditor (Edna, Heimdall) mohl v definici deklarovat `write-scope`
na soubor, do kterého reálně NEMÁ Write/Edit (read-only agenti dostávají od generátoru wrapperů
jen Read/Glob/Grep/Bash). Drift „definice slibuje zápis, tool ho nedovolí" se nezachytil
deterministicky — musel ho najít člověk. N7 přidává tvrdou bránu.

Invariant (N7):
  • read-only agent (short ∈ READONLY v setup-claude-code.sh) smí mít write-scope
    nanejvýš sdílený allowlist (handoffs/**, STATE.md) = svůj envelope/výstup,
  • jakýkoli jiný write CÍL u read-only agenta → FAIL (exit≠0, jmenuje agenta + cestu),
  • vyloučené (EXCL:) cesty v závorkách / za negací se NEpočítají (kontext, orchestrátor),
  • generující agent (NE v READONLY) smí mít libovolný write-scope (N7 ho ignoruje).

Test je hermetický: postaví minimální .agentic-like strom (agents/ + pipeline/delivery.yaml +
agents/INDEX.md + scripts/setup/setup-claude-code.sh se stub READONLY množinou) v tmp_path a
vede REÁLNÝ agent-graph-check.sh přes subprocess. Verdikt z N7 se izoluje na bloku [7] výstupu,
protože minimální strom záměrně triggeruje i N1 findings (persony bez grafových bindingů) — to
N7 invariant nezajímá; testujeme jen sekci [7].
"""

import os
import shutil
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
# tests/ → pipeline/ → scripts/ → agent-graph-check.sh
_SCRIPTS = os.path.dirname(os.path.dirname(_HERE))
_CHECK = os.path.join(_SCRIPTS, "agent-graph-check.sh")

_SETUP_STUB = 'READONLY = {"ro-good", "ro-bad", "ro-excl"}\n'

# Read-only auditor se scope jen handoffs/** → N7 PASS.
_RO_GOOD = """---
name: RoGood
role: Auditor
short: ro-good
transformations: [gate]
cache_key: x
---
- **Write scope**: `handoffs/**` (jinak read-only).
"""

# Read-only auditor s reálným write cílem mimo allowlist → N7 FAIL.
_RO_BAD = """---
name: RoBad
role: Auditor
short: ro-bad
transformations: [gate]
cache_key: x
---
- **Write scope**: `specs/**`, `handoffs/**`.
"""

# Read-only auditor s cestou JEN v závorce / za negací (kontext, ne write cíl) → N7 PASS.
# Reprodukuje reálný vzor Heimdall/Edna: víceřádková závorka „… do `audit/x.md` píše orchestrátor".
_RO_EXCL = """---
name: RoExcl
role: Auditor
short: ro-excl
transformations: [gate]
cache_key: x
---
- **Write scope**: `handoffs/**` (jinak read-only — audit-log do
  `audit/destructive-ops.md` persistuje orchestrátor).
"""

# Generující agent (NE v READONLY) s reálným write-scope → N7 ho ignoruje (PASS pro N7).
_GEN = """---
name: Gen
role: Backend
short: gen-be
transformations: [t2]
cache_key: x
---
- **Write scope**: `server/**`, `handoffs/**`.
"""


def _tree(root, agents):
    """Postav minimální .agentic-like strom. `agents`: {short: obsah md}."""
    for sub in ("agents", "pipeline", os.path.join("scripts", "setup")):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "scripts", "setup", "setup-claude-code.sh"), "w") as fh:
        fh.write(_SETUP_STUB)
    with open(os.path.join(root, "pipeline", "delivery.yaml"), "w") as fh:
        fh.write("nodes: []\n")
    with open(os.path.join(root, "agents", "INDEX.md"), "w") as fh:
        fh.write("# Cast\n")
    for short, content in agents.items():
        with open(os.path.join(root, "agents", f"{short}.md"), "w") as fh:
            fh.write(content)
    # reálný skript do stromu (fallback layout: cwd má agents/, pipeline/, scripts/)
    shutil.copy(_CHECK, os.path.join(root, "scripts", "agent-graph-check.sh"))


def _run(root):
    """Spusť check z `root` (fallback layout). Vrať (rc, stdout)."""
    res = subprocess.run(
        ["bash", os.path.join(root, "scripts", "agent-graph-check.sh")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    return res.returncode, res.stdout + res.stderr


def _n7_block(out):
    """Vyřízni jen sekci [7] z výstupu (mezi '[7]' a dalším '---')."""
    lines = out.splitlines()
    start = next((i for i, ln in enumerate(lines) if "[7]" in ln), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), len(lines))
    return "\n".join(lines[start:end])


def test_n7_fails_readonly_with_real_write_scope(tmp_path):
    """Read-only agent s write-scope mimo allowlist → N7 FAIL, jmenuje agenta + cestu."""
    _tree(tmp_path, {"ro-bad": _RO_BAD})
    rc, out = _run(tmp_path)
    block = _n7_block(out)
    assert "FAIL" in block, f"N7 nezachytil read-only write-scope drift:\n{out}"
    assert "ro-bad" in block, f"N7 nejmenuje viníka:\n{out}"
    assert "specs/**" in block, f"N7 nejmenuje porušenou cestu:\n{out}"
    assert rc != 0, "check musí skončit nenulově (použitelný jako brána)"


def test_n7_passes_auditor_handoffs_only(tmp_path):
    """Read-only auditor s write-scope jen handoffs/** → N7 PASS (žádný FAIL v sekci [7])."""
    _tree(tmp_path, {"ro-good": _RO_GOOD})
    _, out = _run(tmp_path)
    block = _n7_block(out)
    assert "FAIL" not in block, f"N7 falešně shodil handoffs-only auditor:\n{out}"
    assert "ok" in block.lower(), f"N7 nehlásí ok:\n{out}"


def test_n7_ignores_parenthesized_context_paths(tmp_path):
    """Cesta jen v (víceřádkové) závorce = kontext/orchestrátor, ne write cíl → N7 PASS."""
    _tree(tmp_path, {"ro-excl": _RO_EXCL})
    _, out = _run(tmp_path)
    block = _n7_block(out)
    assert "FAIL" not in block, f"N7 falešně bral kontext v závorce jako write cíl:\n{out}"


def test_n7_ignores_generating_agent(tmp_path):
    """Generující agent (NE read-only) s reálným write-scope → N7 ho neřeší (žádný FAIL)."""
    _tree(tmp_path, {"gen-be": _GEN})
    _, out = _run(tmp_path)
    block = _n7_block(out)
    assert "FAIL" not in block, f"N7 nesmí omezovat generujícího agenta:\n{out}"
