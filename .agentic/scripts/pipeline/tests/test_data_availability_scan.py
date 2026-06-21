"""Regresní test N2 — raná data-availability kontrola (ADVISORY).

ROOT CAUSE (re-skin vlna): AC chtěla zobrazit data (last_output, počty, kategorie agenta), která
appka v kontraktech NEMĚLA → spec-gate se zacyklil 5 kol (engine to našel po dávkách, ne najednou).
Fix (N2): data-availability-scan.sh — z acceptance/<feature>.md vytáhne jmenovaná datová pole,
porovná s GLOBÁLNÍ množinou krytí (OpenAPI properties rekurzivně + TS type pole), nahlásí pole bez
krytí. ADVISORY: vždy exit 0 (neblokuje — L3 PO 2026-06-19); skript dá PRIOR, Sheldon/Vision soudí.

Invariant:
  • AC pole jmenované v backticku, které NENÍ v kontraktu/typu → marker `data-availability: MISSING`,
  • AC plně krytá (každé pole v kontraktu nebo typu) → `data-availability: OK`,
  • robustnost vůči $ref/allOf: pole definované ve vnořeném/odkazovaném schématu = kryté,
  • skript NIKDY neblokuje (exit 0 i při MISSING),
  • šum (UPPERCASE konstanty, PascalCase názvy, test_*) se NEhlásí jako pole.

Hermetický: staví minimální acceptance/ + contracts/api/ + types/ v tmp_path.
"""

import os
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(os.path.dirname(_HERE))
_SCAN = os.path.join(_SCRIPTS, "data-availability-scan.sh")

pytestmark = pytest.mark.skipif(
    shutil.which("python3") is None,
    reason="python3 nedostupný — data-availability-scan nelze ověřit",
)


def _yaml_available():
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        return False


def _setup(root, *, acceptance=None, contracts=None, types=None):
    """Postav tmp projekt: acceptance/<f>.md, contracts/api/<f>.openapi.yaml, types/<f>.ts."""
    for rel, content in (acceptance or {}).items():
        p = os.path.join(root, "acceptance", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(content)
    for rel, content in (contracts or {}).items():
        p = os.path.join(root, "contracts", "api", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(content)
    for rel, content in (types or {}).items():
        p = os.path.join(root, "clients", "web", "src", "types", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(content)


def _run(root):
    return subprocess.run(["bash", _SCAN, "--root", str(root)],
                          capture_output=True, text=True, cwd=str(root))


# ── jádro N2 ─────────────────────────────────────────────────────────────────────
def test_ac_field_without_coverage_is_missing(tmp_path):
    """AC jmenuje `last_output`, kontrakt ho nemá → MISSING (advisory, exit 0)."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"widget.md": "## AC-1\nDlaždice zobrazí `last_output` posledního kroku.\n"},
        contracts={"widget.openapi.yaml": (
            "openapi: 3.1.0\ncomponents:\n  schemas:\n    Widget:\n      type: object\n"
            "      properties:\n        status:\n          type: string\n"
        )},
    )
    res = _run(tmp_path)
    assert res.returncode == 0, f"advisory skript nesmí blokovat:\n{res.stderr}"
    assert "data-availability: MISSING" in res.stdout
    assert "last_output" in res.stdout


def test_ac_fully_covered_is_ok(tmp_path):
    """AC jmenuje `status`, kontrakt ho má → OK."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"widget.md": "## AC-1\nDlaždice zobrazí `status` kroku.\n"},
        contracts={"widget.openapi.yaml": (
            "openapi: 3.1.0\ncomponents:\n  schemas:\n    Widget:\n      type: object\n"
            "      properties:\n        status:\n          type: string\n"
        )},
    )
    res = _run(tmp_path)
    assert res.returncode == 0
    assert "data-availability: OK" in res.stdout
    assert "MISSING" not in res.stdout


def test_field_covered_by_ts_type(tmp_path):
    """Pole nekryté kontraktem, ale přítomné v TS typu → kryté (OK)."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"widget.md": "## AC-1\nZobraz `assignee`.\n"},
        contracts={"other.openapi.yaml": "openapi: 3.1.0\ncomponents: {}\n"},
        types={"widget.ts": "export interface Widget {\n  assignee: string\n}\n"},
    )
    res = _run(tmp_path)
    assert res.returncode == 0
    assert "data-availability: OK" in res.stdout


def test_nested_ref_schema_field_is_covered(tmp_path):
    """Robustnost vůči $ref/allOf: pole definované ve vnořeném schématu (vlastní properties blok)
    se započítá do globální množiny krytí → AC pole z něj je OK, ne MISSING."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"widget.md": "## AC-1\nZobraz `nested_field`.\n"},
        contracts={"widget.openapi.yaml": (
            "openapi: 3.1.0\ncomponents:\n  schemas:\n"
            "    Outer:\n      allOf:\n        - $ref: '#/components/schemas/Inner'\n"
            "    Inner:\n      type: object\n      properties:\n"
            "        nested_field:\n          type: string\n"
        )},
    )
    res = _run(tmp_path)
    assert res.returncode == 0
    assert "data-availability: OK" in res.stdout, f"vnořené schéma pole nehlášeno jako kryté:\n{res.stdout}"


def test_noise_tokens_not_reported(tmp_path):
    """Šum se nehlásí jako pole: UPPERCASE konstanta, PascalCase typ, test_ prefix."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"widget.md": (
            "## AC-1\nChyba `ERR_TOKEN_INVALID`, komponenta `StatusBadge`, test `test_widget`.\n"
        )},
        contracts={"widget.openapi.yaml": "openapi: 3.1.0\ncomponents: {}\n"},
    )
    res = _run(tmp_path)
    assert res.returncode == 0
    assert "ERR_TOKEN_INVALID" not in res.stdout
    assert "StatusBadge" not in res.stdout
    assert "test_widget" not in res.stdout
    assert "data-availability: OK" in res.stdout


def test_advisory_never_blocks(tmp_path):
    """Advisory invariant: i s nálezem MISSING je exit 0 (neblokuje start)."""
    if not _yaml_available():
        pytest.skip("PyYAML nedostupný")
    _setup(
        tmp_path,
        acceptance={"w.md": "## AC\nZobraz `missing_field` a `another_missing`.\n"},
        contracts={"w.openapi.yaml": "openapi: 3.1.0\ncomponents: {}\n"},
    )
    res = _run(tmp_path)
    assert res.returncode == 0, "advisory skript MUSÍ vrátit 0 i při MISSING (neblokuje)"
    assert "MISSING" in res.stdout
