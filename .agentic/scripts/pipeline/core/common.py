#!/usr/bin/env python3
"""common.py — sdílené jádro pipeline runneru.

Vytaženo z dřívějších bash-heredoců (next/result/check/state/ledger/run), aby se
neopakoval graf/artifacts loading, čtení+atomický zápis current-run stavového bloku,
`coerce_flag`, outcome vokabuláře a `expand_type`. Dřív byly tyhle kusy duplikované
napříč soubory s ručními „drž v sync" poznámkami — teď jeden zdroj pravdy.

Moduly se importují jako sourozenci (běží přes `python3 core/<modul>.py`, takže
`sys.path[0]` = adresář core/). Budoucí app vrstva (VISION §Most) importuje totéž.
"""
import os
import re
import sys
from typing import Any, NoReturn

try:
    import yaml
except ImportError:
    print("CHYBA: chybí PyYAML (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

# ── outcome vokabuláře ────────────────────────────────────────────────────────
# Validační vokabulář (result.sh /done): work PASS/FAIL, human-gate ACK/APPROVED/
# REJECTED, routing PENDING, terminál/blok DONE/BLOCKER.
RESULT_OUTCOMES = {"PASS", "FAIL", "APPROVED", "REJECTED", "ACK", "PENDING", "DONE", "BLOCKER"}
# Atom-rozpoznatelné outcomes v hraně `when` (DONE/BLOCKER nejsou edge atomy).
EDGE_OUTCOMES = RESULT_OUTCOMES - {"DONE", "BLOCKER"}

STATE_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.S)


def die(msg: str, code: int = 2) -> NoReturn:
    print(msg, file=sys.stderr)
    sys.exit(code)


# ── graf + artifacts ──────────────────────────────────────────────────────────
def find_graph(explicit: str | None = None) -> str | None:
    """Cesta ke grafu: explicit > PIPELINE_GRAPH > .agentic/pipeline > pipeline. None = nenalezen."""
    if explicit:
        return explicit
    env = os.environ.get("PIPELINE_GRAPH")
    if env:
        return env
    for p in (".agentic/pipeline/delivery.yaml", "pipeline/delivery.yaml"):
        if os.path.isfile(p):
            return p
    return None


def require_graph(explicit: str | None = None) -> str:
    g = find_graph(explicit)
    if not g:
        die("CHYBA: nenalezen pipeline/delivery.yaml (nastav PIPELINE_GRAPH).")
    return g


def load_yaml(path: str) -> Any:
    return yaml.safe_load(open(path, encoding="utf-8"))


def load_graph(path: str) -> dict:
    return load_yaml(path) or {}


def sibling(graph_file: str, name: str) -> str:
    """Soubor vedle grafu (artifacts.yaml / interactions.yaml / …)."""
    return os.path.join(os.path.dirname(graph_file), name)


def find_agentic(rel: str) -> str | None:
    """Soubor/adresář: .agentic/<rel> (v projektu) > <rel> (framework). None = nenalezen.
    Sdílené resolvery (scaffold/feature/compose/apply-feature/lib)."""
    for base in (os.path.join(".agentic", rel), rel):
        if os.path.exists(base):
            return base
    return None


def load_artifacts(graph_file: str) -> dict | None:
    """Artifact registr vedle grafu; None = chybí (SKIP typové kontroly)."""
    p = sibling(graph_file, "artifacts.yaml")
    if not os.path.isfile(p):
        return None
    return (load_yaml(p) or {}).get("artifacts", {}) or {}


def load_vocabulary(graph_file: str) -> dict | None:
    """Slovníkový registr vedle grafu (vocabulary.yaml); None = chybí (SKIP slovníkové kontroly).
    Fail-closed validace flagů/typů/enumů (check.sh + result.sh)."""
    p = sibling(graph_file, "vocabulary.yaml")
    if not os.path.isfile(p):
        return None
    return load_yaml(p) or {}


def expand_type(T: str, artifacts: dict | None) -> list[str]:
    """Abstraktní typ → [T] + subtypes; konkrétní → [T]. Staleness/C9 bere max přes členy."""
    spec = (artifacts or {}).get(T) or {}
    if spec.get("abstract"):
        return [T] + list(spec.get("subtypes") or [])
    return [T]


# ── flagy ─────────────────────────────────────────────────────────────────────
def coerce_flag(v: object) -> bool | str:
    """bool-ish → bool (has_ui/has_db…); jinak hodnota verbatim (design_source: author|intake)."""
    if isinstance(v, bool):
        return v
    low = str(v).strip().lower()
    if low in ("1", "true", "yes", "on"):
        return True
    if low in ("0", "false", "no", "off"):
        return False
    return str(v).strip()


# ── kanonický kořen běhového stavu (cwd-nezávislý) ────────────────────────────
def run_root() -> str:
    """Kořen běhového stavu (current-run.md + runs/). Ukotven na UMÍSTĚNÍ SKRIPTU
    (kořen projektu = rodič .agentic), NE na cwd → run.sh dá identický stav, ať se
    spustí z kořene projektu nebo z .agentic. `AGENTIC_RUN_ROOT` env přebíjí (izolace
    selftestu v mktemp; obdoba PIPELINE_GRAPH pro graf). Bez tohohle ukotvení by se
    current-run.md rozešel mezi dvěma místy podle cwd (viz IMPLEMENTATION.md §stav)."""
    env = os.environ.get("AGENTIC_RUN_ROOT")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))              # .agentic/scripts/pipeline/core
    agentic = os.path.dirname(os.path.dirname(os.path.dirname(here)))  # .agentic
    return os.path.dirname(agentic)                                # kořen projektu


def run_file_path() -> str:
    """Kanonická cesta k current-run.md (kořen projektu, cwd-nezávislá)."""
    return os.path.join(run_root(), "current-run.md")


def runs_dir(run: str) -> str:
    """Adresář běhu runs/<run> pod kořenem projektu (cwd-nezávislý)."""
    return os.path.join(run_root(), "runs", str(run))


# ── current-run.md stavový blok ───────────────────────────────────────────────
def read_state(run_file: str) -> tuple[dict, str | None, "re.Match | None"]:
    """Vrať (st, txt, match) z current-run.md.
    Chybí soubor → ({}, None, None). Chybí blok → ({}, txt, None)."""
    if not os.path.isfile(run_file):
        return {}, None, None
    txt = open(run_file, encoding="utf-8").read()
    m = STATE_BLOCK_RE.search(txt)
    if not m:
        return {}, txt, None
    return (yaml.safe_load(m.group(1)) or {}), txt, m


def state_only(run_file: str) -> dict:
    """Jen stavový dict (pohodlí pro read-only čtenáře)."""
    return read_state(run_file)[0]


def dump_block(st: dict) -> str:
    return "```yaml\n" + yaml.safe_dump(st, sort_keys=False, allow_unicode=True) + "```"


def write_state(run_file: str, st: dict,
                header: str = "# current-run.md — strojový stav běhu pipeline\n\n") -> None:
    """Atomicky zapiš stav do current-run.md, zachová okolní text. Re-readuje soubor
    čerstvě (najde aktuální blok) → bezpečné i po předchozí mutaci ve stejném běhu."""
    block = dump_block(st)
    txt = open(run_file, encoding="utf-8").read() if os.path.isfile(run_file) else None
    m = STATE_BLOCK_RE.search(txt) if txt else None
    if txt is not None and m is not None:
        new = txt[:m.start()] + block + txt[m.end():]    # nahraď existující blok in-place
    else:
        new = header + block + "\n"                       # nový soubor / chybějící blok
    tmp = run_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    os.replace(tmp, run_file)
