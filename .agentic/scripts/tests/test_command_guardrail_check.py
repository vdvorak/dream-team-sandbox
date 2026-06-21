"""Unit testy command-guardrail-check.py — SEKUNDÁRNÍ příkazový denylist.

Pokrytí: deny matchne (git stash/reset/clean/checkout/rebase/cherry-pick/revert/commit/
force-push, přepis/rm engine stavu) i allow_through projde (read-only varianty, run.sh,
git push bez force, čtení). Hraniční: except (git stash list), řetězce (&&, ;, pipe, subshell),
fail-safe. Testuje nad REÁLNOU projektovou politikou (zdroj pravdy).
"""
import pytest


# ── deny matchne (pozitivní) ────────────────────────────────────────────────────
@pytest.mark.parametrize("cmd,rule", [
    ("git stash", "git-stash"),
    ("git stash push -m wip", "git-stash"),
    ("git stash pop", "git-stash"),
    ("git commit -m x", "git-commit"),
    ("git reset --hard HEAD", "git-reset-tree"),
    ("git clean -fdx", "git-clean"),
    ("git checkout -- .", "git-checkout-restore-switch"),
    ("git restore src/x", "git-checkout-restore-switch"),
    ("git switch main", "git-checkout-restore-switch"),
    ("git rebase -i HEAD~3", "git-rebase"),
    ("git cherry-pick abc123", "git-cherry-pick"),
    ("git revert abc123", "git-revert"),
    ("git push --force origin main", "git-force-push"),
    ("git push -f", "git-force-push"),
    ("git push --force-with-lease", "git-force-push"),
    ("> current-run.md", "engine-state-overwrite"),
    (">> STATE.md", "engine-state-overwrite"),
    ("echo x > current-run.md", "engine-state-overwrite"),
    ("rm current-run.md", "engine-state-rm-mv"),
    ("mv STATE.md /tmp/", "engine-state-rm-mv"),
    ("rm -rf runs/old", "engine-state-rm-mv"),
])
def test_deny_matches(cmdcheck, policy, cmd, rule):
    r = cmdcheck.check_command(cmd, policy)
    assert r["allow"] is False, cmd
    assert r["rule"] == rule, f"{cmd}: expected {rule} got {r['rule']}"
    assert r["reason"]


# ── allow_through projde (negativní — nikdy neblokovat) ──────────────────────────
@pytest.mark.parametrize("cmd", [
    "git status",
    "git diff HEAD",
    "git log --oneline -5",
    "git show HEAD",
    "git stash list",                 # KLÍČOVÉ: read-only varianta stash projde
    "git ls-files",
    "git branch -a",
    "git rev-parse HEAD",
    "git push origin main",           # push bez force OK
    "git push",
    "cat current-run.md",             # KLÍČOVÉ: čtení engine stavu projde
    "grep foo STATE.md",
    "sed -n '1,5p' current-run.md",
    "pytest scripts/tests",
    "ruff check .",
    "npm test",
    "npm run build",
    "node script.js",
    "python3 scripts/gen-cast-tables.py",
    ".agentic/scripts/pipeline/run.sh done envelope.json",
])
def test_allow_through_passes(cmdcheck, policy, cmd):
    r = cmdcheck.check_command(cmd, policy)
    assert r["allow"] is True, f"{cmd} should be allowed, got deny {r}"


# ── except: git stash deny ale git stash list allow (oba úhly) ──────────────────
def test_stash_deny_but_list_allow(cmdcheck, policy):
    assert cmdcheck.check_command("git stash", policy)["allow"] is False
    assert cmdcheck.check_command("git stash list", policy)["allow"] is True


# ── přepis engine stavu deny ale cat allow ──────────────────────────────────────
def test_overwrite_deny_but_cat_allow(cmdcheck, policy):
    assert cmdcheck.check_command("> current-run.md", policy)["allow"] is False
    assert cmdcheck.check_command("cat current-run.md", policy)["allow"] is True


# ── řetězce: deny se chytne i v &&/;/pipe/subshell ──────────────────────────────
@pytest.mark.parametrize("cmd", [
    "cd .agentic && git stash",
    "git add . ; git commit -m x",
    "true && git reset --hard",
    "(git rebase main)",
    "foo | git clean -fd",
])
def test_deny_in_chain(cmdcheck, policy, cmd):
    assert cmdcheck.check_command(cmd, policy)["allow"] is False, cmd


def test_allow_through_chain_with_readonly(cmdcheck, policy):
    # řetězec, kde se objeví jen read-only git → allow_through ho pustí
    assert cmdcheck.check_command("git status && git diff", policy)["allow"] is True


# ── nesouvisející příkazy projdou ────────────────────────────────────────────────
@pytest.mark.parametrize("cmd", [
    "ls -la",
    "mkdir -p handoffs/x",
    "git add -A",                     # add není destruktivní a není v denylistu
    "echo hello",
    "rm -rf /tmp/scratch",            # rm mimo engine cesty
])
def test_unrelated_allowed(cmdcheck, policy, cmd):
    assert cmdcheck.check_command(cmd, policy)["allow"] is True, cmd


# ── fail-safe + syntetická politika ─────────────────────────────────────────────
def test_empty_command_allowed(cmdcheck, policy):
    assert cmdcheck.check_command("", policy)["allow"] is True


def test_allow_through_overrides_deny(cmdcheck):
    # syntetická: stejný string matchne deny i allow_through → allow vyhrává (přebíjí)
    pol = {
        "allow_through": [r"run\.sh"],
        "deny_commands": [{"id": "x", "match": r"git\s+commit", "reason": "no"}],
    }
    # run.sh done interně commituje — allow_through ho pustí i kdyby obsahoval "commit"
    assert cmdcheck.check_command("run.sh done; git commit", pol)["allow"] is True


def test_except_blocks_deny(cmdcheck):
    pol = {"deny_commands": [
        {"id": "x", "match": r"git\s+stash", "except": r"git\s+stash\s+list", "reason": "no"}]}
    assert cmdcheck.check_command("git stash", pol)["allow"] is False
    assert cmdcheck.check_command("git stash list", pol)["allow"] is True


def test_first_matching_deny_wins(cmdcheck):
    pol = {"deny_commands": [
        {"id": "first", "match": r"git", "reason": "r1"},
        {"id": "second", "match": r"git\s+stash", "reason": "r2"}]}
    assert cmdcheck.check_command("git stash", pol)["rule"] == "first"


# ── CLI ──────────────────────────────────────────────────────────────────────────
def test_cli_deny_exit2(cmdcheck, capsys):
    rc = cmdcheck.main(["--cmd", "git stash"])
    assert rc == 2
    assert "DENY" in capsys.readouterr().out


def test_cli_allow_exit0(cmdcheck, capsys):
    rc = cmdcheck.main(["--cmd", "git stash list"])
    assert rc == 0
    assert "ALLOW" in capsys.readouterr().out


def test_cli_positional(cmdcheck, capsys):
    rc = cmdcheck.main(["git commit -m x"])
    assert rc == 2


def test_cli_json(cmdcheck, capsys):
    import json
    rc = cmdcheck.main(["--cmd", "git stash", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2 and out["allow"] is False and out["rule"] == "git-stash"


def test_cli_missing_cmd_exit1(cmdcheck, capsys):
    rc = cmdcheck.main([])
    assert rc == 1


# ── konzistence s reálnou politikou (zdroj pravdy) ───────────────────────────────
def test_real_policy_has_all_designed_rules(policy):
    ids = {r["id"] for r in policy["deny_commands"]}
    expected = {"git-stash", "git-commit", "git-reset-tree", "git-clean",
                "git-checkout-restore-switch", "git-rebase", "git-cherry-pick",
                "git-revert", "git-force-push", "engine-state-overwrite", "engine-state-rm-mv"}
    assert expected.issubset(ids)
