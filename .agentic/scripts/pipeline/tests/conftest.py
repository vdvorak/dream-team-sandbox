"""conftest.py — unit-vrstva nad doménovým modelem enginu (predicate/graph/runstate).

Přidá core/ na sys.path (core moduly importují sourozence: `from common import …`) a nabídne
sdílený `make_ctx` factory = duck-type EvalContext pro `Predicate.evaluate` / `Node.is_active`.

Tahle vrstva je DEV-only: leží mimo distribuční globy (`pipeline/*.sh`, `core/*.py`), takže
se NErozesílá do .agentic/ projektů ani do jejich CI. Integrační guard zůstává selftest.sh;
tohle je jemnozrnný unit guard nad čistými (bez I/O) doménovými třídami.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)


class FakeCtx:
    """Minimální EvalContext (duck-type frontier.Ctx). `flag()` vrací surovou hodnotu z
    `flags` dictu — reálná Ctx navrch řeší flag-resolution politiku (touches_db→has_db,
    design_source→author…), ta sem nepatří: tady testujeme logiku ATOMU pro daný vstup.
    `role_status`/`agent_status` drží Node.is_active aktivační gating."""

    def __init__(self, flags=None, cls=None, outcome=None, role_status=None, agent_status=None):
        self.flags = dict(flags or {})
        self.cls = cls
        self.outcome = outcome
        self.role_status = dict(role_status or {})
        self.agent_status = dict(agent_status or {})

    def flag(self, name):
        return self.flags.get(name)


@pytest.fixture
def make_ctx():
    """Factory: make_ctx(flags={…}, outcome="FAIL", cls="feature", role_status={…})."""
    def _make(**kw):
        return FakeCtx(**kw)
    return _make
