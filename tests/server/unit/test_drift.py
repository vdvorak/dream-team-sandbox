"""Unit testy — drift-detekce (hash match/mismatch, re-pin, fail-closed).

Acceptance vazba: CE-6 (viditelná drift, žádný tichý sync), I11, CE-2 (fail-closed).
"""

import pytest

from server.cage.deploy import drift
from server.cage.deploy.drift import WORKSPACE_DEF_FILES
from server.cage.errors import CageDriftError


def _make_fake_app_repo(tmp_path, marker="v1"):
    """Vytvoří fake appkové workspace-def soubory s daným markerem (pro hash variaci)."""
    for rel in WORKSPACE_DEF_FILES:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {rel}\ncontent-{marker}\n")
    return tmp_path


def test_first_deploy_pins_hash(tmp_path):
    app = _make_fake_app_repo(tmp_path / "app")
    lock = tmp_path / "cage-deploy.lock"
    h = drift.check_drift(app, lock, accept_drift=False)
    assert lock.is_file()
    assert drift.read_pinned_hash(lock) == h


def test_unchanged_def_passes(tmp_path):
    app = _make_fake_app_repo(tmp_path / "app")
    lock = tmp_path / "cage-deploy.lock"
    h1 = drift.check_drift(app, lock)
    h2 = drift.check_drift(app, lock)  # nic se nezměnilo
    assert h1 == h2


def test_drift_fails_closed_without_accept(tmp_path):
    app = _make_fake_app_repo(tmp_path / "app", marker="v1")
    lock = tmp_path / "cage-deploy.lock"
    drift.check_drift(app, lock)  # pin v1
    # appka změní workspace definici (drift)
    _make_fake_app_repo(app, marker="v2")
    # Fail-closed (CE-6): bez --accept-drift → deploy FAIL.
    with pytest.raises(CageDriftError):
        drift.check_drift(app, lock, accept_drift=False)


def test_accept_drift_repins(tmp_path):
    app = _make_fake_app_repo(tmp_path / "app", marker="v1")
    lock = tmp_path / "cage-deploy.lock"
    drift.check_drift(app, lock)
    pinned_v1 = drift.read_pinned_hash(lock)
    _make_fake_app_repo(app, marker="v2")
    # Vědomý re-pin (operátor re-reviewoval overlay).
    h2 = drift.check_drift(app, lock, accept_drift=True)
    assert h2 != pinned_v1
    assert drift.read_pinned_hash(lock) == h2


def test_missing_def_file_fails_closed(tmp_path):
    app = _make_fake_app_repo(tmp_path / "app")
    lock = tmp_path / "cage-deploy.lock"
    # smaž jednu komponentu definice → drift hash nelze spočítat
    (app / WORKSPACE_DEF_FILES[0]).unlink()
    with pytest.raises(CageDriftError):
        drift.check_drift(app, lock)


def test_hash_is_order_stable_and_content_sensitive(tmp_path):
    app1 = _make_fake_app_repo(tmp_path / "a", marker="x")
    app2 = _make_fake_app_repo(tmp_path / "b", marker="x")
    assert drift.compute_workspace_def_hash(app1) == drift.compute_workspace_def_hash(app2)
    app3 = _make_fake_app_repo(tmp_path / "c", marker="y")
    assert drift.compute_workspace_def_hash(app1) != drift.compute_workspace_def_hash(app3)
