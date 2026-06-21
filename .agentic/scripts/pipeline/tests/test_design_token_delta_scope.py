"""Regresní test design-token-scan.sh — grep-half design-auditu je PER-SOUBOR delta-scoped (N1).

ROOT CAUSE (vlna2-reskin): design-audit (Edna) skenoval CELÝ projekt → ~44 kontrastních /
hardcoded nálezů, VŠECHNY mimo deltu vlny (stará paleta v netknutých komponentách). To roztočilo
return-loop a shodilo circuit-breaker. Fix (N1, vzor code-lint/format-check delta-scope, commit
086ff73): grep-half (hardcoded barvy/px) skenuje jen změněné UI soubory; pre-existing dluh mimo
deltu nepadne (→ app-wide cleanup backlog, advisory). Screenshot-half (kontrast z renderu) řeší
Edna úsudkem nad delta seznamem, ne tímto skriptem.

Invariant (vynucuje constitution §Filozofie #7 + flow-gate-scoping FIX #1, AC-1/AC-2):
  • hardcoded barva v NEzměněné komponentě (mimo deltu) NESMÍ shodit audit-bránu,
  • hardcoded barva ve ZMĚNĚNÉ komponentě ji shodit MUSÍ,
  • bez --files = full-scan (zpětná kompat) najde i pre-existing,
  • prázdný delta (jen ne-UI soubory) → PASS (nic ke skenu),
  • tokens.css (definice tokenů) se NEskenuje (barvy tam SMÍ žít),
  • var(--color-*) použití NENÍ nález (legitimní token).

Hermetický: vytvoří tmp UI soubory v tmp_path, vede skript přes subprocess s --root tmp.
"""

import os
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
# tests/ → pipeline/ → scripts/ → design-token-scan.sh
_SCRIPTS = os.path.dirname(os.path.dirname(_HERE))
_SCAN = os.path.join(_SCRIPTS, "design-token-scan.sh")

# Hardcoded barva mimo token → nález. Token-použití → čisté.
_DIRTY_TSX = 'export const C = () => <div style={{ color: "#746C5D" }}>x</div>\n'
_CLEAN_TSX = 'export const C = () => <div className="ok">x</div>\n'
_DIRTY_CSS = ".badge { background: #ff0000; padding: 24px; }\n"
_CLEAN_CSS = ".badge { background: var(--color-bg); padding: var(--space-md); }\n"


def _write(root, files):
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)


def _run(root, files_list=None, added_lines=None):
    cmd = ["bash", _SCAN, "--root", str(root)]
    if files_list is not None:
        listfile = os.path.join(str(root), "_delta.txt")
        with open(listfile, "w") as fh:
            fh.write("\n".join(files_list) + ("\n" if files_list else ""))
        cmd += ["--files", listfile]
    if added_lines is not None:
        mapfile = os.path.join(str(root), "_added.txt")
        with open(mapfile, "w") as fh:
            fh.write("\n".join(added_lines) + ("\n" if added_lines else ""))
        cmd += ["--added-lines", mapfile]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))


# ── REGRESE: jádro N1 ─────────────────────────────────────────────────────────────────
def test_preexisting_hardcoded_outside_delta_does_not_fail(tmp_path):
    """Hardcoded barva ve staré NEDOTČENÉ komponentě (mimo deltu) NESMÍ shodit design-audit.
    To je přesně vlna2-reskin: ~44 nálezů mimo deltu roztočilo circuit-breaker."""
    _write(tmp_path, {"src/Legacy.tsx": _DIRTY_TSX, "src/New.tsx": _CLEAN_TSX})
    res = _run(tmp_path, files_list=["src/New.tsx"])
    assert res.returncode == 0, (
        f"pre-existing hardcoded barva mimo deltu shodila audit:\n{res.stdout}\n{res.stderr}"
    )
    assert "Legacy.tsx" not in res.stdout, "Legacy.tsx skenován, ač není v deltě"


def test_changed_component_with_hardcoded_does_fail(tmp_path):
    """Hardcoded barva ve ZMĚNĚNÉ komponentě (v deltě) audit-bránu shodit MUSÍ."""
    _write(tmp_path, {"src/Legacy.tsx": _DIRTY_TSX, "src/New.tsx": _CLEAN_TSX})
    res = _run(tmp_path, files_list=["src/Legacy.tsx"])
    assert res.returncode != 0, (
        f"hardcoded barva v deltě neshodila audit:\n{res.stdout}\n{res.stderr}"
    )
    assert "Legacy.tsx" in res.stdout
    assert "HARDCODED_COLOR" in res.stdout


def test_changed_css_with_hardcoded_px_and_color(tmp_path):
    """Změněný CSS s hardcoded barvou i px → nález (px = kandidát na --space-* token)."""
    _write(tmp_path, {"src/badge.css": _DIRTY_CSS})
    res = _run(tmp_path, files_list=["src/badge.css"])
    assert res.returncode != 0
    assert "HARDCODED_COLOR" in res.stdout
    assert "HARDCODED_PX" in res.stdout


# ── zpětná kompatibilita + hrany ────────────────────────────────────────────────────
def test_full_scan_still_catches_preexisting(tmp_path):
    """Bez --files = full-scan → pre-existing hardcoded barva stále nalezena (vědomý úklid)."""
    _write(tmp_path, {"src/Legacy.tsx": _DIRTY_TSX, "src/New.tsx": _CLEAN_TSX})
    res = _run(tmp_path, files_list=None)
    assert res.returncode != 0
    assert "Legacy.tsx" in res.stdout


def test_empty_delta_skips(tmp_path):
    """Delta bez UI zdrojáku (jen .md) → nic ke skenu, PASS."""
    _write(tmp_path, {"src/Legacy.tsx": _DIRTY_TSX, "README.md": "# doc\n"})
    res = _run(tmp_path, files_list=["README.md"])
    assert res.returncode == 0
    assert "Legacy.tsx" not in res.stdout
    assert "prázdný" in res.stdout


def test_token_usage_is_not_a_finding(tmp_path):
    """var(--color-*) / var(--space-*) je legitimní token → žádný nález."""
    _write(tmp_path, {"src/clean.css": _CLEAN_CSS})
    res = _run(tmp_path, files_list=["src/clean.css"])
    assert res.returncode == 0, f"token-použití hlášeno jako nález:\n{res.stdout}"


def test_tokens_css_definitions_not_scanned(tmp_path):
    """tokens.css drží DEFINICE tokenů (barvy tam SMÍ žít) → neskenuje se ani v deltě."""
    _write(tmp_path, {"src/tokens.css": ":root { --color-bg: #112233; --space-md: 16px; }\n"})
    res = _run(tmp_path, files_list=["src/tokens.css"])
    assert res.returncode == 0, f"tokens.css (definice) shodil audit:\n{res.stdout}"
    assert "prázdný" in res.stdout


def test_mixed_delta_only_scans_changed(tmp_path):
    """Delta = clean.tsx i když Legacy.tsx (špinavý) leží ve STEJNÉM adresáři → PASS.
    Dokazuje per-SOUBOR filtr (ne per-adresář)."""
    _write(tmp_path, {"src/Legacy.tsx": _DIRTY_TSX, "src/New.tsx": _CLEAN_TSX})
    res = _run(tmp_path, files_list=["src/New.tsx"])
    assert res.returncode == 0, f"per-soubor filtr selhal:\n{res.stdout}"
    assert "Legacy.tsx" not in res.stdout


# ── REGRESE: jádro N5 — per-HUNK scope (řádková granularita uvnitř dotčeného souboru) ──────────
# ROOT CAUSE (#4b): vlna sáhla na FlowTab.css kvůli 3 NOVÝM pravidlům, ale per-soubor grep vynořil
# i ~41 STARÝCH hardcoded px z #4a jako „in-delta" → falešná blokace. Edna to ve #4b zachránila
# úsudkem (posoudila jen +řádky git diffu), ale spoléhat na auditorův úsudek je křehké. N5: skript
# bere added-lines mapu (path:lineno přidaných řádků) → starý dluh v dotčeném souboru NEpadne,
# nový (+řádek) ano. Mapu počítá preflight z `git diff --unified=0`; skener git nečte.

# CSS se starým dluhem (řádky 1-2) i novým hardcoded řádkem (řádek 4).
_MIXED_DEBT_CSS = (
    ".old-a { color: #111111; padding: 24px; }\n"  # řádek 1 — pre-existing dluh
    ".old-b { color: #222222; margin: 32px; }\n"  # řádek 2 — pre-existing dluh
    ".clean { color: var(--color-x); }\n"  # řádek 3 — čistý
    ".new { color: #ff0000; padding: 48px; }\n"  # řádek 4 — NOVÝ hardcoded (vlna ho přidala)
)


def test_preexisting_debt_in_touched_file_suppressed_new_line_blocks(tmp_path):
    """N5 jádro: soubor je V DELTĚ, ale jen řádek 4 byl přidán vlnou. Starý dluh (řádky 1-2)
    se NEvynoří jako blocking; nový hardcoded řádek 4 bránu shodit MUSÍ. Přesně FlowTab.css #4b."""
    _write(tmp_path, {"src/FlowTab.css": _MIXED_DEBT_CSS})
    res = _run(
        tmp_path,
        files_list=["src/FlowTab.css"],
        added_lines=["src/FlowTab.css:4"],  # jen řádek 4 přidán vlnou
    )
    assert res.returncode != 0, (
        f"nový hardcoded řádek v deltě neshodil bránu:\n{res.stdout}\n{res.stderr}"
    )
    assert "FlowTab.css:4:" in res.stdout, "řádek 4 (nový) chybí v nálezech"
    assert "FlowTab.css:1:" not in res.stdout, "starý dluh řádek 1 vynořen jako blocking (per-hunk selhal)"
    assert "FlowTab.css:2:" not in res.stdout, "starý dluh řádek 2 vynořen jako blocking (per-hunk selhal)"
    assert "POTLAČENO" in res.stderr, "potlačení pre-existing dluhu se neoznámilo"


def test_touched_file_only_preexisting_debt_no_added_token_line_passes(tmp_path):
    """Soubor v deltě, ale přidané řádky NEmají token nález (přidalo se jen čisté pravidlo).
    Veškerý hardcoded je pre-existing → brána PASS (vlna nezavlekla nový dluh)."""
    _write(tmp_path, {"src/FlowTab.css": _MIXED_DEBT_CSS})
    res = _run(
        tmp_path,
        files_list=["src/FlowTab.css"],
        added_lines=["src/FlowTab.css:3"],  # přidán jen čistý řádek 3
    )
    assert res.returncode == 0, (
        f"pre-existing dluh v dotčeném souboru shodil bránu:\n{res.stdout}\n{res.stderr}"
    )
    assert "čisto" in res.stdout


def test_whole_file_marker_scans_all_lines(tmp_path):
    """Nový soubor (path:* v mapě) nemá bázi → celý je „přidaný" → všechny řádky in-delta."""
    _write(tmp_path, {"src/FlowTab.css": _MIXED_DEBT_CSS})
    res = _run(
        tmp_path,
        files_list=["src/FlowTab.css"],
        added_lines=["src/FlowTab.css:*"],
    )
    assert res.returncode != 0
    assert "FlowTab.css:1:" in res.stdout, "nový soubor: řádek 1 měl být in-delta"
    assert "FlowTab.css:4:" in res.stdout


def test_no_added_lines_map_keeps_per_file_behavior(tmp_path):
    """Bez --added-lines = zpětná kompat: per-SOUBOR (všechny řádky dotčeného souboru = nález)."""
    _write(tmp_path, {"src/FlowTab.css": _MIXED_DEBT_CSS})
    res = _run(tmp_path, files_list=["src/FlowTab.css"])  # bez added_lines
    assert res.returncode != 0
    assert "FlowTab.css:1:" in res.stdout, "bez mapy musí padnout per-soubor (i starý řádek)"
