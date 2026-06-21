#!/usr/bin/env python3
"""result.py — zpracuje node-result obálku („/done" v souboru) (z result.sh).

Když uzel dokončí práci, zavolá se s jeho envelope (templates/node-result.md):
  1) ověří (povinná pole; uzel ∈ graf; outputs.type ∈ artifacts; outcome ∈ vokabulář)
  2) F3 auto-derive z grafu (outputs typy / agent / phase) — orchestrátor je nemapuje ručně
  3) připíše envelope do runs/<run>/ledger.yaml (append-only multi-doc)
  4) posune current-run.md (frontier model + incremental-rebuild verze)

CLI:   python3 result.py <envelope.yaml> [--run-file current-run.md] [--check-only]
Závislost: python3 + PyYAML. Exit: 0 = OK | 1 = nevalidní envelope | 2 = chyba.
"""
import argparse
import os
import sys
from datetime import datetime
from typing import Callable, NoReturn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import RESULT_OUTCOMES, load_artifacts, require_graph, write_state, yaml
from graph import Graph, Node
from runstate import RunState
from vocab import Vocabulary


def fail(msg: str) -> NoReturn:
    print(f"NEVALIDNÍ envelope: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_iso(s: object) -> datetime:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        fail(f"nevalidní ISO čas: {s}")


# ── outcome handlery (polymorfně místo if/elif řetězu) ─────────────────────────
# Každý handler: matches(outcome, severity, returns_to) -> vybere se PRVNÍ, který sedí
# (pořadí = dnešní pořadí větví: advisory → returns_to → bare FAIL → REJECTED → else);
# apply(state, node, env, signature, stamp) provede stavové mutace a vrátí ctr_note string.
# Texty (ctr_note, status, note) MUSÍ zůstat bajt-identické — selftest je grepuje.
Stamp = Callable[[str], None]   # orazítkuj uzel verzemi (incremental rebuild)


class OutcomeHandler:
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        raise NotImplementedError

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        raise NotImplementedError


class AdvisoryFail(OutcomeHandler):
    """FAIL advisory — zaznamenej nález, ale BEZ re-flow (uzel zůstane completed)."""
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        return outcome == "FAIL" and severity == "advisory"

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        state.mark_completed(node)
        state.set_outcome(node, "FAIL")
        stamp(node)
        state.add_finding(node, "advisory", env.get("returns_to"), signature)
        state.status = "in_progress"
        return " (advisory finding — bez re-flow)"


class ReturnFail(OutcomeHandler):
    """FAIL blocking s returns_to — un-completne cíl, bumpne counter, nese payload."""
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        return outcome == "FAIL" and bool(returns_to)

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        target = env["returns_to"]
        # Re-flow transitivita (BUG 2): cíl se přepracuje → invaliduj jeho výstupní typy verzí,
        # ať downstream konzumenti (vč. verifikačních qa/code-lint) zestárnou a znovu proběhnou.
        state.uncomplete(target, env.get("_returns_to_outputs"))
        key, count = state.bump_counter(node, target)
        if count >= 3:
            state.status = "blocked"
            state.note = f"BLOCKER: {key} dosáhl {count}× — eskaluj o roli výš (constitution)"
        else:
            state.status = "in_progress"
        if signature:
            state.add_payload(target, signature)
        state.add_finding(node, "blocking", target, signature)
        return f", return {key}={count} (un-complete cíl {target}; downstream lazily přes staleness)"


class BareFail(OutcomeHandler):
    """FAIL bez returns_to — žádné re-flow, jen výzva dodat cíl."""
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        return outcome == "FAIL"

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        state.set_outcome(node, "FAIL")
        state.status = "in_progress"
        return " (FAIL bez returns_to — dodej returns_to pro re-flow)"


class Rejected(OutcomeHandler):
    """REJECTED — tvrdý halt běhu (constitution §8)."""
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        return outcome == "REJECTED"

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        state.set_outcome(node, "REJECTED")
        state.status = "blocked"
        state.note = f"{node} REJECTED — běh zastaven (constitution §8)"
        return " (REJECTED → halt)"


class Completion(OutcomeHandler):
    """Úspěch (PASS/APPROVED/ACK/DONE) nebo BLOCKER — completne, orazítkuje, smaže payload."""
    def matches(self, outcome: str, severity: str, returns_to: object) -> bool:
        return True  # fallback (dnešní else větev)

    def apply(self, state: RunState, node: str, env: dict, signature: str, stamp: Stamp) -> str:
        outcome = env["outcome"]   # klíč je po validate_envelope vždy přítomný a validní
        state.mark_completed(node)
        state.set_outcome(node, outcome)
        stamp(node)
        state.clear_payload(node)
        if outcome == "BLOCKER":
            state.status = "blocked"
            state.note = env.get("note") or state.note or f"{node} BLOCKER — eskaluj o roli výš"
        else:
            state.status = "in_progress"
        return ""


# Pořadí výběru = dnešní pořadí if/elif větví; první matches vyhraje.
OUTCOME_HANDLERS = [AdvisoryFail(), ReturnFail(), BareFail(), Rejected(), Completion()]


# ── validace envelope ──────────────────────────────────────────────────────────
def load_envelope(env_path: str) -> dict:
    try:
        return yaml.safe_load(open(env_path, encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fail(f"nevalidní YAML: {e}")


def validate_envelope(env: dict, graph: Graph, vocab: Vocabulary) -> tuple[str, str, str, Node]:
    """Povinná pole + uzel v grafu + outcome/severity/fault/model ∈ vokabulář (fail-closed).
    Vrací (run, node, outcome, node_def) — node je zaručeně v grafu."""
    run = env.get("run")
    node = env.get("node")
    outcome = env.get("outcome")
    if not run:
        fail("chybí 'run'")
    if not node:
        fail("chybí 'node'")
    if node not in graph:
        fail(f"uzel '{node}' není v grafu")
    if outcome not in RESULT_OUTCOMES:
        fail(f"outcome '{outcome}' není z {sorted(RESULT_OUTCOMES)}")
    _validate_vocab_fields(env, graph, vocab)
    _validate_architecture_touches(env, node, outcome)
    return run, node, outcome, graph.nodes[node]


def _validate_vocab_fields(env: dict, graph: Graph, vocab: Vocabulary) -> None:
    """Fail-closed slovníky: neznámá severity / fault / model = nevalidní envelope (ne tichý
    fallback). Chybí-li registr → fallbacky severities/model_tiers (graceful)."""
    v_sev = vocab.severities
    v_models = vocab.model_tiers
    v_faults = vocab.faults  # prázdné = SKIP fault check
    sev = env.get("severity")
    if sev is not None and str(sev).strip().lower() not in v_sev:
        fail(f"severity '{sev}' není z {v_sev}")
    flt = env.get("fault")
    if flt and v_faults and str(flt).strip() not in v_faults:
        fail(f"fault '{flt}' není z {v_faults}")
    # model-override validace (Tony triage → per-node model, B3)
    for k, v in (env.get("models") or {}).items():
        if str(v).strip().lower() not in v_models:
            fail(f"model-override '{k}: {v}' není z {v_models}")
        if k not in graph:
            fail(f"model-override pro neznámý uzel '{k}'")


# Feature-level prořezávací flagy, které architecture (PASS) MUSÍ deklarovat (bool).
# touches_db (B2) + rodina touches_* (flow-consistency-hardening 2026-06-17): každý gatuje
# jednu produkující vrstvu (db-schema / backend / ui-system). Explicitní deklarace u architecture
# je zdroj pravdy o prořezu; chybějící architecture (lightweight) NEpadá sem — řeší frontier default.
_ARCH_TOUCHES = ("touches_db", "touches_server", "touches_shared_ui")


def _validate_architecture_touches(env: dict, node: str, outcome: str) -> None:
    """Pilíř A: architecture node s outcome PASS musí deklarovat každý touches_* flag (bool).
    Vynechání = validační chyba (AC-1). Platí i pro lightweight=true větev (skip_if se
    nevyhodnotí zde, ale envelope při auto-PASS neprojde přes validate_envelope, takže
    auto-skipnutá architecture sem nedorazí — flagy pak řeší frontier default = capability)."""
    if node != "architecture":
        return
    if outcome not in ("PASS", "APPROVED", "ACK", "DONE"):
        return   # FAIL / REJECTED nemusí deklarovat — nepostoupí do navazujících uzlů
    flags = env.get("flags") or {}
    for fl in _ARCH_TOUCHES:
        if fl not in flags:
            fail(
                f"uzel 'architecture' s outcome PASS musí deklarovat 'flags.{fl}' (true/false); "
                f"chybí — přidej 'flags: {{{fl}: true}}' nebo 'flags: {{{fl}: false}}' do envelope"
            )
        if not isinstance(flags[fl], bool):
            fail(
                f"flags.{fl} musí být bool (true/false), dostáno: {flags[fl]!r}"
            )


def derive_outputs(env: dict, node_def: Node, outcome: str) -> None:
    """F3 auto-derive: graf = zdroj pravdy o output typech / agentovi / fázi → orchestrátor je
    NEmapuje ručně. Explicitní outputs (s path) přebijí auto-derive → B1 path-check drží.
    Auto-derive jen u dokončení (success)."""
    if not env.get("outputs") and outcome in ("PASS", "APPROVED", "ACK", "DONE"):
        derived = [{"type": t} for t in node_def.outputs]
        if derived:
            env["outputs"] = derived
    env.setdefault("agent", node_def.agent)
    env.setdefault("phase", node_def.phase)


def validate_outputs(env: dict, artifacts: dict) -> None:
    """Každý output má 'type' ∈ artifacts; deklarovaný `path` musí na disku existovat (B1
    path-existence proti phantom PASS)."""
    for o in (env.get("outputs") or []):
        t = o.get("type") if isinstance(o, dict) else None
        if not t:
            fail(f"output bez 'type': {o}")
        spec = artifacts.get(t) if artifacts else None
        if artifacts and spec is None:
            fail(f"output type '{t}' není v artifacts.yaml")
        path = o.get("path") if isinstance(o, dict) else None
        if path and spec and not (spec.get("external") or spec.get("abstract")):
            if not os.path.exists(path):
                fail(f"output '{t}' deklaruje path '{path}', ale na disku neexistuje (phantom PASS)")


def fill_time(env: dict) -> dict:
    """time je VOLITELNÉ (minimal envelope, F3): start+end → seconds; jinak 0 (honest „neměřeno")."""
    t = env.get("time") or {}
    started, ended = t.get("started"), t.get("ended")
    if t.get("seconds") is None:
        if started and ended:
            t["seconds"] = int((parse_iso(ended) - parse_iso(started)).total_seconds())
        else:
            t["seconds"] = 0
    env["time"] = t
    return t


# ── ledger + posun stavu ───────────────────────────────────────────────────────
def append_ledger(run: str, env: dict) -> None:
    ledger_dir = common.runs_dir(run)
    os.makedirs(ledger_dir, exist_ok=True)
    ledger = os.path.join(ledger_dir, "ledger.yaml")
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("---\n")
        yaml.safe_dump(env, fh, sort_keys=False, allow_unicode=True)
    print(f"ledger: připsáno → {ledger}")


def changed_types(env: dict, node_def: Node) -> list:
    """Typy, které completion uzlu orazítkuje novou verzí (incremental rebuild). Default
    (bez `changed`) = všechny outputy uzlu (plný re-flow lazily); `none` = žádné."""
    chg = env.get("changed")
    if chg is None:
        return list(node_def.outputs)
    if isinstance(chg, str):
        return [] if chg.strip().lower() in ("none", "") else [chg.strip()]
    if isinstance(chg, list):
        return [str(c).strip() for c in chg if str(c).strip()]
    return []


def resolve_returns(env: dict, graph: Graph, node: str, outcome: str, st: dict) -> None:
    """FAIL bez returns_to → engine doplní cíl: Ted fault (fault==<dom> hrana), jinak
    single-return auto-resolve (právě 1 return cíl)."""
    fault = str(env.get("fault") or "").strip()
    if outcome == "FAIL" and fault and not env.get("returns_to"):
        target = graph.return_target_for_fault(node, fault)
        if target:
            env["returns_to"] = target
            st["fault"] = fault
    if outcome == "FAIL" and not env.get("returns_to"):
        target = graph.single_return_target(node)
        if target:
            env["returns_to"] = target


def advance_state(run_file: str, run: str, node: str, outcome: str,
                  env: dict, graph: Graph, node_def: Node) -> None:
    """Posun current-run.md: ensure klíče, merge flagy/modely, resolve return cíle a
    aplikuj outcome handler (frontier model + incremental-rebuild verze)."""
    state, txt, m = RunState.read(run_file)
    if txt is None:  # soubor neexistuje → default stav
        state = RunState(RunState.fresh_result(run))
    elif m is None:
        fail(f"{run_file} nemá ```yaml stavový blok")
    state.ensure_result_keys()
    st = state.st

    state.remove_inflight(node)
    state.remove_awaiting(node)
    state.clear_halt_if(node)

    st["last_outcome"] = outcome
    st["active_node"] = node
    st["run"] = st.get("run") or run
    if env.get("class"):
        st["class"] = env["class"]

    if isinstance(env.get("flags"), dict):
        state.merge_flags(env["flags"])
    if isinstance(env.get("models"), dict):
        state.merge_models(env["models"])

    severity = str(env.get("severity") or "blocking").strip().lower()
    if severity not in ("blocking", "advisory"):
        severity = "blocking"
    signature = str(env.get("signature") or env.get("note") or "").strip()

    resolve_returns(env, graph, node, outcome, st)

    returns_to = env.get("returns_to")
    if returns_to and returns_to in graph.nodes:   # re-flow cíl → jeho výstupní typy (BUG 2 invalidace)
        env["_returns_to_outputs"] = list(graph.nodes[returns_to].outputs)
    handler = next(h for h in OUTCOME_HANDLERS if h.matches(outcome, severity, returns_to))
    ctr_note = handler.apply(state, node, env, signature,
                             lambda nid: state.stamp(nid, changed_types(env, node_def)))

    write_state(run_file, st)
    print(f"current-run.md: node={node} outcome={outcome}, completed={len(st['completed'])}, "
          f"status={st['status']}{ctr_note}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("envelope")
    ap.add_argument("--run-file", default=common.run_file_path())
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args(argv)

    env_path = args.envelope
    if not os.path.isfile(env_path):
        print(f"CHYBA: chybí envelope soubor: {env_path}", file=sys.stderr)
        sys.exit(2)

    graph_f = require_graph()
    graph = Graph.load(graph_f)
    artifacts = load_artifacts(graph_f) or {}
    vocab = Vocabulary.load(graph_f)

    env = load_envelope(env_path)
    run, node, outcome, node_def = validate_envelope(env, graph, vocab)
    derive_outputs(env, node_def, outcome)
    validate_outputs(env, artifacts)
    t = fill_time(env)

    print(f"envelope OK: run={run} node={node} outcome={outcome} "
          f"outputs={len(env.get('outputs') or [])} seconds={t['seconds']}")
    if args.check_only:
        sys.exit(0)

    append_ledger(run, env)
    advance_state(args.run_file, run, node, outcome, env, graph, node_def)

    # commit-on-done (engine-native, §3b/§4-R1): engine sám stageuje + commitne stav vlny
    # po dokončení uzlu. Fail-soft (mimo git / chyba → WARN, done pokračuje). current-run.md
    # už je zapsaný advance_state výš → je součástí node-commitu (stav i výroba v jednom commitu).
    # Baseline-exclusion: stageuje JEN wave-změny (pre-existing dirty/untracked z `start` se
    # vynechá). commit_baseline čteme z čerstvě zapsaného stavu.
    import nodecommit
    baseline = (common.state_only(args.run_file) or {}).get("commit_baseline")
    nodecommit.commit_node(env, baseline=baseline)


if __name__ == "__main__":
    main()
