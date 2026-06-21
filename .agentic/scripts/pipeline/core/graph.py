#!/usr/bin/env python3
"""graph.py — doménový model pipeline grafu: Node (+ podtřídy) · Edge · Graph.

Engine přestal sahat na syrové dicty z delivery.yaml a iteruje nad objekty: uzly znají
svůj typ (polymorfně) a svou aktivaci, hrany svůj `when` predikát a směr, graf nabízí
dotazy (forward producenti / return cíle / dosažitelnost) místo ručních deps-dictů.
`when` se parsuje při loadu (Predicate). Load je LENIENTNÍ — i rozbitý graf se načte
(check.py ho musí umět projít a reportovat); neznámý node-type → generický Node.
"""
import os
import sys
from typing import Iterator, Protocol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_graph
from predicate import EvalContext, Predicate


class ActivationContext(EvalContext, Protocol):
    """EvalContext (pro Edge.when / Predicate) rozšířený o aktivační status, který
    Node.is_active potřebuje: `role_status` (node-id → active/inactive z active_roles)
    + `agent_status` (zpětná kompat, keyed by agent short). Naplňuje frontier.Ctx."""

    role_status: dict[str, str]
    agent_status: dict[str, str]


# ── Node ──────────────────────────────────────────────────────────────────────
class Node:
    """Uzel grafu = ROLE (capability). `agent` je jen cast binding (persona)."""
    type: str = "agent"          # default i pro uzel bez explicitního type
    _CATEGORY: str | None = None  # drive partition kategorie; None = generický/neznámý uzel (lenientní)

    def __init__(self, nid: str, raw: dict | None) -> None:
        self.id = nid
        self.raw: dict = raw or {}
        self.type = self.raw.get("type", type(self).type)
        self.agent = self.raw.get("agent")
        self.phase = self.raw.get("phase")
        self.model = self.raw.get("model")
        self.level = self.raw.get("level")
        self.interaction = self.raw.get("interaction")
        self.desc = self.raw.get("desc")
        self.inputs: list = list(self.raw.get("inputs") or [])
        self.outputs: list = list(self.raw.get("outputs") or [])
        self.requires: list | None = self.raw.get("requires")   # None = neuvedeno (≠ prázdný list)
        self.readonly = bool(self.raw.get("readonly", False))
        self.failure_limit = self.raw.get("failure_limit")
        self.when = Predicate.of(self.raw.get("when"))
        # skip_if (FIX #2): predikát, jehož PRAVDIVOST → uzel auto-PASS (lehká dráha přeskočí
        # feasibility+architecture). Vyhodnocuje frontier; UNKNOWN/judgment = NEskipuj (fail-safe).
        self.skip_if = Predicate.of(self.raw.get("skip_if"))

    def is_active(self, ctx: ActivationContext) -> str:
        """('active'|'inactive'|'unknown') — activation (role) + agent backcompat + when predikát."""
        if ctx.role_status.get(self.id) == "inactive":      # active_roles gatuje ROLI (node-id)
            return "inactive"
        if self.agent and ctx.agent_status.get(self.agent) == "inactive":  # zpětná kompat (agents:)
            return "inactive"
        if self.when.root is not None:
            c = self.when.classify(ctx)
            if c == "skip":
                return "inactive"
            if c == "judgment":
                return "unknown"
        return "active"

    def blocking(self, interactions: dict) -> bool:
        """Jen human-gate: blokuje běh? (interactions.blocking, fallback level==L3)."""
        return False

    def drive_category(self, blocking: bool = False) -> str | None:
        """Kategorie pro drive partition (JOIN/TERMINAL/WORKER/ROUTER/…); polymorfně dle typu
        uzlu místo string-žebříku v run.py. Human-gate dělí dle resolvnutého `blocking`."""
        return self._CATEGORY

    def io_names(self) -> list:
        return list(self.inputs) + list(self.outputs)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.id!r})"


class AgentNode(Node):
    type = "agent"
    _CATEGORY = "WORKER"


class GateNode(Node):
    type = "gate"
    _CATEGORY = "WORKER"


class HumanGateNode(Node):
    type = "human-gate"

    def blocking(self, interactions: dict) -> bool:
        ix = (interactions or {}).get(self.interaction, {}) or {}
        return bool(ix.get("blocking", self.level == "L3"))

    def drive_category(self, blocking: bool = False) -> str | None:
        return "BLOCKING_GATE" if blocking else "FREE_GATE"


class RouterNode(Node):
    type = "router"
    _CATEGORY = "ROUTER"


class JoinNode(Node):
    type = "join"
    _CATEGORY = "JOIN"


class TerminalNode(Node):
    type = "terminal"
    _CATEGORY = "TERMINAL"


_NODE_CLASSES: dict[str, type[Node]] = {
    c.type: c for c in
    (AgentNode, GateNode, HumanGateNode, RouterNode, JoinNode, TerminalNode)}


def make_node(nid: str, raw: dict | None) -> Node:
    """Factory: typovaný Node dle `type`; neznámý type → generický Node (lenientní load)."""
    cls = _NODE_CLASSES.get((raw or {}).get("type", "agent"), Node)
    return cls(nid, raw)


# ── Edge ──────────────────────────────────────────────────────────────────────
class Edge:
    """Hrana drátuje ROLE (ne jména). `to` je vždy list (single → [single]). Faithful
    k dřívějšímu edge_targets: chybějící `to` → [None] (check to reportuje jako C2)."""

    def __init__(self, raw: dict | None) -> None:
        self.raw: dict = raw or {}
        self.frm = self.raw.get("from")
        t = self.raw.get("to")
        self.to: list = t if isinstance(t, list) else [t]
        self.kind = self.raw.get("kind", "normal")
        self.counter = self.raw.get("counter")
        self.when = Predicate.of(self.raw.get("when"))

    def is_return(self) -> bool:
        return self.kind == "return"

    def is_forward(self) -> bool:
        return self.kind != "return"

    def live_targets(self) -> list:
        return [t for t in self.to if t]

    def __repr__(self) -> str:
        return f"Edge({self.frm!r}→{self.to!r}, kind={self.kind!r})"


# ── Graph ─────────────────────────────────────────────────────────────────────
class Graph:
    def __init__(self, nodes: dict[str, Node], edges: list[Edge],
                 meta: dict | None, raw: dict) -> None:
        self.nodes = nodes        # dict: id -> Node
        self.edges = edges        # list[Edge]
        self.meta: dict = meta or {}
        self.entry = self.meta.get("entry")
        self.raw = raw

    @classmethod
    def load(cls, path: str) -> "Graph":
        data = load_graph(path)
        nodes = {nid: make_node(nid, n) for nid, n in (data.get("nodes") or {}).items()}
        edges = [Edge(e) for e in (data.get("edges") or [])]
        return cls(nodes, edges, data.get("meta") or {}, data)

    # ── iterace ───────────────────────────────────────────────────────────────
    def __contains__(self, nid: object) -> bool:
        return nid in self.nodes

    def __iter__(self) -> Iterator[str]:
        return iter(self.nodes)

    def get(self, nid: str) -> Node | None:
        return self.nodes.get(nid)

    def nodes_by_type(self, t: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.type == t]

    def has_type(self, t: str) -> bool:
        return any(n.type == t for n in self.nodes.values())

    # ── hrany ─────────────────────────────────────────────────────────────────
    def forward_edges(self) -> list[Edge]:
        return [e for e in self.edges if e.is_forward()]

    def edges_from(self, nid: str) -> list[Edge]:
        return [e for e in self.edges if e.frm == nid]

    def return_edges_from(self, nid: str) -> list[Edge]:
        return [e for e in self.edges if e.is_return() and e.frm == nid]

    def forward_producers(self) -> dict[str, list[str]]:
        """{node_id: [src,...]} forward (non-return) producenti — dataflow kostra (C11/C12)."""
        prod: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for e in self.forward_edges():
            for t in e.to:
                if t in prod and e.frm in self.nodes:
                    prod[t].append(e.frm)
        return prod

    def return_target_for_fault(self, nid: str, fault: str) -> str | None:
        """Return cíl pro diagnostikovaný fault (hrana s atomem `fault == <fault>`)."""
        for e in self.return_edges_from(nid):
            if e.when.has_fault(fault):
                tos = e.live_targets()
                if tos:
                    return tos[0]
        return None

    def single_return_target(self, nid: str) -> str | None:
        """Právě 1 distinct return cíl z uzlu → engine routuje bez fault; jinak None."""
        rets = [t for e in self.return_edges_from(nid) for t in e.live_targets()]
        return rets[0] if len(set(rets)) == 1 else None

    # ── dosažitelnost (check) ───────────────────────────────────────────────────
    def adjacency(self) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for e in self.edges:
            if e.frm in adj:
                adj[e.frm] += [t for t in e.to if t in self.nodes]
        return adj

    def reachable(self, start: str | None, skip: str | None = None,
                  adj: dict[str, list[str]] | None = None) -> set[str]:
        adj = adj if adj is not None else self.adjacency()
        seen: set[str] = set()
        stack: list[str] = [start] if (start is not None and start in self.nodes) else []
        while stack:
            x = stack.pop()
            if x in seen or x == skip:
                continue
            seen.add(x)
            for y in adj.get(x, []):
                if y != skip:
                    stack.append(y)
        return seen

    def all_predicates(self) -> Iterator[tuple[Predicate, str]]:
        """(predikát, where-label) přes uzly i hrany — vstup pro slovníkovou validaci (C14)."""
        for nid, n in self.nodes.items():
            yield n.when, f"node '{nid}'"
        for e in self.edges:
            yield e.when, f"edge {e.frm}→{e.to}"
