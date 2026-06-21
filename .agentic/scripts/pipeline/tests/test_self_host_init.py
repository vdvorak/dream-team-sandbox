"""Unit testy self_host_init.py — deterministický seed PRODUCT vrstvy (self-host).

Generovaný project-config MUSÍ projít structure_check (skript a validátor jsou inverze)."""
import self_host_init as shi
import structure_check as sc
from graph import Graph, make_node


def _graph() -> Graph:
    nodes = {
        "product": make_node("product", {"type": "agent", "agent": "vision-po"}),
        "intake": make_node("intake", {"type": "router"}),          # bez agenta → ne role
        "backend": make_node("backend", {"type": "agent", "agent": "bob"}),
        "qa": make_node("qa", {"type": "gate", "agent": "joey"}),   # gate s agentem → role
    }
    return Graph(nodes, [], {}, {})


def _target_graph() -> Graph:
    """Graf s when-predikáty nad targety/flagy — pro test zobecněné derivace role-setu."""
    nodes = {
        "product":   make_node("product", {"type": "agent", "agent": "vision-po"}),
        "backend":   make_node("backend", {"type": "agent", "agent": "bob",
                                           "when": "project.has_server"}),
        "db-schema": make_node("db-schema", {"type": "agent", "agent": "chandler",
                                             "when": "project.has_db && touches_db"}),
        "web":       make_node("web", {"type": "agent", "agent": "peter",
                                       "when": "project.targets.web && spec.has_ui"}),
        "mobile":    make_node("mobile", {"type": "agent", "agent": "mob",
                                          "when": "project.targets.mobile && spec.has_ui"}),
        "ui-system": make_node("ui-system", {"type": "agent", "agent": "leonard",
                                             "when": "spec.has_ui"}),
        "devops":    make_node("devops", {"type": "agent", "agent": "alfred",
                                          "when": "project.has_deploy"}),
    }
    return Graph(nodes, [], {}, {})


def test_derive_roles_only_agent_nodes():
    assert set(shi.derive_roles(_graph())) == {"product", "backend", "qa"}   # intake (router) vyřazen


def test_derive_roles_self_host_round_trip_unchanged():
    """Bez targets (None) = self-host: VŠECHNY role s agentem (parita s původním chováním)."""
    g = _target_graph()
    assert set(shi.derive_roles(g)) == {"product", "backend", "db-schema",
                                        "web", "mobile", "ui-system", "devops"}


def test_derive_roles_no_web_target_deactivates_web_roles():
    """N4 jádro: deklarovaný target-set bez webu → role gated `targets.web` vypadnou."""
    roles = set(shi.derive_roles(_target_graph(),
                                 targets={"server": {"backend": True}}, flags={}))
    assert "web" not in roles and "mobile" not in roles   # cílové platformy mrtvé
    assert "backend" in roles                              # has_server (z target sub-klíče) live
    # ui-system gated jen spec.has_ui (per-feature, NEznámé při setupu) → zůstává; Watson ho
    # vypne profilem (úsudek „bez UI"). Strukturální target-mrtvost ≠ feature-level has_ui.
    assert "ui-system" in roles


def test_derive_roles_web_project_keeps_web_drops_other_clients():
    roles = set(shi.derive_roles(_target_graph(),
                                 targets={"web": {"backend": True}}, flags={}))
    assert "web" in roles and "mobile" not in roles


def test_derive_roles_explicit_false_flags_deactivate_db_deploy():
    """Watson rozhodne „bez DB/deploy" → flags=False; deterministicky odřízne db/deploy role."""
    roles = set(shi.derive_roles(_target_graph(), targets={"web": {"backend": True}},
                                 flags={"has_db": False, "has_deploy": False}))
    assert "db-schema" not in roles and "devops" not in roles
    assert "backend" in roles and "web" in roles


def test_derive_roles_has_ui_false_drops_ui_roles():
    """CLI/no-UI projekt: Watson předá has_ui=False → spec.has_ui role (ui-system) vypadne."""
    roles = set(shi.derive_roles(_target_graph(), targets={"cli": {"backend": True}},
                                 flags={"has_ui": False}))
    assert "ui-system" not in roles and "web" not in roles
    assert "backend" in roles


def test_generated_config_passes_section_check():
    secs = sc.parse_sections(shi.project_config_md("x", ["product", "backend"]))
    assert sc.check_sections(secs) == []          # všechny required sekce přítomné


def test_generated_config_self_host_type():
    secs = sc.parse_sections(shi.project_config_md("x", ["product"]))
    assert sc.section(secs, "Projekt")["project_type"] == "self-host"


def test_generated_config_active_roles_passes_s4():
    secs = sc.parse_sections(shi.project_config_md("x", ["product", "backend"]))
    assert sc.check_active_roles(secs, _graph()) == []   # role ∈ graf, stav active


def test_generated_config_paths_keys_present():
    secs = sc.parse_sections(shi.project_config_md("x", ["product"]))
    paths = sc.section(secs, "Fyzické cesty")
    for key in sc.REQUIRED_PATHS:
        assert key in paths


def test_generated_constitution_has_vize_section():
    assert "## Vize a mise" in shi.project_constitution_md("x")
