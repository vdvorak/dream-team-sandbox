"""Unit testy structure_check.py — validátor PRODUCT-layer tvaru projektu (S1–S4).

Pozn.: S2 path-checky + S3 layout běží proti cwd (= repo root při běhu brány)."""
import structure_check as sc
from graph import Graph, make_node


def _graph(*ids: str) -> Graph:
    return Graph({i: make_node(i, {"type": "agent"}) for i in ids}, [], {}, {})


# ── S1 sekce ────────────────────────────────────────────────────────────────────
def test_s1_missing_all():
    out = sc.check_sections({})
    assert len(out) == len(sc.REQUIRED_SECTIONS)
    assert any("'## Projekt'" in f for f in out)


def test_s1_present_prefix_match():
    secs = {s: {} for s in ["Projekt", "Targets", "Project flags", "Active roles",
                            "Fyzické cesty (logical → physical)"]}  # match dle prefixu
    assert sc.check_sections(secs) == []


# ── S2 fyzické cesty ──────────────────────────────────────────────────────────────
def test_s2_missing_key():
    out = sc.check_paths({"Fyzické cesty": {}})
    assert any("chybí klíč 'project_constitution'" in f for f in out)


def test_s2_nonexistent_path():
    out = sc.check_paths({"Fyzické cesty": {k: "DOES-NOT-EXIST/" for k in sc.REQUIRED_PATHS}})
    assert all("neexistuje na disku" in f for f in out) and len(out) == len(sc.REQUIRED_PATHS)


def test_s2_lazy_not_required():
    # lazy specs/stack nejsou v REQUIRED_PATHS → jejich absence se neřeší
    paths = {k: "." for k in sc.REQUIRED_PATHS}   # "." vždy existuje
    assert sc.check_paths({"Fyzické cesty": paths}) == []


# ── S3 project_type layout ────────────────────────────────────────────────────────
def test_s3_selfhost_ok_on_repo():
    # běh z repo rootu: TOOL vrstva (constitution.md/agents/pipeline/core) existuje
    assert sc.check_project_type({"Projekt": {"project_type": "self-host"}}) == []


def test_s3_normal_needs_agentic():
    out = sc.check_project_type({"Projekt": {"project_type": "greenfield"}})
    assert any(".agentic/" in f for f in out)   # repo root nemá .agentic/


# ── S4 active_roles ───────────────────────────────────────────────────────────────
def test_s4_unknown_role():
    out = sc.check_active_roles({"Active roles": {"active_roles": {"ghost": "active"}}}, _graph("product"))
    assert any("neznámá role 'ghost'" in f for f in out)


def test_s4_bad_state():
    out = sc.check_active_roles({"Active roles": {"active_roles": {"product": "on"}}}, _graph("product"))
    assert any("neznámý stav 'on'" in f for f in out)


def test_s4_ok():
    assert sc.check_active_roles(
        {"Active roles": {"active_roles": {"product": "active", "backend": "inactive"}}},
        _graph("product", "backend")) == []


def test_s4_missing_map():
    assert sc.check_active_roles({"Active roles": {}}, _graph("product")) == \
        ["S4 chybí 'active_roles' mapa v sekci '## Active roles'"]


# ── parse ─────────────────────────────────────────────────────────────────────────
def test_parse_sections():
    text = ("# Project Config\n## Projekt\n```yaml\nproject_type: self-host\n```\n"
            "## Targets\n```yaml\nactive_targets: {web: true}\n```\n")
    secs = sc.parse_sections(text)
    assert secs["Projekt"]["project_type"] == "self-host"
    assert secs["Targets"]["active_targets"] == {"web": True}
