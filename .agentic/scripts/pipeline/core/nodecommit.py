#!/usr/bin/env python3
"""nodecommit.py — engine-native commit-on-done (per-node granularita).

Z backlog/agent-command-guardrails.md §3b + §4 vrstva 1: `git commit` vlastní VÝHRADNĚ
engine-proces, ne agent-shell. Po každém `done` uzlu engine sám stageuje a commitne stav
vlny → git historie drží per-node stopu a agent commit vůbec nepotřebuje (denylist mu ho
může zakázat bez výjimky).

Tohle je NOVÁ engine schopnost (dřív commit dělal ručně orchestrátor po done) — viz §2.

DESIGN (zdokumentováno v §rozhodnutí níže):
- **Staging — BASELINE-EXCLUSION (ne `git add -A`):** Repo má běžně trvalé netrackované
  runtime artefakty (runs/fixture-*, .tmp/, .agentic/audit/ …) + cizí rozdělané změny, které
  s vlnou NESOUVISÍ. `git add -A` by je všechny zametl do node-commitu (incident
  remove-db-layer). Proto si `run.sh start` zachytí množinu cest dirty/untracked PŘED vlnou
  (`commit_baseline` ve stavu) a `commit_node` stageuje JEN cesty, které se změnily a NEJSOU
  v baseline = změny vzniklé během vlny. Pre-existing stav se NIKDY nezamete — judgment-free,
  robustní pro libovolný stav repa.
- **Message:** `chore(wave:<run>): <node-id> <outcome>` — odvozeno z done envelope (node+run
  jsou v něm vždy). Tělo nese strojová fakta (outcome, agent, returns_to).
- **Edge cases:**
  - FAIL s returns_to → COMMITNE (re-flow mění tree, ten stav patří do historie).
  - terminal `done` → COMMITNE (uzavření vlny). light-path AUTO-SKIP → engine ho commitne v
    drive (commit_node se zavolá i pro auto-skip PASS). Prázdný diff (žádná wave-změna) →
    no-op commit se přeskočí (žádný --allow-empty), aby historie nebobtnala.
  - Mazání: wave smaže tracked soubor → stageuje se deletion (`git add -A <cesta>` zahrne
    i odstranění), pokud cesta není v baseline.
  - Soubor dirty UŽ v baseline, který agent během vlny dál změní → ZŮSTÁVÁ vyloučen (jeho
    změny „nepatří vlně"). Přijatelný a obhajitelný trade-off: baseline = „co bylo rozdělané
    před vlnou, to vlna nevlastní". Kdo si to chce commitnout, commitne ručně mimo engine.
- **Baseline degradace (repair):** repair rekonstruuje stav z ledgeru, který baseline
  NENESE → po repairu je commit_baseline prázdný (= „nic vyloučeno"). To je OK (repair je
  recovery, ne start nové vlny); commit_node pak stageuje jen reálně změněné cesty od HEAD.

FAIL-SOFT (vzor git_head v run.py): mimo git / git chybí / commit selže → WARN + return
False, NIKDY nevyhodí ven. Engine `done` se nesmí shodit kvůli gitu (telemetrie/commit jsou
doplněk, ne výrobní invariant).

OPT-IN (od 2026-06-20 incidentu): commit-on-done je DEFAULT VYPNUTO; zapne ho jen
AGENTIC_NODE_COMMIT=1, který `run.sh` nastaví VÝHRADNĚ pro `done`/`drive` (orchestrátorova CLI
vlna). Serverové `/api/done` ani testy flag nezapínají → necommitují. Důvod: tyhle done volání
nejdou přes `run.sh start`, takže nemají baseline → `git add -A` by zametlo celý working tree.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

# Env zapínač — OPT-IN. Commit-on-done smí vystřelit JEN z orchestrátorovy CLI vlny
# (`run.sh done`/`drive`, který flag explicitně zapne). Default OFF chrání před tím, aby
# commit vystřelil ze serverového /api/done nebo z testů (in-process import nemá flag → no-op).
_ENV_FLAG = "AGENTIC_NODE_COMMIT"


def commit_enabled() -> bool:
    """Default VYPNUTO (opt-in). True POUZE když je AGENTIC_NODE_COMMIT explicitně truthy
    (1/true/yes/on); unset/prázdné/cokoli jiného = False.

    INCIDENT (2026-06-20): default ON vystřelil commit 8× ze serverových/testovacích done volání,
    která NEjdou přes `run.sh start` (chybí baseline → `git add -A` zametlo celý working tree).
    Commit-on-done je teď opt-in scoped na orchestrátorovu CLI vlnu — `run.sh` flag zapne jen pro
    `done`/`drive`; server `/api/done` a testy ho nezapínají, takže necommitují."""
    v = str(os.environ.get(_ENV_FLAG, "")).strip().lower()
    return v in ("1", "true", "yes", "on")


def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess | None:
    """Spusť git v `cwd`. Selhání spuštění (mimo git / chybí binárka) → None (fail-soft)."""
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None


def _in_git_repo(cwd: str) -> bool:
    r = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    return bool(r and r.returncode == 0 and r.stdout.strip() == "true")


def is_tree_dirty(cwd: str | None = None) -> bool | None:
    """Má working tree necommitnuté změny? True/False; None = mimo git / chyba (nevíme).

    Dnes už jen ADVISORY signál pro `run.sh start` (commit-on-done nestageuje `git add -A`,
    nýbrž baseline-exclusion — viz `capture_baseline`/`commit_node`), takže špinavý tree start
    NEodmítá; jen na něj upozorní."""
    root = cwd or common.run_root()
    if not _in_git_repo(root):
        return None
    r = _git(["status", "--porcelain"], root)
    if r is None or r.returncode != 0:
        return None
    return bool(r.stdout.strip())


def _porcelain_paths(cwd: str) -> set[str] | None:
    """Množina cest, které git status --porcelain hlásí jako změněné/netrackované.

    Parsuje porcelain v1 (`XY <path>`, případně `XY <old> -> <new>` u rename) → set cest
    relativních ke git rootu. None = mimo git / git selhal (volající degraduje fail-soft).
    Renamy bereme PŮVODNÍ i NOVOU cestu (obě jsou „dotčené"). Robustní vůči mezerám: status
    kódy jsou první 2 znaky, cesta začíná na pozici 3."""
    if not _in_git_repo(cwd):
        return None
    r = _git(["status", "--porcelain"], cwd)
    if r is None or r.returncode != 0:
        return None
    paths: set[str] = set()
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line.strip()
        if " -> " in path:   # rename/copy: "old -> new" — obě cesty jsou dotčené
            old, _, new = path.partition(" -> ")
            paths.add(_unquote(old.strip()))
            paths.add(_unquote(new.strip()))
        else:
            paths.add(_unquote(path.strip()))
    return paths


def _unquote(p: str) -> str:
    """Git status quotuje cesty s ne-ASCII / mezerami do uvozovek (core.quotepath).
    Odstraň vnější uvozovky (jednoduchá normalizace; baseline porovnání je set-membership)."""
    if len(p) >= 2 and p.startswith('"') and p.endswith('"'):
        return p[1:-1]
    return p


def capture_baseline(cwd: str | None = None) -> list[str] | None:
    """Zachyť při `run.sh start` množinu cest, které jsou dirty/untracked PŘED vlnou.

    = „commit baseline exclusion set". commit_node tyhle cesty NIKDY nestageuje (nepatří
    vlně). Vrací SEŘAZENÝ list (deterministická serializace do stavu) nebo None mimo git
    (start to uloží jako None → commit_node degraduje na „nic vyloučeno")."""
    root = cwd or common.run_root()
    paths = _porcelain_paths(root)
    if paths is None:
        return None
    return sorted(paths)


def _build_message(env: dict) -> str:
    """Commit message z done envelope. node+run vždy přítomné (po validate_envelope).
    Konvenční subject + strojové tělo (outcome/agent/returns_to) — bez lidské prózy."""
    run = env.get("run") or "?"
    node = env.get("node") or "?"
    outcome = (env.get("outcome") or "?")
    subject = f"chore(wave:{run}): {node} {outcome}"
    body_lines = [f"node: {node}", f"outcome: {outcome}", f"run: {run}"]
    if env.get("agent"):
        body_lines.append(f"agent: {env['agent']}")
    if env.get("returns_to"):
        body_lines.append(f"returns_to: {env['returns_to']}")
    body_lines.append("")
    body_lines.append("engine commit-on-done (per-node).")
    return subject + "\n\n" + "\n".join(body_lines)


def commit_node(env: dict, cwd: str | None = None,
                baseline: list[str] | None = None) -> bool:
    """Stage (baseline-exclusion) + commit stavu po `done` uzlu. Fail-soft, idempotentní vůči
    prázdnému diffu (no-op když není co commitnout). Vrací True když commit vznikl.

    Stageuje JEN cesty změněné během vlny = aktuálně dirty/untracked MÍNUS `baseline`
    (pre-existing dirty/untracked zachycený při `start`). `git add -A <cesta>` per cesta
    zahrne i mazání (deletion). Pre-existing haraburdí se NIKDY nezamete.

    env = done envelope (node/run/outcome/…). cwd = git root (default run_root).
    baseline = exclusion set z capture_baseline (None → nic vyloučeno; např. po repair)."""
    if not commit_enabled():
        return False
    root = cwd or common.run_root()
    if not _in_git_repo(root):
        print("commit-on-done: mimo git repo — přeskočeno (fail-soft).", file=sys.stderr)
        return False

    current = _porcelain_paths(root)
    if current is None:
        print("commit-on-done: WARN — `git status` selhal; done pokračuje.", file=sys.stderr)
        return False

    excluded = set(baseline or [])
    wave_paths = sorted(current - excluded)
    if not wave_paths:
        print("commit-on-done: žádná wave-změna ke commitnutí (no-op; "
              f"{len(excluded)} cest vyloučeno baselinou).", file=sys.stderr)
        return False

    # `git add -A -- <cesty>`: stageuje add/modify I deletion pro vyjmenované cesty (jen ty,
    # co patří vlně). Pre-existing dirty/untracked v baseline zůstane nestageováno.
    add = _git(["add", "-A", "--", *wave_paths], root)
    if add is None or add.returncode != 0:
        print(f"commit-on-done: WARN — `git add` wave-cest selhal "
              f"({add.stderr.strip() if add else 'spuštění selhalo'}); done pokračuje.",
              file=sys.stderr)
        return False

    # Pojistka: po staging-restrikci může být index prázdný (vše bylo v baseline) → no-op.
    diff = _git(["diff", "--cached", "--quiet"], root)
    if diff is not None and diff.returncode == 0:
        print("commit-on-done: žádná wave-změna ke commitnutí (no-op).", file=sys.stderr)
        return False

    msg = _build_message(env)
    com = _git(["commit", "-m", msg], root)
    if com is None or com.returncode != 0:
        print(f"commit-on-done: WARN — `git commit` selhal "
              f"({com.stderr.strip() if com else 'spuštění selhalo'}); done pokračuje.",
              file=sys.stderr)
        return False

    node = env.get("node")
    print(f"commit-on-done: zacommitováno node={node} ({env.get('outcome')}); "
          f"{len(wave_paths)} wave-cest, {len(excluded)} vyloučeno baselinou.")
    return True
