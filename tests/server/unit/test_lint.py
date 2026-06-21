"""Unit testy — pre-deploy lint/scan (error-code cesty, fail-closed regrese-guardy).

Acceptance vazba: I7 (ERR_INGRESS_LEAK), I9 (ERR_SECRET_LEAK), I10/CE-7 (ERR_GIT_WRITE_CRED).
"""

import pytest

from server.cage.deploy import lint
from server.cage.errors import GitWriteCredError, IngressLeakError, SecretLeakError


# --- I7: [http_service] leak ---

def test_http_service_present_fails_closed():
    cfg = "app = 'x'\n[http_service]\n  internal_port = 8081\n"
    with pytest.raises(IngressLeakError):
        lint.lint_no_http_service(cfg)


def test_http_service_double_bracket_form_detected():
    cfg = "app = 'x'\n[[http_service]]\n"
    with pytest.raises(IngressLeakError):
        lint.lint_no_http_service(cfg)


def test_commented_http_service_is_ok():
    # Zakomentovaná sekce neobchází policy → nesmí FAILnout.
    cfg = "app = 'x'\n# [http_service]  ← záměrně odstraněno (I7)\n"
    lint.lint_no_http_service(cfg)  # nesmí raisnout


def test_overlay_fly_config_has_no_http_service():
    # Náš dodaný overlay fly.workspace.toml MUSÍ projít lintem (6PN-only).
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3]
    cfg = root / "server" / "cage" / "overlay" / "fly.workspace.toml"
    lint.lint_overlay_fly_config(cfg)  # nesmí raisnout


# --- I9: secret leak ---

def test_high_value_secret_in_env_fails_closed():
    env = {"WORKSPACE_DIR": "/workspace", "GH_TOKEN": "xxx"}
    with pytest.raises(SecretLeakError):
        lint.scan_secret_leak(env)


def test_clean_env_passes_secret_scan():
    env = {"WORKSPACE_DIR": "/workspace", "AGENT_PORT": "8081"}
    lint.scan_secret_leak(env)  # nesmí raisnout


@pytest.mark.parametrize("key", lint.HIGH_VALUE_SECRETS)
def test_each_high_value_secret_detected(key):
    with pytest.raises(SecretLeakError):
        lint.scan_secret_leak({key: "value"})


# --- I10/CE-7: git write credential ---

def test_classic_pat_fails_closed():
    with pytest.raises(GitWriteCredError):
        lint.scan_git_write_cred("token=ghp_" + "a" * 30)


def test_fine_grained_pat_fails_closed():
    with pytest.raises(GitWriteCredError):
        lint.scan_git_write_cred("github_pat_11ABC_xyz123")


def test_private_key_fails_closed():
    blob = "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n"
    with pytest.raises(GitWriteCredError):
        lint.scan_git_write_cred(blob)


def test_clean_text_passes_git_scan():
    # read-only clone URL bez write tokenu je OK.
    lint.scan_git_write_cred("https://api.github.com/repos/x/y", "WORKSPACE_DIR=/workspace")
