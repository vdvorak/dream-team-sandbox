#!/usr/bin/env python3
"""structure_check.py — validátor PRODUCT-layer tvaru projektu (z structure-check.sh).

Brána dosud ověřovala GRAF (check.sh) a ENGINE (selftest/pytest/mypy), ale ne „má projekt
správný TVAR" — že PRODUCT vrstva (project-config sekce, fyzické cesty, project_type layout,
active_roles) sedí. Konformita tvaru = deterministický skript, ne jen konvence + úspěšný běh
(scripts-not-LLM enforcement). Sourozenec check.py (graf) — tohle je projekt.

Kontroly S1–S4:
  S1  required ## sekce v project-config.md
  S2  Fyzické cesty existují na disku (lazy specs/stack = allowed-absent)
  S3  project_type layout: self-host → TOOL na rootu · normal → .agentic/ s TOOL vrstvou
  S4  active_roles klíče ∈ role grafu (node-id v delivery.yaml); hodnoty ∈ {active, inactive}

CLI:   python3 structure_check.py [project-config.md]
Závislost: python3 + PyYAML. Exit: 0 = OK | 1 = nálezy | 2 = chyba.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import find_graph, yaml
from graph import Graph

REQUIRED_SECTIONS = ["Projekt", "Targets", "Project flags", "Active roles", "Fyzické cesty"]
# Cesty z `## Fyzické cesty`, které MUSÍ existovat na disku (subset; lazy = allowed-absent).
REQUIRED_PATHS = ["project_constitution", "project_state", "backlog", "handoffs", "graph", "engine"]
LAZY_PATHS = ["specs", "stack"]            # config je značí „zatím neexistuje" → smí chybět
SELFHOST_TOOL = ["constitution.md", "agents", "pipeline", "scripts/pipeline/core"]
ROLE_STATES = {"active", "inactive", "done"}


def parse_sections(text: str) -> dict[str, dict]:
    """{'## heading' (bez ##): yaml-dict prvního ```yaml bloku v sekci}."""
    sections: dict[str, dict] = {}
    parts = re.split(r"(?m)^## (.+)$", text)   # [preamble, h1, body1, h2, body2, …]
    it = iter(parts[1:])
    for heading, body in zip(it, it):
        m = re.search(r"```yaml\s*\n(.*?)\n```", body, re.S)
        data: dict = {}
        if m:
            try:
                loaded = yaml.safe_load(m.group(1))
                data = loaded if isinstance(loaded, dict) else {}
            except yaml.YAMLError:
                data = {}
        sections[heading.strip()] = data
    return sections


def section(sections: dict[str, dict], prefix: str) -> dict:
    """Sekce, jejíž nadpis začíná na `prefix` (nadpisy mají závorky: „Fyzické cesty (…)")."""
    for heading, data in sections.items():
        if heading.startswith(prefix):
            return data
    return {}


def check_sections(sections: dict[str, dict]) -> list[str]:
    """S1 — required ## sekce přítomné (match dle prefixu, nadpisy mají parenthetical)."""
    out: list[str] = []
    for req in REQUIRED_SECTIONS:
        if not any(h.startswith(req) for h in sections):
            out.append(f"S1 chybí sekce '## {req}' v project-config")
    return out


def check_paths(sections: dict[str, dict]) -> list[str]:
    """S2 — Fyzické cesty: required klíče existují na disku; lazy smí chybět."""
    out: list[str] = []
    paths = section(sections, "Fyzické cesty")
    for key in REQUIRED_PATHS:
        if key not in paths:
            out.append(f"S2 Fyzické cesty: chybí klíč '{key}'")
            continue
        p = str(paths[key]).strip()
        if not os.path.exists(p):
            out.append(f"S2 cesta '{key}: {p}' neexistuje na disku")
    return out


def check_project_type(sections: dict[str, dict]) -> list[str]:
    """S3 — layout dle project_type: self-host = TOOL na rootu; jinak .agentic/ s TOOL vrstvou."""
    out: list[str] = []
    ptype = str(section(sections, "Projekt").get("project_type") or "").strip()
    if ptype == "self-host":
        for p in SELFHOST_TOOL:
            if not os.path.exists(p):
                out.append(f"S3 self-host: chybí TOOL vrstva '{p}' na rootu")
    else:
        if not os.path.isdir(".agentic"):
            out.append("S3 projekt: chybí '.agentic/' (TOOL vrstva) — projekt nekonzumuje framework")
    return out


def check_active_roles(sections: dict[str, dict], graph: Graph) -> list[str]:
    """S4 — active_roles klíče ∈ role grafu (node-id); hodnoty ∈ {active, inactive, done}."""
    out: list[str] = []
    roles = section(sections, "Active roles").get("active_roles")
    if not isinstance(roles, dict):
        return ["S4 chybí 'active_roles' mapa v sekci '## Active roles'"]
    for role, state in roles.items():
        if role not in graph:
            out.append(f"S4 active_roles: neznámá role '{role}' (∉ uzly grafu)")
        if str(state).strip() not in ROLE_STATES:
            out.append(f"S4 active_roles: role '{role}' má neznámý stav '{state}' (z {sorted(ROLE_STATES)})")
    return out


def report(config: str, sections: dict[str, dict], findings: list[str]) -> None:
    print(f"config:    {config}")
    print(f"sekce:     {len(sections)}   project_type: {section(sections, 'Projekt').get('project_type', '-')}")
    if not findings:
        print("RESULT: OK — projekt má správný PRODUCT-layer tvar.")
        sys.exit(0)
    print(f"RESULT: {len(findings)} nález(ů):")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    config = argv[0] if argv else "project-config.md"
    if not os.path.isfile(config):
        print(f"CHYBA: chybí {config} (PRODUCT vrstva projektu).", file=sys.stderr)
        sys.exit(2)

    text = open(config, encoding="utf-8").read()
    sections = parse_sections(text)
    graph_file = find_graph()
    graph = Graph.load(graph_file) if graph_file else Graph({}, [], {}, {})

    findings: list[str] = []
    findings += check_sections(sections)
    findings += check_paths(sections)
    findings += check_project_type(sections)
    findings += check_active_roles(sections, graph)

    report(config, sections, findings)


if __name__ == "__main__":
    main()
