#!/usr/bin/env python3
"""frontier.py — deterministicky spočítá další uzel(y) v pipeline grafu (z next.sh).

Routing dělá kód, ne LLM: agent dodá jen VÝSLEDEK uzlu (PASS/FAIL/…), tahle vrstva
z grafu + project flagů + run-stavu spočítá ready/judgment/waiting množinu (frontier
dataflow ready-rule + incremental-rebuild staleness), nebo kandidáty single-node režimu.

CLI:
  python3 frontier.py --from <node> [--outcome PASS|FAIL|APPROVED] [--class feature|…]
                      [--run current-run.md] [--flag has_db=true …] [--targets web,mobile]
                      [--emit text|json|frontier]
  (bez --from se vezme active_node z current-run.md)

Importovatelné: `frontier_for_state(st)` vrátí frontier dict přímo (run.py to volá místo
subprocess+JSON). Závislost: python3 + PyYAML.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import (coerce_flag, expand_type, load_artifacts, load_yaml,
                    sibling, state_only, yaml)
from graph import Graph
from predicate import Predicate
from runstate import RunState

Dep = tuple   # (src node-id, edge.when: Predicate) — jedna live dep hrana; src je z YAML (dynamický)


class Ctx:
    """EvalContext: flagy + cls/outcome + activation status. `when` predikáty vyhodnocuje
    Predicate AST (predicate.py), aktivaci uzlu Node.is_active — oboje si od Ctx vezme jen
    flag-resolution (.flag/.flags/.cls/.outcome) a status mapy (.role_status/.agent_status).
    Graf drží jako `.graph` (Graph objekt)."""

    def __init__(self, graph: Graph, artifacts: dict | None, flags: dict, targets: set[str],
                 targets_declared: bool, agent_status: dict[str, str], cls: str | None,
                 outcome: str | None, role_status: dict[str, str] | None = None) -> None:
        self.graph = graph
        self.artifacts = artifacts
        self.flags, self.targets, self.targets_declared = flags, targets, targets_declared
        self.agent_status, self.cls, self.outcome = agent_status, cls, outcome
        self.role_status = role_status or {}   # node-id (role) -> active/inactive (active_roles)

    def flag(self, name: str) -> object:
        """True/False/None(unknown). Deklarované active_targets (i prázdné) autoritativní;
        touches_db default = has_db (feature-level, B2)."""
        if name in self.flags:
            return self.flags[name]
        if name in ("touches_db", "project.touches_db"):
            return self.flags.get("has_db")
        # flow-consistency-hardening: touches_* default = příslušná capability (fail-safe = NEprořezávat).
        # Chybí-li flag (např. lightweight vlna skipla architecture), spadne na has_server/has_ui →
        # backend/ui-system běží jako dnes; explicitní touches_*=false (od architecture) je prořeže.
        if name in ("touches_server", "project.touches_server"):
            return self.flags.get("has_server")
        if name in ("touches_shared_ui", "project.touches_shared_ui", "spec.touches_shared_ui"):
            return self.flags.get("has_ui")
        # design_source (feature-design politika, projekt-level): author|intake|derive.
        # Default = author (denisa kreslí mockup) → existující projekty bez flagu nepadnou;
        # solo projekty Watson nastaví na derive. NENÍ to per-feature gate (viz delivery.yaml).
        if name in ("design_source", "project.design_source"):
            return self.flags.get("design_source", "author")
        known = self.targets or self.targets_declared
        if name in ("has_web", "targets.web"):
            return ("web" in self.targets) if known else None
        if name in ("has_mobile", "targets.mobile"):
            return ("mobile" in self.targets) if known else None
        if name in ("has_desktop", "targets.desktop"):
            return ("desktop" in self.targets) if known else None
        return None

    def type_ver(self, T: str, type_versions: dict) -> int:
        return max((type_versions.get(x, 0) for x in expand_type(T, self.artifacts)), default=0)


# ── project config ────────────────────────────────────────────────────────────
def load_project_config(config_file: str | None) -> tuple[dict, set[str], bool,
                                                          dict[str, str], dict[str, str]]:
    """(flags, targets, targets_declared, agent_status, role_status) z project-config.md.
    role_status keyed by ROLE (node-id) z `active_roles`; agent_status keyed by short
    z `agents:` (zpětná kompat). Aktivace gatuje ROLI; agent je jen binding."""
    flags: dict = {}
    targets: set[str] = set()
    agent_status: dict[str, str] = {}
    role_status: dict[str, str] = {}
    targets_declared = False
    if config_file and os.path.isfile(config_file):
        txt = open(config_file, encoding="utf-8").read()
        for blk in re.findall(r"```yaml\s*\n(.*?)\n```", txt, re.S):
            try:
                data = yaml.safe_load(blk) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(data, dict):
                continue
            # active_roles: gatuje ROLE (node-id). Map {role: active/inactive} (unmarked=active,
            # parita se starým agents) nebo list aktivních (ostatní default active — jen pojmenování).
            ar = data.get("active_roles")
            if isinstance(ar, dict):
                for k, v in ar.items():
                    role_status[str(k)] = str(v).strip()
            elif isinstance(ar, list):
                for k in ar:
                    role_status[str(k)] = "active"
            if isinstance(data.get("agents"), dict):   # zpětná kompat (keyed by agent short)
                for k, v in data["agents"].items():
                    agent_status[k] = str(v).strip()
            fl = data.get("flags")
            if isinstance(fl, dict):
                for k, v in fl.items():
                    flags[k] = coerce_flag(v)
            at = data.get("active_targets")
            if at is not None:
                targets_declared = True
            if isinstance(at, dict):
                targets |= {k for k, v in at.items() if v}
                derive_target_flags(at, flags)
            elif isinstance(at, list):
                targets |= set(at)
    return flags, targets, targets_declared, agent_status, role_status


# (backend|db|deploy sub-klíč targetu) → project flag. JEDINÝ zdroj téhle derivace —
# volá load_project_config (z konfigu) i derive_roles (z Watson rozhodnutí), ať se nerozejdou.
_TARGET_FLAG = {"backend": "has_server", "db": "has_db", "deploy": "has_deploy"}


def derive_target_flags(targets_spec: dict, flags: dict) -> dict:
    """Odvoď project flagy (has_server/has_db/has_deploy) z target sub-klíčů (deterministicky,
    ať se neduplikují ručně — I4). Explicitní `flags:` je přebíjí (setdefault = explicit wins)."""
    for tspec in targets_spec.values():
        if isinstance(tspec, dict):
            for sub, flag in _TARGET_FLAG.items():
                if tspec.get(sub):
                    flags.setdefault(flag, True)
    return flags


def apply_overrides(flags: dict, targets: set[str], targets_declared: bool,
                    targets_str: str | None, flag_args: list[str] | None) -> bool:
    for tok in (targets_str or "").split(","):
        if tok.strip():
            targets.add(tok.strip())
            targets_declared = True
    for f in (flag_args or []):
        if "=" in f:
            k, v = f.split("=", 1)
            flags[k.strip()] = coerce_flag(v.strip())
    return targets_declared


def ctx_from_targets(graph: Graph, targets_spec: dict | None, flags: dict | None,
                     artifacts: dict | None = None) -> Ctx:
    """Postav Ctx přímo z (targets, flags) — tj. z Watson ROZHODNUTÍ, bez project-config souboru.
    Použije TYTÉŽ predikáty/derivace jako runtime (derive_target_flags + Ctx.flag), aby se aktivace
    role odvozená při setupu (derive_roles) nerozešla s tím, jak ji pak gatuje frontier/is_active.
    `targets_spec` = {target: bool | {backend,db,deploy}}; prázdný dict = deklarováno, žádný target."""
    targets_spec = {} if targets_spec is None else targets_spec
    flags = dict(flags or {})
    targets = {k for k, v in targets_spec.items() if v}
    derive_target_flags(targets_spec, flags)
    return Ctx(graph, artifacts, flags, targets, targets_declared=True,
               agent_status={}, cls=None, outcome=None, role_status={})


def build_ctx(graph_file: str, cls: str | None = None, outcome: str | None = None,
              flag_args: list[str] | None = None, targets_str: str | None = None) -> Ctx:
    graph = Graph.load(graph_file)
    artifacts = load_artifacts(graph_file)
    config_file = "project-config.md" if os.path.isfile("project-config.md") else None
    flags, targets, td, agent_status, role_status = load_project_config(config_file)
    td = apply_overrides(flags, targets, td, targets_str, flag_args)
    return Ctx(graph, artifacts, flags, targets, td, agent_status, cls,
               (outcome or "").upper() or None, role_status)


def load_interactions(graph_file: str) -> dict:
    ip = sibling(graph_file, "interactions.yaml")
    if os.path.isfile(ip):
        return (load_yaml(ip) or {}).get("interactions", {}) or {}
    return {}


# ── frontier (dataflow ready-rule + staleness) ────────────────────────────────
class Frontier:
    """Spočítá ready/judgment/waiting množinu (dataflow ready-rule + incremental-rebuild
    staleness) iterací nad Graph/RunState objekty — žádné ruční deps-dicty ani nested ify."""

    def __init__(self, graph: Graph, ctx: Ctx, state: RunState, interactions: dict | None) -> None:
        self.graph = graph
        self.ctx = ctx
        self.state = state
        self.interactions: dict = interactions or {}

    def _active(self, nid: str) -> str:
        n = self.graph.get(nid)
        return n.is_active(self.ctx) if n else "active"   # mimo-graf uzel = active (parita)

    def _live_deps(self) -> dict[str, list[Dep]]:
        """{cíl: [(src, edge.when)]} forward, strukturálně ne-falsifikované hrany."""
        deps: dict[str, list[Dep]] = {}
        for e in self.graph.forward_edges():
            if not e.when.structural_live(self.ctx):
                continue
            for t in e.to:
                deps.setdefault(t, []).append((e.frm, e.when))
        return deps

    def _active_deps(self, deps: dict[str, list[Dep]], nid: str) -> list[Dep]:
        return [(s, w) for (s, w) in deps.get(nid, [])
                if self._active(s) != "inactive" and s not in self.state.skipped]

    def _valid_completed(self, deps: dict[str, list[Dep]]) -> set[str]:
        """Staleness fixpoint: completed uzel je STALE, má-li vstupní typ novější verzi
        než jeho node-verze; bez verze → downward-closure fallback (E2).

        Re-flow transitivita (BUG 2): un-completnutí cíle re-flow tu díru NEřeší samo —
        proto re-flow zároveň INVALIDUJE výstupní typy cíle (RunState.uncomplete bumpne
        epoch a smaže `node_versions[target]` + zvedne `type_versions[output]`). Tím se
        downstream verifikační uzly (qa, code-lint), které z té implementace vychází přes
        type-graf, stanou stale přes EXISTUJÍCÍ verzový mechanismus a znovu proběhnou PŘED
        uzávěrem vlny — bez plného forward-closure re-flow (scoped re-flow E1 zůstává).

        VÝJIMKA (lehká dráha, FIX #2): uzel s pravdivým `skip_if` je vyřešen POLITIKOU,
        nezávisle na vstupech (jeho výstupy úmyslně nikdy nevzniknou; downstream ho bere
        jako PASS). Takový completed uzel se z principu NESMÍ stát stale — jinak ho
        staleness vyhodí z valid_completed, `_auto_skip` ho znovu nabídne a drive ho
        auto-skipuje donekonečna (cyklus). Skip-eligible completed uzly proto chráníme
        před invalidací (`skip_if == TRUE` = drží svou platnost sám o sobě)."""
        type_versions, node_versions = self.state.type_versions, self.state.node_versions
        skip_protected = {nid for nid in self.state.completed
                          if (n := self.graph.get(nid)) is not None
                          and n.skip_if.root is not None
                          and n.skip_if.classify(self.ctx) == "eligible"}
        valid = set(self.state.completed)
        changed = True
        while changed:
            changed = False
            for nid in list(valid):
                if nid in skip_protected:        # politikou vyřešený uzel není nikdy stale
                    continue
                nver = node_versions.get(nid)
                if nver is not None:
                    node = self.graph.get(nid)
                    in_types = node.inputs if node else []
                    stale = any(self.ctx.type_ver(T, type_versions) > nver for T in in_types)
                else:
                    srcs = [s for (s, _w) in self._active_deps(deps, nid)]
                    stale = bool(srcs) and not all(s in valid for s in srcs)
                if stale:
                    valid.discard(nid)
                    changed = True
        return valid

    def _ready_kind(self, nid: str, completed_set: set[str], deps: dict[str, list[Dep]]) -> str | None:
        """('ready'|'judgment'|'waiting'|None) — None = uzel se vůbec neúčastní (entry-less)."""
        active_deps = self._active_deps(deps, nid)
        if not active_deps:
            return "ready" if nid == self.graph.entry else None
        pend = False
        for (s, w) in active_deps:
            if s not in completed_set:
                return "waiting"
            c = w.classify(self.ctx, self.state.outcomes.get(s))
            if c == "judgment":
                pend = True
            elif c != "eligible":
                return "waiting"
        return "judgment" if pend else "ready"

    def _info(self, nid: str) -> dict:
        n = self.graph.nodes[nid]   # nid pochází z iterace grafu → uzel vždy existuje
        d = {"node": nid, "agent": n.agent or "-", "model": n.model or "-",
             "type": n.type, "interaction": n.interaction, "level": n.level,
             "inputs": ", ".join(n.inputs) or "-"}
        if n.type == "human-gate":
            d["blocking"] = n.blocking(self.interactions)
        return d

    def _auto_skip(self, completed_set: set[str], deps: dict[str, list[Dep]]) -> set[str]:
        """FIX #2 lehká dráha: uzly s `skip_if` predikátem == TRUE → auto-PASS. UNKNOWN/judgment
        (chybí flag) = NEskipuj (fail-safe: raději spustit než nesprávně přeskočit). Už completed/
        skipnuté uzly sem nepatří (řeší je completed_set/skipped).

        FIX A (2026-06-17, vlna project-create-wizard): auto-skip JEN když jsou vlastní vstupy
        uzlu už uspokojené (`_ready_kind == ready`). Skip_if je vyřešení POLITIKOU, ale uzel
        nesmí být prohlášen za hotového PRODUCENTA, dokud jeho vlastní upstream reálně neproběhl
        — jinak se jeho konzumenti (backend ← architecture, ui-system ← feasibility) stanou
        dataflow-ready DŘÍV, než product vůbec vytvořil spec (phantom-ready). Skip = „výstup
        uspokojen", ale jen v MÍSTĚ grafu, kam dataflow legitimně dorazil. (Loop-fix FIX #2 ve
        `_valid_completed/skip_protected` zůstává: jakmile je uzel jednou právoplatně skipnut,
        staleness ho už neinvaliduje. Tady řešíme opačný směr — KDY ho vůbec poprvé skipnout.)"""
        out: set[str] = set()
        for nid, n in self.graph.nodes.items():
            if n.skip_if.root is None:
                continue
            if n.skip_if.classify(self.ctx) != "eligible":   # FALSE/judgment → běž
                continue
            if self._ready_kind(nid, completed_set, deps) != "ready":   # vstupy ještě nedorazily
                continue
            out.add(nid)
        return out

    def _blocking_reason(self, src: str) -> str | None:
        """Vrátí důvod blokace produkujícího uzlu, nebo None (ještě běží / neznámý stav)."""
        if src in self.state.skipped:
            return "skipped"
        act = self._active(src)
        if act == "inactive":
            return "inactive"
        # bare FAIL: completed, ale outcome FAIL a bez returns_to → výstup nikdy nevznikne
        if src in self.state.completed:
            outcome = self.state.outcomes.get(src)
            if outcome == "FAIL":
                return "failed"
        return None

    def _stall_diagnostics(self, waiting: list[str], deps: dict[str, list[Dep]], completed_set: set[str]) -> list[dict]:
        """Pilíř B: pro každý waiting uzel najdi blocking zdroj.
        Volá se jen při ready==[] && judgment==[] && inflight==[].
        Vrátí seznam {blocked_node, blocking_node, reason}.
        Pracuje s celým deps (ne _active_deps) — jinak skipped/inactive producenti uniknou (AC-4).
        completed_set se přeskočí jen pro uzly s úspěšným outcome — bare FAIL v completed je
        stále blocking (výstup nikdy nevznikne)."""
        result = []
        for nid in waiting:
            for (src, _w) in deps.get(nid, []):
                if src in completed_set:
                    # Přeskočit jen pokud producent nepůsobí stall (PASS/ACK/APPROVED/DONE).
                    # Bare FAIL v completed = blokuje — reason='failed'.
                    outcome = self.state.outcomes.get(src)
                    if outcome != "FAIL":
                        continue
                reason = self._blocking_reason(src)
                if reason:
                    result.append({
                        "blocked_node": nid,
                        "blocking_node": src,
                        "reason": reason,
                    })
        return result

    def compute(self) -> dict:
        deps = self._live_deps()
        completed_set = self._valid_completed(deps)
        # SMÍŘENÍ inflight ↔ valid_completed (jediný zdroj pravdy): perzistovaný `frontier:`
        # je jen ECHO promocí do inflight (run.py add_inflight). Demotuje ho výhradně
        # `done <uzel>` → když uzel mezitím ZPLATNÍ (stane se valid_completed živým přepočtem,
        # např. po opravě grafu přestane být stale), echo nikdo neuklidí a přežije jako ghost:
        # bucket-loop ho slepě přeskakuje (ř. níže) a terminal_reached čeká na prázdný inflight
        # → ghost blokuje uzávěr vlny. Uzel, který je SOUČASNĚ v inflight A ve valid_completed,
        # je kontradikce (hotový ≠ rozdělaný) → reality (valid_completed) vyhrává a z LIVE
        # inflight ho vyřadíme. Odvozením (ne ad-hoc cleanupem perzistovaného pole) je reziduum
        # NEMOŽNÉ z konstrukce: ať ghost vznikne jakkoliv, každý recompute ho smíří. Perzistovaný
        # `state.frontier` (úložiště orchestrátora) neměníme — `done` ho dorovná přirozeně.
        inflight = set(self.state.inflight) - completed_set
        skipped = set(self.state.skipped)
        # Auto-skip (lehká dráha) uzly se chovají jako completed PASS pro dataflow ready-rule
        # (downstream je nečeká), ale surfují odděleně → drive je zapíše do completed+outcomes.
        auto_skip = {nid for nid in self._auto_skip(completed_set, deps)
                     if nid not in completed_set and nid not in inflight and nid not in skipped}
        completed_set = completed_set | auto_skip

        buckets: dict[str, list[str]] = {"ready": [], "judgment": [], "waiting": []}
        # Uzly aktivní, ale bez přiřazení do bucketu (producenti jsou inactive/skipped →
        # _active_deps je vyfiltruje → _ready_kind vrátí None → uzel se ztratí z pohledu).
        # Sbíráme je pro stall diagnostiku (AC-3, AC-4).
        limbo: list[str] = []
        for nid in self.graph:
            if nid in completed_set or nid in inflight or nid in skipped:
                continue
            if self._active(nid) == "inactive":
                continue
            kind = self._ready_kind(nid, completed_set, deps)
            if kind:
                buckets[kind].append(nid)
            elif deps.get(nid):
                # Uzel má live deps, ale žádnou active dep → producenti jsou inactive/skipped
                limbo.append(nid)

        stall_diagnostics: list[dict] = []
        # AC-5 guard: diagnostika jen při skutečném stallu (ne při normálním souběhu)
        if not buckets["ready"] and not buckets["judgment"] and not inflight:
            # waiting (čeká na live deps) + limbo (producenti inactive/skipped) = oba stall kandidáti
            stall_candidates = buckets["waiting"] + limbo
            stall_diagnostics = self._stall_diagnostics(stall_candidates, deps, completed_set)

        terminal_reached = any((n := self.graph.get(x)) is not None and n.type == "terminal"
                               for x in completed_set)
        return {"ready": [self._info(x) for x in buckets["ready"]],
                "judgment": [self._info(x) for x in buckets["judgment"]],
                "waiting": [self._info(x) for x in buckets["waiting"]],
                "auto_skip": sorted(auto_skip),
                "inflight": sorted(inflight),
                "terminal_reached": terminal_reached,
                "stall_diagnostics": stall_diagnostics}

    def next_candidates(self, frm: str) -> dict:
        node = self.graph.get(frm)
        if node is not None and node.type == "terminal":
            return {"from": frm, "terminal": True, "candidates": []}
        cands = []
        for e in self.graph.edges_from(frm):
            verdict = e.when.classify(self.ctx)
            if verdict == "skip":
                continue
            for t in e.to:
                act = self._active(t)
                if act == "inactive":
                    continue
                n = self.graph.get(t)
                cands.append({
                    "node": t, "agent": (n.agent if n else None) or "-",
                    "model": (n.model if n else None) or "-",
                    "kind": e.kind, "edge": verdict, "act": act,
                    "type": n.type if n else "agent",
                    "interaction": n.interaction if n else None,
                    "level": n.level if n else None,
                    "inputs": (", ".join(n.inputs) if n else "") or "-",
                    "cond": e.raw.get("when", "-"),
                })
        return {"from": frm, "outcome": self.ctx.outcome, "class": self.ctx.cls,
                "terminal": False, "candidates": cands}


def compute_frontier(ctx: Ctx, st: "dict | RunState", interactions: dict) -> dict:
    """Frontier dict ze stavu (st = raw dict nebo RunState)."""
    state = st if isinstance(st, RunState) else RunState(st)
    return Frontier(ctx.graph, ctx, state, interactions).compute()


def compute_next(ctx: Ctx, frm: str) -> dict:
    return Frontier(ctx.graph, ctx, RunState({}), {}).next_candidates(frm)


def merge_state_into_ctx(ctx: Ctx, st: dict, args: "argparse.Namespace") -> None:
    """Vlij per-feature flagy + class z run-stavu do ctx (frontier emit). Authoritu má
    run-state nad project-configem; explicitní CLI --flag/--class přebíjí oboje (operator
    override). Bez tohohle je has_ui/touches_db UNKNOWN a flag-gated-off uzly leaknou."""
    for k, v in (st.get("flags") or {}).items():
        ctx.flags[k] = coerce_flag(v)
    if not args.cls and st.get("class"):
        ctx.cls = str(st["class"]).strip()
    for f in (args.flag or []):                 # explicitní CLI override vyhrává
        if "=" in f:
            k, v = f.split("=", 1)
            ctx.flags[k.strip()] = coerce_flag(v.strip())


# ── importovatelná zkratka pro run.py (drive) ─────────────────────────────────
def frontier_for_state(st: dict, graph_file: str | None = None) -> dict:
    """Frontier dict přímo ze stavu — st flagy/class jako overrides (run.py drive
    to volá místo subprocess na next.sh)."""
    graph_file = graph_file or common.require_graph()
    flag_args = []
    for k, v in (st.get("flags") or {}).items():
        if isinstance(v, bool):
            sv = "true" if v else "false"
        else:
            sv = str(v)
        flag_args.append(f"{k}={sv}")
    ctx = build_ctx(graph_file, cls=st.get("class"), flag_args=flag_args)
    return compute_frontier(ctx, st, load_interactions(graph_file))


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--from", dest="frm", default="")
    ap.add_argument("--outcome", default="")
    ap.add_argument("--class", dest="cls", default="")
    ap.add_argument("--run", default=common.run_file_path())
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--targets", default="")
    ap.add_argument("--emit", default="text")  # text | json | frontier
    args = ap.parse_args(argv)

    graph_file = common.require_graph()
    ctx = build_ctx(graph_file, cls=(args.cls or None), outcome=args.outcome,
                    flag_args=args.flag, targets_str=args.targets)

    if args.emit == "frontier":
        st = state_only(args.run)
        # Frontier MUSÍ vidět per-feature flagy z run-stavu (has_ui/touches_db/…) — jinak
        # je flag-predikát uzlu UNKNOWN (judgment) místo skip a flag-gated-off UI/DB uzly
        # leaknou do ready/waiting. Drive cesta (frontier_for_state) je merguje; CLI emit
        # je teď taky merguje. Pořadí: project-config < run-state < explicitní --flag/--class.
        merge_state_into_ctx(ctx, st, args)
        out = compute_frontier(ctx, st, load_interactions(graph_file))
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0 if (out["ready"] or out["judgment"]) else 1)

    # single-node režim
    frm = args.frm or None
    if not frm:
        frm = (state_only(args.run) or {}).get("active_node")
    if not frm:
        print("CHYBA: chybí --from a current-run.md neudává active_node.", file=sys.stderr)
        sys.exit(2)
    if frm not in ctx.graph:
        print(f"CHYBA: uzel '{frm}' není v grafu.", file=sys.stderr)
        sys.exit(2)

    res = compute_next(ctx, frm)
    if args.emit == "json":
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(0 if (res.get("terminal") or res.get("candidates")) else 1)

    if res.get("terminal"):
        print(f"from: {frm} (terminal — běh u konce)")
        sys.exit(1)
    cands = res["candidates"]
    print(f"from: {frm}   outcome: {ctx.outcome or '-'}   class: {ctx.cls or '-'}")
    if not cands:
        print("next: (žádná odchozí hrana neplatí pro tento outcome)")
        sys.exit(1)
    print("next:")
    for c in cands:
        note = c["edge"] + (", activation:unknown" if c["act"] == "unknown" else "")
        print(f"  - {c['node']:16} → agent:{c['agent']:18} model:{c['model']:7} "
              f"kind:{c['kind']:8} [{note}]")
        print(f"      when: {c['cond']}")
        print(f"      inputs: {c['inputs']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
