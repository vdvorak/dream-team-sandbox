"""Unit testy command-guardrail-pathcheck.py — PRIMÁRNÍ write-protection (path-based).

Pokrytí: glob překlad (**, *), write-protected skupiny (engine_runtime/authored/code),
write-owner allow vs deny, nechráněné cesty, normalizace cest. Testuje nad REÁLNOU
projektovou politikou (zdroj pravdy) i nad syntetickou politikou pro hraniční glob případy.
"""


# ── glob → regex (deterministický překlad) ──────────────────────────────────────
def test_glob_doublestar_matches_nested(pathcheck):
    rx = pathcheck._glob_to_regex("runs/**")
    assert rx.match("runs/x")
    assert rx.match("runs/2026/ledger.yaml")
    assert rx.match("runs/")            # ** matchne i nulu segmentů za /
    assert not rx.match("runsX")
    assert not rx.match("xruns/y")


def test_glob_doublestar_dir_prefix(pathcheck):
    rx = pathcheck._glob_to_regex(".agentic/agents/**")
    assert rx.match(".agentic/agents/eywa-meta.md")
    assert rx.match(".agentic/agents/sub/dir/file.md")
    assert not rx.match(".agentic/agentsX/file.md")
    assert not rx.match(".agentic/templates/foo.md")


def test_glob_singlestar_stays_in_segment(pathcheck):
    rx = pathcheck._glob_to_regex("a/*.md")
    assert rx.match("a/b.md")
    assert not rx.match("a/b/c.md")     # * nepřekročí /


def test_norm_path_strips_leading(pathcheck):
    assert pathcheck._norm_path("./runs/x") == "runs/x"
    assert pathcheck._norm_path("/runs/x") == "runs/x"
    assert pathcheck._norm_path("runs\\x") == "runs/x"


# ── engine_runtime: jen engine smí psát, agenti read-only ───────────────────────
def test_runtime_bob_denied(pathcheck, policy):
    r = pathcheck.check_write("bob-backend", "runs/x", policy)
    assert r["allow"] is False
    assert r["group"] == "engine_runtime"
    assert "engine" in r["reason"]


def test_runtime_current_run_denied_for_eywa_too(pathcheck, policy):
    # běhový stav nepíše ani Eywa ručně — jen engine-proces
    r = pathcheck.check_write("eywa-meta", "current-run.md", policy)
    assert r["allow"] is False
    assert r["group"] == "engine_runtime"


def test_runtime_state_md_denied(pathcheck, policy):
    assert pathcheck.check_write("peter-web", "STATE.md", policy)["allow"] is False


def test_runtime_agentic_runs_denied(pathcheck, policy):
    assert pathcheck.check_write("bob-backend", ".agentic/runs/2026/ledger.yaml", policy)["allow"] is False


def test_runtime_engine_writer_allowed(pathcheck, policy):
    # engine-proces (pseudo-agent "engine") JE writer engine_runtime → allow
    r = pathcheck.check_write("engine", "runs/x/ledger.yaml", policy)
    assert r["allow"] is True
    assert r["writer"] == "engine"


def test_runtime_dot_prefixed_path(pathcheck, policy):
    # normalizace ./ → pořád chráněné
    assert pathcheck.check_write("bob-backend", "./current-run.md", policy)["allow"] is False


# ── engine_authored: jen Eywa smí psát ──────────────────────────────────────────
def test_authored_agents_only_eywa(pathcheck, policy):
    assert pathcheck.check_write("eywa-meta", ".agentic/agents/x.md", policy)["allow"] is True
    assert pathcheck.check_write("bob-backend", ".agentic/agents/x.md", policy)["allow"] is False


def test_authored_policy_only_eywa(pathcheck, policy):
    assert pathcheck.check_write("eywa-meta", ".agentic/policy/command-guardrails.yaml", policy)["allow"] is True
    assert pathcheck.check_write("ted-architect", ".agentic/policy/x.yaml", policy)["allow"] is False


def test_authored_pipeline_only_eywa(pathcheck, policy):
    assert pathcheck.check_write("eywa-meta", ".agentic/pipeline/delivery.yaml", policy)["allow"] is True
    assert pathcheck.check_write("bob-backend", ".agentic/pipeline/delivery.yaml", policy)["allow"] is False


def test_authored_templates_only_eywa(pathcheck, policy):
    assert pathcheck.check_write("eywa-meta", ".agentic/templates/handoff.md", policy)["allow"] is True
    assert pathcheck.check_write("denisa-ux", ".agentic/templates/handoff.md", policy)["allow"] is False


# ── engine_code: nikdo z agentů (writer=l3-maintainer) ──────────────────────────
def test_engine_code_denied_for_everyone(pathcheck, policy):
    assert pathcheck.check_write("eywa-meta", ".agentic/scripts/pipeline/core/run.py", policy)["allow"] is False
    assert pathcheck.check_write("bob-backend", ".agentic/scripts/pipeline/check.sh", policy)["allow"] is False


# ── nechráněné cesty (mimo write-protection) ────────────────────────────────────
def test_unprotected_paths_allowed(pathcheck, policy):
    for p in ("clients/web/src/App.tsx", "server/main.py", "handoffs/x/note.md",
              "contracts/error-codes.md", "specs/feature.md"):
        r = pathcheck.check_write("bob-backend", p, policy)
        assert r["allow"] is True, p
        assert r["group"] is None


def test_first_matching_group_decides(pathcheck):
    # syntetická politika: ověř, že rozhoduje PRVNÍ matchnuvší skupina (pořadí v dictu)
    pol = {"write_protect": {
        "a": {"paths": ["x/**"], "writer": "engine", "agents_access": "read-only", "reason": "ra"},
        "b": {"paths": ["x/**"], "writer": "bob", "agents_access": "read-only", "reason": "rb"},
    }}
    r = pathcheck.check_write("bob", "x/file", pol)
    assert r["group"] == "a" and r["allow"] is False   # první (engine) rozhoduje, ne druhá (bob)


# ── CLI exit kódy ───────────────────────────────────────────────────────────────
def test_cli_allow_exit0(pathcheck, capsys):
    rc = pathcheck.main(["--agent", "engine", "--path", "runs/x"])
    assert rc == 0
    assert "ALLOW" in capsys.readouterr().out


def test_cli_deny_exit2(pathcheck, capsys):
    rc = pathcheck.main(["--agent", "bob-backend", "--path", "current-run.md"])
    assert rc == 2
    assert "DENY" in capsys.readouterr().out


def test_cli_json(pathcheck, capsys):
    import json
    rc = pathcheck.main(["--agent", "bob-backend", "--path", "runs/x", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2 and out["allow"] is False


def test_cli_bad_policy_exit1(pathcheck, capsys):
    rc = pathcheck.main(["--agent", "bob", "--path", "x", "--policy", "/nonexistent.yaml"])
    assert rc == 1
