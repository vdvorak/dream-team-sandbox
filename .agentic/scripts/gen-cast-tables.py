#!/usr/bin/env python3
"""gen-cast-tables.py — generuje derivovatelné cast tabulky z delivery.yaml + frontmatterů.

N6 (determinism-audit): cast tabulka, dispatch po fázích a model-strategy přehled v
INDEX.md/OVERVIEW.md jsou MECHANICKÉ PROJEKCE grafu (`delivery.yaml`: `id:`+`agent:`+`model:`+`phase:`)
a agent frontmatterů (`name`, `role`, `universe`, `model`). Dřív je Eywa psala ručně při každé
změně cast → stárly. Tenhle skript je vygeneruje; ruční psaní těchhle bloků odpadá.

HRANICE (constitution §Filozofie #7):
  - GENEROVANÉ (tady): tabulky odvozené z grafu = stejný vstup → stejný výstup, žádný úsudek.
  - AUTORSKÉ (skript nesahá): dispatch diagram (ASCII flow), workflow graf, return-paths próza,
    sloupec "Proč" u model-strategy, activation profily, meta-agent triggery. To je úsudek/vysvětlení
    a zůstává ruční (drift proti grafu hlídá agent-graph-check.sh N6, ne tenhle skript).

Skript přepisuje JEN obsah mezi značkami `<!-- GENERATED: <blok> -->` … `<!-- /GENERATED: <blok> -->`.
Próza mimo značky zůstává netknutá. Bloky:
  cast-index       — INDEX.md §Cast standardní-flow tabulka (short|jméno|role|funkce|universe)
  model-strategy   — INDEX.md §Model strategy tabulka agentů per tier (BEZ sloupce "Proč" = autorský)
  cast-overview    — OVERVIEW.md §Cast standardní-flow tabulka (short|jméno|role|fáze|default model)

Usage:
  python3 .agentic/scripts/gen-cast-tables.py           # přepíše bloky in-place
  python3 .agentic/scripts/gen-cast-tables.py --check    # exit!=0 pokud by se obsah lišil (CI/preflight)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# ── Lokalizace zdrojů (běží z root projektu i z .agentic/) ────────────────────
HERE = Path(__file__).resolve().parent          # …/.agentic/scripts
AGENTIC = HERE.parent                           # …/.agentic
AGENTS_DIR = AGENTIC / "agents"
DELIVERY = AGENTIC / "pipeline" / "delivery.yaml"
INDEX_MD = AGENTS_DIR / "INDEX.md"
OVERVIEW_MD = AGENTS_DIR / "OVERVIEW.md"

# Meta-persony stojí mimo standardní flow → nemají uzel v grafu (jen autorské tabulky).
META_PERSONAS = {"eywa-meta", "watson-interviewer", "monk-ideation"}

BEGIN = "<!-- GENERATED: {name} — needituj ručně, spusť scripts/gen-cast-tables.py -->"
END = "<!-- /GENERATED: {name} -->"


# ── Načtení dat ───────────────────────────────────────────────────────────────
def load_frontmatters() -> dict[str, dict[str, str]]:
    """short → {name, role, universe, model} z agent frontmatterů."""
    out: dict[str, dict[str, str]] = {}
    for f in sorted(AGENTS_DIR.glob("*.md")):
        if f.name in {"INDEX.md", "OVERVIEW.md", "ARCHITECTURE.md"}:
            continue
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        short = fm.get("short")
        if not short:
            continue
        out[short] = {
            "name": str(fm.get("name", "")),
            "role": str(fm.get("role", "")),
            "universe": str(fm.get("universe", "")),
            "model": str(fm.get("model", "")),
        }
    return out


def load_graph() -> dict:
    return yaml.safe_load(DELIVERY.read_text(encoding="utf-8"))


def graph_bindings(graph: dict) -> list[dict[str, str]]:
    """Pořadí uzlů z grafu → list {agent, role(node-id), phase, model}.

    Jeden agent může plnit víc rolí (uzlů); každý uzel = řádek. Zachová pořadí z YAML
    (= pořadí ve flow), deduplikuje (agent, role) páry — production/monitor sdílí alfred-devops
    s devops uzlem, ale jsou to různé role → různé řádky; stejnou roli 2× neuvedeme.
    """
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node_id, node in (graph.get("nodes") or {}).items():
        if not isinstance(node, dict):
            continue
        agent = node.get("agent")
        if not agent:
            continue
        key = (agent, node_id)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "agent": agent,
                "role": node_id,
                "phase": str(node.get("phase", "")),
                "model": str(node.get("model", "")),
            }
        )
    return rows


# ── Sestavení tabulek ─────────────────────────────────────────────────────────
def first_role_per_agent(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Pro cast tabulku: jeden řádek per agent = jeho PRIMÁRNÍ (první v grafu) uzel.

    alfred-devops má devops/production/monitor — primární je první výskyt (devops). Další
    uzly téhož agenta zmíníme jako '(+ role/…)' jen pokud existují, aby tabulka nezamlčela
    multi-role agenty, ale zůstala 1 řádek/agent (lidsky čitelné).
    """
    primary: dict[str, dict[str, str]] = {}
    extra_roles: dict[str, list[str]] = {}
    for r in rows:
        a = r["agent"]
        if a not in primary:
            primary[a] = r
        else:
            extra_roles.setdefault(a, []).append(r["role"])
    out = []
    for a, r in primary.items():
        rr = dict(r)
        rr["extra_roles"] = extra_roles.get(a, [])
        out.append(rr)
    return out


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def build_cast_index(rows, fm) -> str:
    """INDEX.md §Cast — short | jméno | uzel(role) | funkce | universe."""
    lines = [
        "| Short (persona) | Jméno | Uzel grafu (role) | Funkce | Universe |",
        "|---|---|---|---|---|",
    ]
    for r in first_role_per_agent(rows):
        a = r["agent"]
        meta = fm.get(a, {})
        role_cell = f"`{r['role']}`"
        if r["extra_roles"]:
            role_cell += " (+ " + "/".join(f"`{x}`" for x in r["extra_roles"]) + ")"
        lines.append(
            f"| `{a}` | {md_escape(meta.get('name', ''))} | {role_cell} "
            f"| {md_escape(meta.get('role', ''))} | {md_escape(meta.get('universe', ''))} |"
        )
    return "\n".join(lines)


def build_cast_overview(rows, fm) -> str:
    """OVERVIEW.md §Cast — short | jméno | role | fáze | default model.

    Fáze = sjednocení phase přes všechny uzly agenta (zachová pořadí výskytu). Default model =
    z frontmatteru (= strop; uzlové modely se z něj derivují).
    """
    by_agent: dict[str, dict] = {}
    order: list[str] = []
    for r in rows:
        a = r["agent"]
        if a not in by_agent:
            by_agent[a] = {"phases": [], "role": fm.get(a, {}).get("role", "")}
            order.append(a)
        ph = r["phase"]
        if ph and ph not in by_agent[a]["phases"]:
            by_agent[a]["phases"].append(ph)

    lines = [
        "| Agent | Jméno | Role | Fáze | Default model |",
        "|---|---|---|---|---|",
    ]
    for a in order:
        meta = fm.get(a, {})
        phases = ", ".join(by_agent[a]["phases"])
        lines.append(
            f"| `{a}` | {md_escape(meta.get('name', ''))} | {md_escape(meta.get('role', ''))} "
            f"| {phases} | {md_escape(meta.get('model', ''))} |"
        )
    return "\n".join(lines)


def build_model_strategy(rows, fm) -> str:
    """INDEX.md §Model strategy — agenti seskupení podle default modelu (BEZ sloupce 'Proč').

    'Proč' je autorský úsudek (proč zrovna opus) → zůstává ruční próza nad/pod blokem. Tady jen
    mechanická projekce: který agent má jaký strop. Model bereme z frontmatteru (kanonický strop).
    Tier pořadí opus → sonnet → haiku (od dražšího).
    """
    tier_order = ["opus", "sonnet", "haiku"]
    by_model: dict[str, list[str]] = {}
    order_seen: list[str] = []
    for r in rows:
        a = r["agent"]
        if a in order_seen:
            continue
        order_seen.append(a)
        model = fm.get(a, {}).get("model", "") or r["model"]
        by_model.setdefault(model, []).append(a)

    lines = [
        "| Default model | Agenti |",
        "|---|---|",
    ]
    models = [m for m in tier_order if m in by_model] + [
        m for m in by_model if m not in tier_order
    ]
    for m in models:
        agents = ", ".join(f"`{a}`" for a in by_model[m])
        lines.append(f"| `{m}` | {agents} |")
    return "\n".join(lines)


# ── In-place přepis bloků ─────────────────────────────────────────────────────
def replace_block(text: str, name: str, new_body: str) -> str:
    begin = BEGIN.format(name=name)
    end = END.format(name=name)
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    replacement = f"{begin}\n{new_body}\n{end}"
    if not pattern.search(text):
        raise SystemExit(
            f"FAIL: značky pro blok '{name}' nenalezeny v cílovém souboru.\n"
            f"  Očekávám:\n    {begin}\n    …\n    {end}\n"
            f"  Vlož je ručně 1× kolem místa, kam tabulka patří."
        )
    return pattern.sub(lambda _: replacement, text, count=1)


def main() -> int:
    check_only = "--check" in sys.argv[1:]

    fm = load_frontmatters()
    graph = load_graph()
    rows = graph_bindings(graph)

    targets = [
        (
            INDEX_MD,
            [
                ("cast-index", build_cast_index(rows, fm)),
                ("model-strategy", build_model_strategy(rows, fm)),
            ],
        ),
        (
            OVERVIEW_MD,
            [
                ("cast-overview", build_cast_overview(rows, fm)),
            ],
        ),
    ]

    drift = False
    for path, blocks in targets:
        original = path.read_text(encoding="utf-8")
        updated = original
        for name, body in blocks:
            updated = replace_block(updated, name, body)
        if updated != original:
            drift = True
            if check_only:
                print(f"DRIFT: {path.name} — generované bloky nejsou aktuální")
            else:
                path.write_text(updated, encoding="utf-8")
                print(f"updated: {path.name}")
        else:
            print(f"ok: {path.name} — beze změny")

    if check_only:
        if drift:
            print("---\ngen-cast-tables: DRIFT (spusť bez --check pro regeneraci)")
            return 1
        print("---\ngen-cast-tables: AKTUÁLNÍ")
        return 0
    print("---\ngen-cast-tables: hotovo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
