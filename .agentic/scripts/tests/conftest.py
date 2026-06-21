"""conftest.py — unit vrstva nad guardrail checkery (scripts/command-guardrail-*.py).

Checkery jsou čisté tool-agnostické moduly (PyYAML + re), bez závislosti na enginu.
Tahle vrstva je DEV-only (leží mimo distribuční globy pipeline) — jemnozrnný unit guard
nad deterministickými rozhodovacími funkcemi (check_write / check_command).

Checker soubory mají pomlčky v názvu (konvence scripts/), proto je importujeme přes
importlib z absolutní cesty a vystavíme jako fixture (`pathcheck`, `cmdcheck`, `policy`).
"""
import importlib.util
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
POLICY_PATH = _SCRIPTS.parent / "policy" / "command-guardrails.yaml"


def _load_module(filename: str, modname: str):
    path = _SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def pathcheck():
    return _load_module("command-guardrail-pathcheck.py", "cg_pathcheck")


@pytest.fixture(scope="session")
def cmdcheck():
    return _load_module("command-guardrail-check.py", "cg_cmdcheck")


@pytest.fixture(scope="session")
def policy(pathcheck):
    """Reálná projektová politika (zdroj pravdy) — testy validují i obsah, ne jen logiku."""
    return pathcheck.load_policy(str(POLICY_PATH))
