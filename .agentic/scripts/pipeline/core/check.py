#!/usr/bin/env python3
"""check.py — validátor integrity pipeline grafu (read-only guardrail) (z check.sh).

Drží delivery.yaml konzistentní s agent rosterem a vynucuje strict spec-driven invariant
+ flow-blind agenty + řízené slovníky + próza↔graf most. Kontroly C1–C17 (každá = funkce
vracející nálezy): C1–C12 graf/typy, C13 flow-blind, C14 known flagy/hodnoty ve `when`,
C15 known node-type/edge-kind/phase, C16 próza↔graf (flow.md sliby bran = uzly v grafu),
C17 forward-acyclic (forward hrany = DAG; cyklus = stale-reopen smyčka → frontier ghost).

Konzumuje doménový model: `Graph` (adjacency/reachable/forward_producers + dotazy),
`Vocabulary` (slovníky) a `Predicate.problems()` (C14 padá zadarmo z parsovaného AST —
konec duplicitního regex when-parseru).

CLI:   python3 check.py [pipeline/delivery.yaml]
Závislost: python3 + PyYAML. Exit: 0 = OK | 1 = nálezy | 2 = chyba.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RESULT_OUTCOMES, require_graph, sibling, yaml
from graph import Graph
from vocab import Vocabulary

SPEC_AUTHORITY = "product"
PRODUCER_PHASES = {"T2", "T3-post"}
INTERACTION_KINDS = {"choice", "approval", "ack", "upload", "text", "delegate-or-provide"}
EXEMPT13 = {"eywa-meta"}                                  # kurátor cast registru (persona = data)
FLOWBLIND_META = {"watson-interviewer", "monk-ideation"}  # ne-delivery, ale taky flow-blind


def find_agents_dir() -> str:
    for d in (".agentic/agents", "agents"):
        if os.path.isdir(d):
            return d
    return ""


def agent_shorts(agents_dir: str) -> set[str]:
    shorts: set[str] = set()
    if agents_dir:
        for f in glob.glob(os.path.join(agents_dir, "*.md")):
            base = os.path.basename(f)[:-3]
            if base not in ("INDEX", "OVERVIEW"):
                shorts.add(base)
    return shorts


def require_valid_yaml(graph_file: str) -> None:
    """C1 — graf je validní YAML (gate; Graph.load staví doménový model nad týmiž daty)."""
    try:
        yaml.safe_load(open(graph_file, encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"C1 FAIL: nevalidní YAML: {exc}", file=sys.stderr)
        sys.exit(2)


def load_sidecar(graph_file: str, name: str, key: str, code: str, findings: list[str]) -> dict | None:
    """Registr vedle grafu (artifacts/interactions). None = chybí (→ SKIP), {} = nevalidní
    YAML (+ nález <code>), dict = ok."""
    path = sibling(graph_file, name)
    if not os.path.isfile(path):
        return None
    try:
        return (yaml.safe_load(open(path, encoding="utf-8")) or {}).get(key, {}) or {}
    except yaml.YAMLError as exc:
        findings.append(f"{code} {name} nevalidní YAML: {exc}")
        return {}


# ── kontroly C2–C15 (každá vrací nálezy; SKIP tiskne přímo) ─────────────────────
def check_references(graph: Graph) -> list[str]:
    """C2 — entry + hrany ukazují na existující uzly; C3 — requires → existující uzel."""
    out: list[str] = []
    entry = graph.entry
    if entry not in graph:
        out.append(f"C2 entry '{entry}' není uzel grafu")
    for e in graph.edges:
        for nid in [e.frm] + e.to:
            if nid not in graph:
                out.append(f"C2 hrana odkazuje na neexistující uzel: {nid} ({e.raw})")
    for nid, n in graph.nodes.items():
        for req in (n.requires or []):
            if req not in graph:
                out.append(f"C3 {nid}.requires → neexistující uzel: {req}")
    return out


def check_agents(graph: Graph, agents_dir: str) -> list[str]:
    """C4 — agent (cast binding) je ve sboru. Chybí roster → SKIP (mimo projekt/framework)."""
    shorts = agent_shorts(agents_dir)
    if not shorts:
        print("C4 SKIP: agent roster nenalezen (mimo projekt/framework).")
        return []
    out: list[str] = []
    for nid, n in graph.nodes.items():
        if n.agent and n.agent not in shorts:
            out.append(f"C4 uzel '{nid}' odkazuje na neznámého agenta: {n.agent}")
    return out


def check_reachability(graph: Graph, adj: dict, producers: list[str]) -> list[str]:
    """C5 dead-end · C6 orphan · C7 spec-driven invariant (uzel = role; spec autorita 'product')."""
    out: list[str] = []
    entry = graph.entry
    for nid, n in graph.nodes.items():
        if n.type != "terminal" and not adj.get(nid):
            out.append(f"C5 dead-end: uzel '{nid}' (ne-terminal) nemá odchozí hranu")
    reach = graph.reachable(entry, adj=adj)
    for nid in graph.nodes:
        if nid not in reach:
            out.append(f"C6 orphan: uzel '{nid}' nedosažitelný z entry '{entry}'")
    if SPEC_AUTHORITY not in graph:
        out.append(f"C7 spec autorita '{SPEC_AUTHORITY}' chybí v grafu")
    else:
        reach_wo_spec = graph.reachable(entry, skip=SPEC_AUTHORITY, adj=adj)
        leaked = [p for p in producers if p in reach_wo_spec]
        if leaked:
            out.append("C7 SPEC-DRIVEN PORUŠEN: produkující uzly dosažitelné z entry "
                       f"bez '{SPEC_AUTHORITY}': {', '.join(sorted(leaked))} "
                       "(kód/kontrakt bez spec autority — constitution §1)")
    return out


def check_typed_io(graph: Graph, artifacts: dict | None) -> list[str]:
    """C8 — I/O typy ∈ artifacts; C9 — konzumovaný typ má producenta (i abstract subtype)."""
    if artifacts is None:
        print("C8/C9 SKIP: pipeline/artifacts.yaml nenalezen (typované I/O neověřeno).")
        return []
    out: list[str] = []
    for nid, n in graph.nodes.items():
        for name in n.io_names():
            if name not in artifacts:
                out.append(f"C8 uzel '{nid}': neznámý artifact typ '{name}' (není v artifacts.yaml)")
    produced: set = set()
    for n in graph.nodes.values():
        produced.update(n.outputs)

    def satisfied(t: str) -> bool:
        a = artifacts.get(t)
        if a is None:
            return True
        if a.get("kind") == "source" or a.get("external"):
            return True
        if t in produced:
            return True
        if a.get("abstract"):
            return any(s in produced for s in (a.get("subtypes") or []))
        return False

    consumed: set = set()
    for n in graph.nodes.values():
        consumed.update(n.inputs)
    for t in sorted(consumed):
        if t in artifacts and not satisfied(t):
            out.append(f"C9 typ '{t}' je konzumován, ale nikdo ho neprodukuje (ani abstract subtype)")
    return out


def check_interactions(graph: Graph, interactions: dict | None, artifacts: dict | None) -> list[str]:
    """C10 — human-gate má známou interakci; interakce má známý kind + typované `produces` (P5)."""
    if interactions is None:
        print("C10 SKIP: pipeline/interactions.yaml nenalezen (human-gate interakce neověřeny).")
        return []
    out: list[str] = []
    for nid, n in graph.nodes.items():
        if n.type == "human-gate":
            iref = n.interaction
            if not iref:
                out.append(f"C10 human-gate '{nid}' nemá pole 'interaction'")
            elif iref not in interactions:
                out.append(f"C10 human-gate '{nid}': neznámá interakce '{iref}'")
    for iid, idef in interactions.items():
        idef = idef or {}
        k = idef.get("kind")
        if k not in INTERACTION_KINDS:
            out.append(f"C10 interakce '{iid}': neznámý kind '{k}' (z {sorted(INTERACTION_KINDS)})")
        out += _check_produces(iid, idef, artifacts)
    return out


def _check_produces(iid: str, idef: dict, artifacts: dict | None) -> list[str]:
    """C10 typované I/O (P5): `produces` = { artifact: <∈artifacts> } NEBO { outcome: <∈vocabulary> }."""
    produces = idef.get("produces")
    if not isinstance(produces, dict):
        return [f"C10 interakce '{iid}': chybí typovaný 'produces' (artifact|outcome)"]
    if "artifact" in produces:
        t = produces["artifact"]
        if artifacts is not None and t not in artifacts:
            return [f"C10 interakce '{iid}': produces.artifact '{t}' není v artifacts.yaml"]
    elif "outcome" in produces:
        o = produces["outcome"]
        if o not in RESULT_OUTCOMES:
            return [f"C10 interakce '{iid}': produces.outcome '{o}' není z {sorted(RESULT_OUTCOMES)}"]
    else:
        return [f"C10 interakce '{iid}': produces musí mít 'artifact' nebo 'outcome'"]
    return []


def check_dataflow(graph: Graph) -> list[str]:
    """C11 dataflow-orphan (žádný forward producent) · C12 join.requires odvoditelný z hran."""
    out: list[str] = []
    entry = graph.entry
    fwd = graph.forward_producers()
    for nid in graph.nodes:
        if nid != entry and not fwd[nid]:
            out.append(f"C11 dataflow-orphan: '{nid}' nemá forward (non-return) producenta "
                       "(frontier ho nikdy neudělá ready)")
    for nid, n in graph.nodes.items():
        if n.type == "join" and n.requires is not None:
            req, prod = set(n.requires or []), set(fwd[nid])
            if req != prod:
                out.append(f"C12 {nid}.requires {sorted(req)} ≠ forward producenti "
                           f"{sorted(prod)} (requires je odvoditelný z hran — sjednoť)")
    return out


def check_forward_acyclic(graph: Graph) -> list[str]:
    """C17 cycle-guard — forward (non-return) hrany MUSÍ tvořit DAG. Return hrany jsou
    záměrné zpětné hrany (re-flow), ty se sem nepočítají.

    Proč staticky na `check`: cyklus v dataflow kostře (např. ux-design↔ui-system z findingu #2)
    je STRUKTURÁLNÍ SPOUŠTĚČ runtime ghostů ve frontieru — dva uzly se navzájem stale-reopenují,
    promují se do inflight a smiřovací logika (frontier #3) je sice runtime uklidí, ale graf je
    chybně zapojený. C17 to chytne v authoring/`check` gate, NEŽ vznikne runtime stav (fail-fast,
    constitution §Filozofie #7: deterministická vlastnost grafu = skript, ne oko). Doplňuje runtime
    smíření obranou do hloubky: smíření drží integritu i kdyby cyklus prošel; C17 cyklus nepustí."""
    fwd = graph.forward_producers()                # {node: [forward src,...]}
    succ: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
    for tgt, srcs in fwd.items():
        for s in srcs:
            if s in succ:
                succ[s].append(tgt)
    # DFS s 3-barevným značením (white=0/gray=1/black=2) → první gray-hit = zpětná hrana v cyklu.
    color: dict[str, int] = {nid: 0 for nid in graph.nodes}
    cycle: list[str] = []

    def visit(nid: str, path: list[str]) -> bool:
        color[nid] = 1
        path.append(nid)
        for nxt in succ.get(nid, []):
            if color[nxt] == 1:                    # gray → cyklus; vyřízni úsek path
                cycle.extend(path[path.index(nxt):] + [nxt])
                return True
            if color[nxt] == 0 and visit(nxt, path):
                return True
        path.pop()
        color[nid] = 2
        return False

    for nid in graph.nodes:
        if color[nid] == 0 and visit(nid, []):
            return [f"C17 CYKLUS v forward grafu: {' → '.join(cycle)} "
                    "(forward hrany musí být DAG; cyklus = stale-reopen smyčka → frontier ghost. "
                    "Použij return hranu pro re-flow, ne forward zpětnou hranu)"]
    return []


def check_flowblind(graph: Graph, agents_dir: str) -> list[str]:
    """C13 — delivery agenti + flow-blind meta (watson/monk) nesmí jmenovat jiného agenta
    (short ani first-name s routing slovesem) ani mít routing sekci. Eywa = JEDINÁ výjimka
    (kurátor cast registru — persona-jména u ní bydlí jako data, ne jako flow)."""
    if not agents_dir:
        return []
    delivery_shorts = {n.agent for n in graph.nodes.values() if n.agent}
    all_shorts = delivery_shorts | FLOWBLIND_META | EXEMPT13
    first_names = _agent_first_names(agents_dir)
    out: list[str] = []
    to_check = sorted(s for s in (delivery_shorts | FLOWBLIND_META) if s and s not in EXEMPT13)
    for short in to_check:
        path = os.path.join(agents_dir, short + ".md")
        if not os.path.isfile(path):
            continue
        t0 = open(path, encoding="utf-8").read()
        if "## Handoff target" in t0 or "## Gates a schvalování" in t0:
            out.append(f"C13 agent '{short}' má routing sekci (Handoff target / Gates) — flow patří grafu")
        for s2 in sorted(all_shorts):
            if not s2 or s2 == short:
                continue
            if s2 in t0:
                out.append(f"C13 agent '{short}' jmenuje jiného agenta (short '{s2}') — agent je slepý vůči flow")
            fn = first_names.get(s2)
            if fn and re.search(rf"(→|vrac\w*|předáv?\w*|eskal\w*)\s+\**{re.escape(fn)}", t0):
                out.append(f"C13 agent '{short}' routuje na '{fn}' (jméno kolegy) — flow patří grafu")
    return out


def _agent_first_names(agents_dir: str) -> dict[str, str]:
    """{short: first-name z `name:` frontmatteru} — pro C13 routing-sloveso detekci."""
    names: dict[str, str] = {}
    for f in glob.glob(os.path.join(agents_dir, "*.md")):
        base = os.path.basename(f)[:-3]
        if base in ("INDEX", "OVERVIEW"):
            continue
        try:
            t0 = open(f, encoding="utf-8").read()
        except OSError:
            continue
        mnm = re.search(r"^name:\s*(\S+)", t0, re.M)
        if mnm:
            names[base] = mnm.group(1)
    return names


def check_prose_gates(graph: Graph) -> list[str]:
    """C16 — próza↔graf 1:1: brány slíbené ve flow.md (§Stop body / §Lint gate) mají uzel
    v grafu. Strojový most = `meta.prose_gates` (deklarovaný kontrakt). Pro každý slib
    ověř, že `node` existuje a má očekávaný `type`. Tím třída driftu „próza slibuje bránu,
    graf ji nemá" (díry A1–A3) padne hlučně, ne tiše. Chybí registr → SKIP (graceful)."""
    pg = (graph.meta or {}).get("prose_gates")
    if pg is None:
        print("C16 SKIP: meta.prose_gates nedeklarován (próza↔graf most neověřen).")
        return []
    out: list[str] = []
    if not isinstance(pg, list):
        return ["C16 meta.prose_gates musí být list slibů { id, node, type }"]
    for entry in pg:
        entry = entry or {}
        pid = entry.get("id", "?")
        node = entry.get("node")
        want_type = entry.get("type")
        if not node:
            out.append(f"C16 prose_gate '{pid}': chybí pole 'node' (na který uzel próza míří)")
            continue
        n = graph.get(node)
        if n is None:
            out.append(f"C16 prose_gate '{pid}': flow.md slibuje bránu, ale uzel '{node}' "
                       "v grafu CHYBÍ (próza↔graf drift — přidej uzel nebo sundej slib)")
            continue
        if want_type and n.type != want_type:
            out.append(f"C16 prose_gate '{pid}': uzel '{node}' má type '{n.type}', "
                       f"próza čeká '{want_type}'")
    return out


def check_vocabulary(graph: Graph, graph_file: str) -> list[str]:
    """C14 known flagy/hodnoty ve `when` (přes Predicate.problems) · C15 known node-type/
    edge-kind/phase. Fail-closed: neznámá hodnota = nález. Chybí registr → SKIP."""
    out: list[str] = []
    vocab_raw: dict | None = None
    vpath = sibling(graph_file, "vocabulary.yaml")
    if os.path.isfile(vpath):
        try:
            vocab_raw = yaml.safe_load(open(vpath, encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            vocab_raw = {}
            out.append(f"C14 vocabulary.yaml nevalidní YAML: {exc}")
    if vocab_raw is None:
        print("C14/C15 SKIP: pipeline/vocabulary.yaml nenalezen (slovníky neověřeny).")
        return out
    vocab = Vocabulary(vocab_raw)
    for nid, n in graph.nodes.items():
        out += n.when.problems(vocab, f"node '{nid}'")
        out += n.skip_if.problems(vocab, f"node '{nid}' skip_if")   # FIX #2: skip_if v C14 schématu
        if vocab.node_types and n.type not in vocab.node_types:
            out.append(f"C15 node '{nid}': neznámý type '{n.type}' (∉ {sorted(vocab.node_types)})")
        if n.phase is not None and vocab.phases and n.phase not in vocab.phases:
            out.append(f"C15 node '{nid}': neznámá phase '{n.phase}' (∉ {sorted(vocab.phases)})")
    for e in graph.edges:
        out += e.when.problems(vocab, f"edge {e.frm}→{e.to}")
        ek = e.raw.get("kind")   # raw: chybějící kind = None (ne default "normal") → neověřuj
        if ek is not None and vocab.edge_kinds and ek not in vocab.edge_kinds:
            out.append(f"C15 edge {e.frm}→{e.to}: neznámý kind '{ek}' (∉ {sorted(vocab.edge_kinds)})")
    return out


def report(graph_file: str, graph: Graph, artifacts: dict | None,
           producers: list[str], findings: list[str]) -> None:
    print(f"graph:     {graph_file}")
    print(f"nodes:     {len(graph.nodes)}   edges: {len(graph.edges)}   entry: {graph.entry}")
    if artifacts is not None:
        print(f"artifacts: {len(artifacts)} typů")
    print(f"producers: {', '.join(sorted(producers))}")
    if not findings:
        print("RESULT: OK — graf konzistentní, spec-driven invariant drží.")
        sys.exit(0)
    print(f"RESULT: {len(findings)} nález(ů):")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    graph_file = require_graph(argv[0] if argv else None)
    agents_dir = find_agents_dir()

    require_valid_yaml(graph_file)              # C1 gate (exit 2 na nevalidní YAML)
    graph = Graph.load(graph_file)              # lenientní load — i rozbitý graf se načte
    findings: list[str] = []
    artifacts = load_sidecar(graph_file, "artifacts.yaml", "artifacts", "C8", findings)
    interactions = load_sidecar(graph_file, "interactions.yaml", "interactions", "C10", findings)
    producers = [n.id for n in graph.nodes.values()
                 if n.type == "agent" and n.phase in PRODUCER_PHASES]
    adj = graph.adjacency()

    findings += check_references(graph)                 # C2, C3
    findings += check_agents(graph, agents_dir)         # C4
    findings += check_reachability(graph, adj, producers)   # C5, C6, C7
    findings += check_typed_io(graph, artifacts)        # C8, C9
    findings += check_interactions(graph, interactions, artifacts)  # C10
    findings += check_dataflow(graph)                   # C11, C12
    findings += check_forward_acyclic(graph)            # C17
    findings += check_flowblind(graph, agents_dir)      # C13
    findings += check_vocabulary(graph, graph_file)     # C14, C15
    findings += check_prose_gates(graph)                # C16

    report(graph_file, graph, artifacts, producers, findings)


if __name__ == "__main__":
    main()
