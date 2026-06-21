"""Unit testy — Smokescreen ACL templating (env dosazení, validace, fail-closed).

Acceptance vazba: I2 (doménový allowlist), I3 (build-time hosty deny), rozhodnutí (d)
(CF doména z env, nehardcoduje se), CE-2 (fail-closed na nevalidní vstup).
"""

import pytest

from server.cage.policy.acl import (
    AclTemplateError,
    allow_domains,
    cf_access_domain,
    render_acl,
)


def test_cf_domain_templated_from_team_label():
    assert cf_access_domain("myteam") == "myteam.cloudflareaccess.com"


def test_cf_domain_accepts_full_fqdn_and_normalizes():
    assert cf_access_domain("myteam.cloudflareaccess.com") == "myteam.cloudflareaccess.com"


def test_allow_list_contains_github_and_cf_only():
    domains = allow_domains("acme")
    assert domains == ["api.github.com", "acme.cloudflareaccess.com"]
    # I3: build-time hosty NEjsou v allow.
    assert "raw.githubusercontent.com" not in domains
    assert "pypi.org" not in domains


def test_render_acl_is_default_deny():
    out = render_acl("acme")
    assert "default: deny" in out
    assert "api.github.com" in out
    assert "acme.cloudflareaccess.com" in out


def test_render_acl_reads_env_when_no_arg(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "envteam")
    out = render_acl()  # bez argumentu → z env (rozhodnutí (d))
    assert "envteam.cloudflareaccess.com" in out


def test_render_acl_fails_closed_on_empty_env(monkeypatch):
    # Fail-closed (CE-2): chybí CF_ACCESS_TEAM_DOMAIN → AclTemplateError (deploy ABORT).
    monkeypatch.delenv("CF_ACCESS_TEAM_DOMAIN", raising=False)
    with pytest.raises(AclTemplateError):
        render_acl()


def test_cf_domain_rejects_injection_attempt():
    # Hodnota z env nesmí umožnit injektáž dalších domén/řádků do ACL.
    with pytest.raises(AclTemplateError):
        cf_access_domain("evil.com\n  - domain: attacker")


def test_cf_domain_rejects_multi_label():
    with pytest.raises(AclTemplateError):
        cf_access_domain("foo.bar")


def test_different_teams_render_different_acl():
    # rozhodnutí (d): CF doména NENÍ hardcoded — různý team → různý vyrenderovaný ACL.
    a = render_acl("teamone")
    b = render_acl("teamtwo")
    assert "teamone.cloudflareaccess.com" in a
    assert "teamtwo.cloudflareaccess.com" in b
    assert a != b
