"""Regresní test — commit-on-done (engine-native git commit per node) + clean-tree guard.

Z backlog/agent-command-guardrails.md §3b/§4-R1: git commit vlastní VÝHRADNĚ engine
(commit-on-done), ne agent-shell. Tohle je NOVÁ engine schopnost (dřív commitoval ručně
orchestrátor).

KRITICKÉ — HERMETICITA GITU: KAŽDÝ test pracuje v DOČASNÉM git repu (tmp_path + git init),
NIKDY necommituje do reálného repa. cwd se enginu předává explicitně (commit_node(cwd=…)),
AGENTIC_RUN_ROOT izoluje stav. Guard test (start) jede přes run.py subprocess s
AGENTIC_RUN_ROOT=tmp git repo, takže `git status` čte tmp tree, ne reálný.
"""
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

import nodecommit  # noqa: E402

_RUN_PY = os.path.join(_CORE, "run.py")


# Commit-on-done je nově OPT-IN (default OFF, viz incident 2026-06-20). Tento test soubor
# ověřuje commit chování, takže flag explicitně ZAPÍNÁ pro všechny své testy (autouse).
# Test, který vypnutí cíleně testuje (`test_commit_disabled_by_env`), si přebije monkeypatchem
# na "0"; subprocess testy si flag předávají v env (viz _start / _CLI_ENV níže).
@pytest.fixture(autouse=True)
def _enable_node_commit(monkeypatch):
    monkeypatch.setenv("AGENTIC_NODE_COMMIT", "1")


# Subprocess testy (run.py přes shell) dědí prostředí; flag musí být v jejich env explicitně,
# protože jdou přímo na run.py (NE přes run.sh, který by ho jinak pro done/drive nastavil sám).
_CLI_ENV = {"AGENTIC_NODE_COMMIT": "1"}


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    """Dočasný git repo s jedním base commitem. VŠECHNY commity testů končí TADY, ne v reálném repu."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test Engine")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _head_count(repo):
    return int(_git(repo, "rev-list", "--count", "HEAD").stdout.strip())


def _head_subject(repo):
    return _git(repo, "log", "-1", "--pretty=%s").stdout.strip()


# ── commit_node: stage + commit + message + no-op ──────────────────────────────
def test_commit_node_creates_commit_with_conventional_message(git_repo):
    """Změna v tree → commit_node ji zacommituje se zprávou chore(wave:<run>): <node> <outcome>."""
    (git_repo / "out.txt").write_text("node output\n", encoding="utf-8")
    env = {"run": "wave-x", "node": "backend", "agent": "bob-backend", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is True
    assert _head_count(git_repo) == 2
    assert _head_subject(git_repo) == "chore(wave:wave-x): backend PASS"
    # body nese strojová fakta
    body = _git(git_repo, "log", "-1", "--pretty=%b").stdout
    assert "node: backend" in body and "agent: bob-backend" in body


def test_commit_node_stages_all_changes(git_repo):
    """git add -A: nové, změněné i smazané soubory jdou do node-commitu."""
    (git_repo / "new.txt").write_text("new\n", encoding="utf-8")
    (git_repo / "base.txt").write_text("modified\n", encoding="utf-8")
    env = {"run": "w", "node": "work", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is True
    # po commitu je tree čistý (vše stageováno a zacommitováno)
    assert _git(git_repo, "status", "--porcelain").stdout.strip() == ""


def test_commit_node_noop_on_empty_diff(git_repo):
    """Prázdný diff (nic se nezměnilo) → no-op, žádný prázdný commit (historie nebobtná)."""
    env = {"run": "w", "node": "work", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is False
    assert _head_count(git_repo) == 1   # pořád jen base


def test_commit_node_fail_returns_to_still_commits(git_repo):
    """EDGE: FAIL s returns_to → COMMITNE (re-flow změnil tree, ten stav patří do historie)."""
    (git_repo / "partial.txt").write_text("re-flow stav\n", encoding="utf-8")
    env = {"run": "w", "node": "audit", "outcome": "FAIL", "returns_to": "backend"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is True
    assert _head_subject(git_repo) == "chore(wave:w): audit FAIL"
    assert "returns_to: backend" in _git(git_repo, "log", "-1", "--pretty=%b").stdout


def test_commit_node_terminal_done(git_repo):
    """EDGE: terminal DONE → commitne uzavření vlny."""
    (git_repo / "summary.txt").write_text("uzavřeno\n", encoding="utf-8")
    env = {"run": "w", "node": "done", "outcome": "DONE"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is True
    assert _head_subject(git_repo) == "chore(wave:w): done DONE"


# ── fail-soft: mimo git / vypínač ──────────────────────────────────────────────
def test_commit_node_outside_git_is_failsoft(tmp_path):
    """Mimo git repo → False, NEvyhodí (done se nesmí shodit kvůli gitu)."""
    env = {"run": "w", "node": "work", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(tmp_path)) is False


def test_commit_disabled_by_env(git_repo, monkeypatch):
    """AGENTIC_NODE_COMMIT=0 → engine necommituje (rollout/CI safety switch)."""
    monkeypatch.setenv("AGENTIC_NODE_COMMIT", "0")
    (git_repo / "x.txt").write_text("x\n", encoding="utf-8")
    env = {"run": "w", "node": "work", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is False
    assert _head_count(git_repo) == 1


# ── OPT-IN default (incident 2026-06-20): commit_enabled default OFF, jen =1/true/yes/on ON ──
def test_commit_enabled_default_off_when_unset(monkeypatch):
    """Default (flag unset) → commit_enabled() False. Chrání server/test cestu (žádný run.sh)."""
    monkeypatch.delenv("AGENTIC_NODE_COMMIT", raising=False)
    assert nodecommit.commit_enabled() is False


def test_commit_enabled_off_for_empty_and_garbage(monkeypatch):
    """Prázdná / nesmyslná hodnota → OFF (jen explicitní truthy zapíná)."""
    for val in ("", "   ", "maybe", "2", "off", "no", "false", "0"):
        monkeypatch.setenv("AGENTIC_NODE_COMMIT", val)
        assert nodecommit.commit_enabled() is False, f"{val!r} mělo být OFF"


def test_commit_enabled_on_for_truthy(monkeypatch):
    """Explicitní truthy (1/true/yes/on, case-insensitive) → ON."""
    for val in ("1", "true", "TRUE", "yes", "Yes", "on", "ON"):
        monkeypatch.setenv("AGENTIC_NODE_COMMIT", val)
        assert nodecommit.commit_enabled() is True, f"{val!r} mělo být ON"


def test_commit_node_default_off_no_commit_when_unset(git_repo, monkeypatch):
    """End-to-end: flag unset → commit_node no-op (necommituje), i když je co commitnout."""
    monkeypatch.delenv("AGENTIC_NODE_COMMIT", raising=False)
    (git_repo / "x.txt").write_text("x\n", encoding="utf-8")
    env = {"run": "w", "node": "work", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo)) is False
    assert _head_count(git_repo) == 1


# ── is_tree_dirty ───────────────────────────────────────────────────────────────
def test_is_tree_dirty_detects_changes(git_repo):
    assert nodecommit.is_tree_dirty(cwd=str(git_repo)) is False
    (git_repo / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
    assert nodecommit.is_tree_dirty(cwd=str(git_repo)) is True


def test_is_tree_dirty_outside_git_is_none(tmp_path):
    """Mimo git → None (nevíme); start guard to bere jako fail-soft skip."""
    assert nodecommit.is_tree_dirty(cwd=str(tmp_path)) is None


# ── baseline-exclusion: commit_node stageuje JEN wave-změny ──────────────────────
def test_commit_node_excludes_baseline_paths(git_repo):
    """BUG A jádro: pre-existing dirty/untracked (baseline) se NEZAMETE do node-commitu.

    Repo má před vlnou haraburdí (untracked junk + modified tracked) → baseline. Vlna pak
    vyrobí svůj soubor. commit_node smí zacommitnout JEN wave soubor; haraburdí zůstává
    untracked/modified a NENÍ v commitu."""
    # pre-existing haraburdí (jako runs/fixture-* / .tmp/ v reálném repu)
    (git_repo / "junk.txt").write_text("trvalý runtime artefakt\n", encoding="utf-8")
    (git_repo / "base.txt").write_text("cizí rozdělaná změna\n", encoding="utf-8")
    baseline = nodecommit.capture_baseline(cwd=str(git_repo))
    assert set(baseline) == {"junk.txt", "base.txt"}

    # vlna vyrobí svůj výstup
    (git_repo / "wave_out.txt").write_text("výstup vlny\n", encoding="utf-8")
    env = {"run": "w", "node": "backend", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo), baseline=baseline) is True

    # commit obsahuje JEN wave_out.txt
    files = _git(git_repo, "show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    assert files == ["wave_out.txt"], f"do commitu se dostalo i haraburdí: {files}"

    # haraburdí zůstává nezacommitované (untracked junk + modified base)
    porcelain = _git(git_repo, "status", "--porcelain").stdout
    assert "?? junk.txt" in porcelain
    assert " M base.txt" in porcelain or "M  base.txt" in porcelain


def test_commit_node_noop_when_only_baseline_changed(git_repo):
    """Když se od startu změnilo JEN haraburdí z baseline (žádná wave-změna) → no-op, žádný commit."""
    (git_repo / "junk.txt").write_text("haraburdí\n", encoding="utf-8")
    baseline = nodecommit.capture_baseline(cwd=str(git_repo))
    # po startu se junk dál mění, ale nic wave-ového nepřibylo
    (git_repo / "junk.txt").write_text("haraburdí v2\n", encoding="utf-8")
    env = {"run": "w", "node": "backend", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo), baseline=baseline) is False
    assert _head_count(git_repo) == 1   # pořád jen base


def test_commit_node_baseline_dirty_file_stays_excluded_even_if_wave_touches_it(git_repo):
    """EDGE (zdokumentovaný trade-off): soubor dirty UŽ v baseline, který vlna dál změní,
    ZŮSTÁVÁ vyloučen (jeho změny „nepatří vlně"). Vlna commitne jen svůj NOVÝ soubor."""
    (git_repo / "base.txt").write_text("rozdělané před vlnou\n", encoding="utf-8")
    baseline = nodecommit.capture_baseline(cwd=str(git_repo))
    assert "base.txt" in baseline
    # vlna změní base.txt dál + vyrobí nový soubor
    (git_repo / "base.txt").write_text("vlna do toho šáhla taky\n", encoding="utf-8")
    (git_repo / "wave.txt").write_text("nový\n", encoding="utf-8")
    env = {"run": "w", "node": "backend", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo), baseline=baseline) is True
    files = _git(git_repo, "show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    assert files == ["wave.txt"], f"base.txt v baseline se neměl commitnout: {files}"
    # base.txt zůstává modified (vyloučeno)
    assert "base.txt" in _git(git_repo, "status", "--porcelain").stdout


def test_commit_node_stages_wave_deletion(git_repo):
    """Mazání: vlna smaže tracked soubor (mimo baseline) → stageuje se deletion do commitu."""
    (git_repo / "victim.txt").write_text("smazat mě\n", encoding="utf-8")
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "add victim")
    baseline = nodecommit.capture_baseline(cwd=str(git_repo))   # čistý tree → prázdná baseline
    assert baseline == []
    (git_repo / "victim.txt").unlink()   # vlna ho smaže
    env = {"run": "w", "node": "backend", "outcome": "PASS"}
    assert nodecommit.commit_node(env, cwd=str(git_repo), baseline=baseline) is True
    # po commitu je tree čistý (deletion zacommitnuta) a victim už není tracked
    assert _git(git_repo, "status", "--porcelain").stdout.strip() == ""
    assert _git(git_repo, "cat-file", "-e", "HEAD:victim.txt").returncode != 0


def test_capture_baseline_outside_git_is_none(tmp_path):
    """Mimo git → None (start to uloží jako None → commit_node degraduje na 'nic vyloučeno')."""
    assert nodecommit.capture_baseline(cwd=str(tmp_path)) is None


# ── start advisory (NE tvrdý guard) přes run.py subprocess (hermetické) ───────────
def _start(repo, run="wave-1", extra_env=None):
    """run.py start <run> s AGENTIC_RUN_ROOT=tmp git repo → baseline čte `git status` tmp tree."""
    env = dict(os.environ, AGENTIC_RUN_ROOT=str(repo), **_CLI_ENV)
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, _RUN_PY, "start", run],
                          capture_output=True, text=True, cwd=str(repo), env=env)


def _seed_graph(repo):
    pdir = repo / "pipeline"
    pdir.mkdir(exist_ok=True)
    (pdir / "delivery.yaml").write_text(
        "meta: {entry: intake}\nnodes:\n  intake: {type: router}\n  done: {type: terminal}\n"
        "edges:\n  - {from: intake, to: done, kind: normal}\n", encoding="utf-8")
    return pdir / "delivery.yaml"


def _state_block(repo):
    from common import read_state
    return read_state(str(repo / "current-run.md"))[0]


def test_start_does_not_reject_dirty_tree(git_repo):
    """BUG A: pre-existing untracked artefakty start NEodmítá (jen advisory) — zachytí je do baseline."""
    graph = _seed_graph(git_repo)
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "graph")
    (git_repo / "uncommitted.txt").write_text("trvalý artefakt\n", encoding="utf-8")
    res = _start(git_repo, extra_env={"PIPELINE_GRAPH": str(graph)})
    assert res.returncode == 0, f"start NEMĚL odmítnout (advisory):\n{res.stdout}\n{res.stderr}"
    assert (git_repo / "current-run.md").is_file()
    assert "ADVISORY" in res.stderr
    # baseline zachycena ve stavu
    st = _state_block(git_repo)
    assert "uncommitted.txt" in (st.get("commit_baseline") or [])


def test_start_passes_on_clean_tree_empty_baseline(git_repo):
    """Čistý tree → start projde, baseline prázdná."""
    graph = _seed_graph(git_repo)
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "graph")
    res = _start(git_repo, extra_env={"PIPELINE_GRAPH": str(graph)})
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert _state_block(git_repo).get("commit_baseline") == []


def test_start_no_baseline_when_commit_disabled(git_repo):
    """AGENTIC_NODE_COMMIT=0 → start projde i na špinavém tree a commit_baseline se neukládá."""
    graph = _seed_graph(git_repo)
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "graph")
    (git_repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    res = _start(git_repo, extra_env={"PIPELINE_GRAPH": str(graph), "AGENTIC_NODE_COMMIT": "0"})
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert (git_repo / "current-run.md").is_file()
    assert "commit_baseline" not in _state_block(git_repo)


# ── end-to-end: done v repu s haraburdím commitne JEN wave změny ──────────────────
def test_done_commits_only_wave_changes_with_pre_existing_junk(git_repo):
    """BUG A end-to-end: start v repu s haraburdím + done → commit obsahuje JEN wave výstup,
    pre-existing haraburdí zůstává untracked a NENÍ v commitu. Celé přes run.py CLI."""
    graph = _seed_graph(git_repo)
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "graph")
    # pre-existing haraburdí (analogie runs/fixture-* / .tmp/)
    (git_repo / "junk.txt").write_text("trvalý runtime artefakt\n", encoding="utf-8")
    (git_repo / "more_junk").mkdir()
    (git_repo / "more_junk" / "x.txt").write_text("víc haraburdí\n", encoding="utf-8")

    env_run = dict(os.environ, AGENTIC_RUN_ROOT=str(git_repo), PIPELINE_GRAPH=str(graph), **_CLI_ENV)
    start = subprocess.run([sys.executable, _RUN_PY, "start", "wave-z"],
                           capture_output=True, text=True, cwd=str(git_repo), env=env_run)
    assert start.returncode == 0, f"{start.stdout}\n{start.stderr}"
    head_before = _head_count(git_repo)

    # vlna vyrobí svůj výstup
    (git_repo / "feature.txt").write_text("kód vlny\n", encoding="utf-8")
    envelope = git_repo / "_done.yaml"
    envelope.write_text("run: wave-z\nnode: intake\noutcome: PASS\noutputs: []\n", encoding="utf-8")
    done = subprocess.run([sys.executable, _RUN_PY, "done", str(envelope)],
                          capture_output=True, text=True, cwd=str(git_repo), env=env_run)
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"

    # vznikl PRÁVĚ JEDEN node-commit
    assert _head_count(git_repo) == head_before + 1
    files = set(_git(git_repo, "show", "--name-only", "--pretty=format:", "HEAD").stdout.split())
    # commit nese wave výstup + current-run.md (engine stav vlny); NIC z haraburdí
    assert "feature.txt" in files
    assert "junk.txt" not in files
    assert "more_junk/x.txt" not in files
    # haraburdí pořád untracked
    porcelain = _git(git_repo, "status", "--porcelain").stdout
    assert "junk.txt" in porcelain and "more_junk/" in porcelain
