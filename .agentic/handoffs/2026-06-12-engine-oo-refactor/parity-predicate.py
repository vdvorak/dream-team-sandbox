#!/usr/bin/env python3
"""parity-predicate.py — diferenciální oracle: nový Predicate AST == stará if/regex/eval logika.

Pojistka OO refaktoru (Fáze 1): zmrazená VERBATIM kopie původních frontier.Ctx.atom/
classify/flag_live (před refaktorem) slouží jako referenční implementace. Test projede
všechna `when` z reálného delivery.yaml + syntetický korpus (typo flagy, !=, nested,
FAIL-prefixy) přes kartézský součin (outcome × class × flag-kontext) a tvrdí, že
`Predicate.classify == _ref_classify` a `Predicate.structural_live == _ref_flag_live`.

Protože reference je zmrazená (nezávislá na živém frontier.py), test běží i po smazání
starých metod → trvalý regression guard sémantiky predikátů. Spuštění:
    python3 handoffs/2026-06-12-engine-oo-refactor/parity-predicate.py   # exit 0 = parita drží
"""
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("DT_REPO") or os.path.abspath(os.path.join(HERE, "..", ".."))
CORE = os.path.join(REPO, "scripts", "pipeline", "core")
sys.path.insert(0, CORE)

import yaml  # noqa: E402
from common import EDGE_OUTCOMES  # noqa: E402
from predicate import Predicate  # noqa: E402

# ── zmrazená reference (VERBATIM z frontier.py PŘED refaktorem) ─────────────────
_PROJ = re.compile(r"^(project\.|spec\.)?(has_server|has_db|has_ui|has_deploy|touches_db)$")
_TGT = re.compile(r"^project\.targets\.(web|mobile|desktop)$")
_UNSET = object()


class RefCtx:
    """Kopie relevantní části původního frontier.Ctx (flag-resolution + atom/classify/flag_live).
    Zároveň slouží jako EvalContext pro nový Predicate (duck-type: .flag/.flags/.cls/.outcome)."""

    def __init__(self, flags, targets, targets_declared, cls, outcome):
        self.flags, self.targets, self.targets_declared = flags, targets, targets_declared
        self.cls = cls
        self.outcome = (outcome or "").upper() or None

    def flag(self, name):
        if name in self.flags:
            return self.flags[name]
        if name in ("touches_db", "project.touches_db"):
            return self.flags.get("has_db")
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

    def atom(self, tok, oc=_UNSET):
        oc = self.outcome if oc is _UNSET else oc
        t = tok.strip()
        if not t:
            return None
        if t.upper() in EDGE_OUTCOMES:
            return (oc == t.upper()) if oc else None
        m = _PROJ.match(t)
        if m:
            return self.flag(m.group(2))
        m = _TGT.match(t)
        if m:
            return self.flag("targets." + m.group(1))
        if t.startswith("class =="):
            want = t.split("==", 1)[1].strip()
            return (self.cls == want) if self.cls else None
        if t in ("has_signature",):
            return self.flags.get(t, False)
        m = re.match(r"^([\w.]+)\s*(==|!=)\s*([\w.]+)$", t)
        if m:
            lhs, op, want = m.group(1), m.group(2), m.group(3)
            val = self.flag(lhs)
            if val is None:
                return None
            eq = (str(val) == want)
            return eq if op == "==" else (not eq)
        return "FREE"

    def classify(self, when, oc=_UNSET):
        oc = self.outcome if oc is _UNSET else oc
        if when is None or str(when).strip() == "":
            return "eligible"
        s = str(when).strip()
        parts = [p for p in re.split(r"\(|\)|\&\&|\|\||(?<![=!])!", s) if p.strip()]
        vals = [self.atom(p, oc) for p in parts]
        if any(v == "FREE" for v in vals):
            if s.upper().startswith("FAIL") and oc and oc != "FAIL":
                return "skip"
            return "judgment"
        if any(v is None for v in vals):
            return "judgment"
        expr = s
        expr = re.sub(r"\&\&", " and ", expr)
        expr = re.sub(r"\|\|", " or ", expr)
        for p in sorted(parts, key=len, reverse=True):
            expr = expr.replace(p, str(self.atom(p, oc)))
        expr = re.sub(r"(?<![=!])!", " not ", expr)
        try:
            return "eligible" if eval(expr, {"__builtins__": {}}, {}) else "skip"
        except Exception:
            return "judgment"

    def flag_live(self, when):
        if when is None or str(when).strip() == "":
            return True
        s = str(when).strip()
        parts = [p for p in re.split(r"\(|\)|\&\&|\|\||(?<![=!])!", s) if p.strip()]

        def fv(tok):
            t = tok.strip()
            mm2 = _PROJ.match(t)
            if mm2:
                v = self.flag(mm2.group(2))
                return True if v is None else v
            mm2 = _TGT.match(t)
            if mm2:
                v = self.flag("targets." + mm2.group(1))
                return True if v is None else v
            mm3 = re.match(r"^([\w.]+)\s*(==|!=)\s*([\w.]+)$", t)
            if mm3:
                lhs, op, want = mm3.group(1), mm3.group(2), mm3.group(3)
                if lhs.startswith("class"):
                    return True
                v = self.flag(lhs)
                if v is None:
                    return True
                eq = (str(v) == want)
                return eq if op == "==" else (not eq)
            return True

        expr = s
        expr = re.sub(r"\&\&", " and ", expr)
        expr = re.sub(r"\|\|", " or ", expr)
        for p in sorted(parts, key=len, reverse=True):
            expr = expr.replace(p, str(fv(p)))
        expr = re.sub(r"(?<![=!])!", " not ", expr)
        try:
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return True


# ── korpus ──────────────────────────────────────────────────────────────────
def graph_whens():
    g = yaml.safe_load(open(os.path.join(REPO, "pipeline", "delivery.yaml"), encoding="utf-8"))
    whens = set()
    for n in (g.get("nodes") or {}).values():
        if n.get("when"):
            whens.add(str(n["when"]))
    for e in (g.get("edges") or []):
        if e.get("when"):
            whens.add(str(e["when"]))
    return whens


SYNTH = [
    None, "", "PASS", "FAIL", "APPROVED", "REJECTED", "ACK", "PENDING",
    "project.has_db && touches_db",
    "project.has_server && !(project.has_db && touches_db)",
    "spec.has_ui && design_source == author",
    "spec.has_ui && (design_source == author || design_source == intake)",
    "spec.has_ui && design_source == intake",
    "spec.has_ui && design_source == derive",
    "class == feature || class == improvement || (class == bugfix && !has_signature)",
    "fault == db-schema", "fault == server-logic", "fault == contract", "fault == spec",
    "project.targets.web", "project.targets.mobile", "project.targets.desktop",
    "!project.has_deploy", "project.has_deploy",
    "has_signature", "!has_signature",
    "design_source == intake", "design_source != author", "design_source != derive",
    # nested / kombinace deterministických atomů
    "(PASS || FAIL) && project.has_ui",
    "!(project.has_db) && project.has_server",
    "project.has_ui && project.has_db && project.has_deploy",
    "project.targets.web || project.targets.mobile || project.targets.desktop",
    # free-text (samostatné — reálný tvar judgment hran)
    "mockup needs missing component", "FAIL: build/deploy/migration", "FAIL → rollback",
    # typo / neznámé flagy (FREE → judgment)
    "has_dbb", "touchesdb", "projet.has_db", "spec.has_xyz",
    "foo != bar", "unknown == value",
    # malformed
    "&&", "PASS &&", "( PASS", "PASS ||", ")(",
]


def flag_contexts():
    ALL = {"has_server", "has_db", "has_ui", "has_deploy"}
    out = []
    # prázdné, nedeklarované cíle
    out.append((dict(), set(), False))
    # vše true + všechny cíle deklarované
    out.append(({k: True for k in ALL} | {"has_signature": True, "touches_db": True},
                {"web", "mobile", "desktop"}, True))
    # vše false, cíle deklarované prázdné
    out.append(({k: False for k in ALL} | {"has_signature": False, "touches_db": False},
                set(), True))
    # design_source varianty + jen web
    for ds in ("author", "intake", "derive"):
        out.append(({"has_ui": True, "has_server": True, "has_db": True, "design_source": ds},
                    {"web"}, True))
    # has_db true ale touches_db false (B2)
    out.append(({"has_db": True, "has_server": True, "touches_db": False}, set(), True))
    return out


def main():
    whens = sorted(graph_whens() | {w for w in SYNTH if w is not None}) + [None]
    classes = [None, "feature", "bugfix", "improvement"]
    outcomes = [None, "PASS", "FAIL", "APPROVED", "REJECTED", "ACK", "PENDING"]

    checked = mism = 0
    for flags, targets, declared in flag_contexts():
        for cls, oc, when in itertools.product(classes, outcomes, whens):
            ctx = RefCtx(dict(flags), set(targets), declared, cls, oc)
            pred = Predicate.of(when)
            ref_c, new_c = ctx.classify(when, oc), pred.classify(ctx, oc)
            ref_l, new_l = ctx.flag_live(when), pred.structural_live(ctx)
            checked += 2
            if ref_c != new_c:
                mism += 1
                print(f"  ✗ classify  when={when!r} oc={oc} cls={cls} flags={flags} "
                      f"targets={sorted(targets)}/{declared}: ref={ref_c} new={new_c}")
            if ref_l != new_l:
                mism += 1
                print(f"  ✗ flag_live when={when!r} flags={flags} "
                      f"targets={sorted(targets)}/{declared}: ref={ref_l} new={new_l}")

    print(f"parity-predicate: {checked} porovnání, {mism} neshod "
          f"({len(whens)} when × {len(classes)} class × {len(outcomes)} outcome × "
          f"{len(flag_contexts())} flag-kontext)")
    if mism:
        print("PARITY SELHALA")
        sys.exit(1)
    print("PARITY OK — Predicate AST == stará atom/classify/flag_live logika")


if __name__ == "__main__":
    main()
