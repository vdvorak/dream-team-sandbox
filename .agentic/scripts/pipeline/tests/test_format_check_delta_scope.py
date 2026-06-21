"""Regresní test format-check.sh — delta scope je PER-SOUBOR, ne per-adresář.

ROOT CAUSE (padlo 4×): touched() byl boolean na ADRESÁŘ → po prvním změněném souboru ve stacku
se pustil lint na CELÝ adresář (ruff check ., prettier "src/**", eslint .) a ignoroval seznam
změněných souborů → tahal pre-existing format dluh mimo deltu vlny. Fix: každá stack větev dostane
přímý seznam změněných souborů (delta ∩ stack ∩ přípony) a nástroj kontroluje JEN je.

Invariant (vynucuje constitution I4 + flow-gate-scoping-contract.md FIX #1, AC-1/AC-2):
  • pre-existing problém v NEzměněném souboru (mimo deltu) NESMÍ shodit bránu,
  • změněný soubor s problémem ji shodit MUSÍ,
  • bez --files = full-scan (zpětná kompatibilita) najde i pre-existing,
  • prázdný per-stack průnik → stack se přeskočí (PASS).

Test je hermetický: vytvoří dočasný python projekt (pyproject.toml) v tmp_path, takže neskenuje
reálné repo. Vede `format-check.sh` přes subprocess s `--root tmp` a synthetic --files seznamem.
Stack = python/ruff, protože ruff je deterministický a je to jediný formatter dostupný offline
bez node_modules. Per-soubor logika ve `stack_files()` je sdílená pro všechny stacky (jeden helper).
"""

import os
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
# tests/ → pipeline/ → scripts/ → format-check.sh
_SCRIPTS = os.path.dirname(os.path.dirname(_HERE))
_FORMAT_CHECK = os.path.join(_SCRIPTS, "format-check.sh")

# Pre-existing dluh: tělo se shoduje, ale formát ne (ruff format by ho přepsal) → "Would reformat".
_DIRTY = "x=1\ndef  foo( ):\n  return    x\n"
# Čistý soubor: ruff format ho nesahne, ruff check projde.
_CLEAN = "x = 1\n\n\ndef foo():\n    return x\n"

pytestmark = pytest.mark.skipif(
    shutil.which("ruff") is None and shutil.which("python3") is None,
    reason="ruff ani python3 -m ruff není dostupný — format-check python větev nelze ověřit",
)


def _project(root, files):
    """Vytvoř minimální python projekt (pyproject.toml + src/<files>) v `root`. files: {relpath: obsah}."""
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    with open(os.path.join(root, "pyproject.toml"), "w") as fh:
        fh.write('[project]\nname = "demo"\nversion = "0.1.0"\n')
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)


def _run(root, files_list=None):
    """Spusť format-check.sh nad `root`. files_list = seznam relativních cest (delta) nebo None (full)."""
    cmd = ["bash", _FORMAT_CHECK, "--root", str(root)]
    if files_list is not None:
        listfile = os.path.join(str(root), "_delta.txt")
        with open(listfile, "w") as fh:
            fh.write("\n".join(files_list) + ("\n" if files_list else ""))
        cmd += ["--files", listfile]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))


# ── REGRESE: jádro bugu ─────────────────────────────────────────────────────────────
def test_preexisting_debt_outside_delta_does_not_fail(tmp_path):
    """Špinavý legacy.py MIMO deltu nesmí bránu shodit (delta = jen čistý clean.py). To je přesně
    scénář, který padl 4×: touched() viděl dotčený adresář a lintoval celý → legacy.py spadl."""
    _project(tmp_path, {"src/legacy.py": _DIRTY, "src/clean.py": _CLEAN})
    res = _run(tmp_path, files_list=["src/clean.py"])
    assert res.returncode == 0, (
        f"pre-existing dluh mimo deltu shodil bránu:\n{res.stdout}\n{res.stderr}"
    )
    assert "legacy.py" not in res.stdout, "legacy.py byl skenován, ač není v deltě"
    assert "fails=0" in res.stdout


def test_changed_file_with_debt_does_fail(tmp_path):
    """Špinavý soubor V deltě bránu shodit MUSÍ (jinak by delta-scope propustil reálnou vadu vlny)."""
    _project(tmp_path, {"src/legacy.py": _DIRTY, "src/clean.py": _CLEAN})
    res = _run(tmp_path, files_list=["src/legacy.py"])
    assert res.returncode != 0, (
        f"špinavý soubor v deltě neshodil bránu:\n{res.stdout}\n{res.stderr}"
    )
    assert "legacy.py" in res.stdout
    assert "fails=1" in res.stdout


# ── zpětná kompatibilita + hrany ────────────────────────────────────────────────────
def test_full_scan_still_catches_preexisting(tmp_path):
    """Bez --files = full-scan (dnešní chování) → pre-existing dluh stále nalezen (exit≠0)."""
    _project(tmp_path, {"src/legacy.py": _DIRTY, "src/clean.py": _CLEAN})
    res = _run(tmp_path, files_list=None)
    assert res.returncode != 0
    assert "legacy.py" in res.stdout


def test_empty_delta_skips_stack(tmp_path):
    """Delta bez relevantního zdrojáku (jen .md) → python stack se přeskočí, brána PASS."""
    _project(tmp_path, {"src/legacy.py": _DIRTY})
    (tmp_path / "README.md").write_text("# doc\n")
    res = _run(tmp_path, files_list=["README.md"])
    assert res.returncode == 0
    assert "mimo delta, přeskočeno" in res.stdout
    assert "legacy.py" not in res.stdout


def test_mixed_delta_only_scans_changed(tmp_path):
    """Delta = clean.py (čistý) i když legacy.py (špinavý) leží ve STEJNÉM adresáři → PASS.
    Dokazuje per-SOUBOR filtr: dotčený adresář NEznamená lint celého adresáře."""
    _project(tmp_path, {"src/legacy.py": _DIRTY, "src/clean.py": _CLEAN})
    res = _run(tmp_path, files_list=["src/clean.py"])
    assert res.returncode == 0, f"per-soubor filtr selhal — adresář lintnut celý:\n{res.stdout}"
    assert "legacy.py" not in res.stdout
