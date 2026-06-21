#!/usr/bin/env python3
"""predicate.py — `when` podmínky jako parsovaný strom typovaných atomů (keystone OO modelu).

Nahrazuje trojí regex+`eval()` duplikaci (dřívější frontier.py atom/classify/flag_live)
JEDNÍM vyhodnocením nad AST. Parse NIKDY nefailuje (validace ≠ parse): neznámý/volný token
se stane FreeTextAtom (deliberate judgment kategorie), strukturálně rozbitý výraz Malformed
uzlem (judgment — jako dřívější eval-výjimka). Slovníková validace = `problems()`:
C14 nálezy padají zadarmo z už parsovaného stromu.

Sémantika vyhodnocení (parita se starým enginem — NENÍ Kleene):
  Verdict = TRUE | FALSE | UNKNOWN (chybějící flag/outcome) | JUDGMENT (free-text/neznámé)
  kombinace: jakýkoli JUDGMENT → JUDGMENT; jinak jakýkoli UNKNOWN → UNKNOWN; jinak bool
  classify mapuje: TRUE→eligible, FALSE→skip, UNKNOWN/JUDGMENT→judgment
  FAIL-prefix: free atom začínající „FAIL" je na ne-FAIL outcome FALSE (skip), ne judgment
  structural_live: falsifikují jen strukturální flag/target atomy (None→True, ostatní True)
"""
import os
import re
import sys
from enum import Enum
from typing import TYPE_CHECKING, Iterator, Protocol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import EDGE_OUTCOMES

if TYPE_CHECKING:
    from vocab import Vocabulary


class EvalContext(Protocol):
    """Strukturální kontrakt, který `Predicate`/atomy potřebují k vyhodnocení (duck-type;
    naplňuje ho frontier.Ctx i testovací FakeCtx — predikát NEimportuje konkrétní Ctx).
    `flag()` vrací True | False | None (unknown) | hodnotu (enum string)."""

    flags: dict[str, object]
    cls: str | None
    outcome: str | None

    def flag(self, name: str) -> object: ...


class _Unset:
    """Typ sentinelu „outcome nepředán" (≠ None, který znamená explicitně žádný outcome)."""


UNSET = _Unset()

# Strukturální flag/target atomy = JEDINÉ, co engine vyhodnocuje deterministicky bare.
# Pozor: NE celý vocabulary.flags — bare `design_source` je free-text (judgment),
# deterministická je jen jeho `==` forma. has_signature je zvláštní atom (default False).
PROJ_RE = re.compile(
    r"^(project\.|spec\.)?"
    r"(has_server|has_db|has_ui|has_deploy|touches_db|touches_server|touches_shared_ui)$")
# flags.<x> — explicitní run-state bool flag (např. flags.lightweight, FIX #2 lehká dráha).
# Deterministický strukturální atom: vyhodnotí se přes ctx.flag(<x>) jako bool (chybí → UNKNOWN
# → fail-safe NEskipuj). Validace proti vocabulary.flags řeší problems() (C14).
FLAGS_RE = re.compile(r"^flags\.(\w+)$")
TARGET_RE = re.compile(r"^project\.targets\.(\w+)$")
KNOWN_TARGETS = ("web", "mobile", "desktop")
CMP_RE = re.compile(r"^([\w.]+)\s*(==|!=)\s*([\w.]+)$")    # runtime tvar (deterministický)
CMP_LOOSE_RE = re.compile(r"^([\w.]+)\s*==\s*([\w-]+)$")   # C14 tvar (hodnota i s pomlčkou)
BARE_RE = re.compile(r"^(?:project\.|spec\.)?(\w+)$")


class Verdict(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"      # chybějící informace (flag/outcome) — může dorazit
    JUDGMENT = "judgment"    # mimo deterministický slovník — chce úsudek


def _bool_verdict(b: bool) -> Verdict:
    return Verdict.TRUE if b else Verdict.FALSE


def _flag_verdict(v: object) -> Verdict:
    """Hodnota flagu → Verdict. Ne-bool hodnota (enum string) v bool kontextu = judgment."""
    if v is None:
        return Verdict.UNKNOWN
    if isinstance(v, bool):
        return _bool_verdict(v)
    return Verdict.JUDGMENT


def _free_verdict(text: str, oc: str | None) -> Verdict:
    """Free-text verdikt: „FAIL…" fráze platí jen pro FAIL outcome (jinak skip)."""
    if text.upper().startswith("FAIL") and oc and oc != "FAIL":
        return Verdict.FALSE
    return Verdict.JUDGMENT


# ── atomy ─────────────────────────────────────────────────────────────────────
class Atom:
    is_free: bool = False   # free-like atom (mimo deterministický slovník)

    def __init__(self, raw: str) -> None:
        self.raw = raw

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        raise NotImplementedError

    def structural(self, ctx: EvalContext) -> bool:
        """Strukturální (flag-only) hodnota; ne-strukturální atomy nefalsifikují (True)."""
        return True

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        """C14 nálezy atomu proti slovníku (prázdný seznam = OK)."""
        return []

    def walk(self) -> Iterator["Atom"]:
        yield self

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.raw!r})"


class OutcomeAtom(Atom):
    """PASS / FAIL / APPROVED / REJECTED / ACK / PENDING."""

    def __init__(self, raw: str) -> None:
        super().__init__(raw)
        self.value = raw.strip().upper()

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        return _bool_verdict(oc == self.value) if oc else Verdict.UNKNOWN


class StructuralFlagAtom(Atom):
    """(project.|spec.)?has_* / touches_db — deterministický projektový flag."""

    def __init__(self, base: str, raw: str) -> None:
        super().__init__(raw)
        self.base = base

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        return _flag_verdict(ctx.flag(self.base))

    def structural(self, ctx: EvalContext) -> bool:
        v = ctx.flag(self.base)
        return True if v is None else bool(v)

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if not vocab.is_known_flag(self.base):
            return [f"C14 {where}: neznámý flag/atom '{self.raw}' (∉ vocabulary.flags)"]
        return []


class TargetAtom(Atom):
    """project.targets.<x> — známý target je strukturální, neznámý = free (judgment)."""

    def __init__(self, name: str, raw: str) -> None:
        super().__init__(raw)
        self.name = name
        self.is_free = name not in KNOWN_TARGETS   # neznámý target → free (judgment)

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        if self.is_free:
            return _free_verdict(self.raw, oc)
        return _flag_verdict(ctx.flag("targets." + self.name))

    def structural(self, ctx: EvalContext) -> bool:
        if self.is_free:
            return True
        v = ctx.flag("targets." + self.name)
        return True if v is None else bool(v)

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if vocab.targets and self.name not in vocab.targets:
            return [f"C14 {where}: neznámý target '{self.name}' (∉ {sorted(vocab.targets)})"]
        return []


class SignatureAtom(Atom):
    """has_signature — jediný flag s defaultem False (bugfix bez signature → eligible)."""

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        return _bool_verdict(bool(ctx.flags.get("has_signature", False)))

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if not vocab.is_known_flag("has_signature"):
            return [f"C14 {where}: neznámý flag/atom '{self.raw}' (∉ vocabulary.flags)"]
        return []


class ClassAtom(Atom):
    """class == <x> — intake klasifikace (router outcome, ne projektový flag)."""

    def __init__(self, value: str, raw: str) -> None:
        super().__init__(raw)
        self.value = value

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        return _bool_verdict(ctx.cls == self.value) if ctx.cls else Verdict.UNKNOWN

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if CMP_LOOSE_RE.match(self.raw) and vocab.classes and self.value not in vocab.classes:
            return [f"C14 {where}: neznámá class '{self.value}' (∉ {sorted(vocab.classes)})"]
        return []


class ComparisonAtom(Atom):
    """<flag> == <hodnota> (value-flag rovnost, např. design_source == author).
    runtime_known=False = tvar mimo runtime slovník (hodnota s pomlčkou) → judgment;
    C14 ho přesto validuje (CMP_LOOSE_RE)."""

    def __init__(self, lhs: str, op: str, value: str, raw: str, runtime_known: bool = True) -> None:
        super().__init__(raw)
        self.lhs, self.op, self.value = lhs, op, value
        self.runtime_known = runtime_known
        self.is_free = not runtime_known   # mimo runtime slovník (hodnota s pomlčkou) → judgment

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        if not self.runtime_known:
            return _free_verdict(self.raw, oc)
        v = ctx.flag(self.lhs)
        if v is None:
            return Verdict.UNKNOWN
        eq = (str(v) == self.value)
        return _bool_verdict(eq if self.op == "==" else not eq)

    def structural(self, ctx: EvalContext) -> bool:
        if not self.runtime_known:
            return True
        if self.lhs.startswith("class"):
            return True   # class== není strukturální flag → live (řeší classify/outcome)
        v = ctx.flag(self.lhs)
        if v is None:
            return True
        eq = (str(v) == self.value)
        return eq if self.op == "==" else (not eq)

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if not CMP_LOOSE_RE.match(self.raw):   # C14 bere jen `==` s [\w-]+ hodnotou
            return []
        base = self.lhs.split(".")[-1]
        if base == "class":
            if vocab.classes and self.value not in vocab.classes:
                return [f"C14 {where}: neznámá class '{self.value}' (∉ {sorted(vocab.classes)})"]
        elif base == "fault":
            if vocab.faults and self.value not in vocab.faults:
                return [f"C14 {where}: neznámý fault '{self.value}' (∉ {sorted(vocab.faults)})"]
        elif vocab.is_known_flag(base):
            if vocab.flag_kind(base) == "enum" and self.value not in vocab.enum_values(base):
                return [f"C14 {where}: '{base} == {self.value}' — neznámá hodnota "
                        f"(∉ {vocab.enum_values(base)})"]
        else:
            return [f"C14 {where}: neznámý flag '{base}' v '{self.raw}'"]
        return []


class FaultAtom(ComparisonAtom):
    """fault == <doména> — diagnostická return hrana; Graph podle ní routuje FAIL+fault."""


class FreeTextAtom(Atom):
    """Víceslovná fráze = ZÁMĚRNÁ judgment kategorie (lidský prompt v hraně);
    bare neznámé slovo = judgment + C14 nález (typo flagu)."""
    is_free = True

    def __init__(self, raw: str) -> None:
        super().__init__(raw)
        m = BARE_RE.match(raw)
        self.bare_word: str | None = m.group(1) if m else None

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        return _free_verdict(self.raw, oc)

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        if self.bare_word and not vocab.is_known_flag(self.bare_word):
            return [f"C14 {where}: neznámý flag/atom '{self.raw}' (∉ vocabulary.flags)"]
        return []


# ── kompozity ─────────────────────────────────────────────────────────────────
class Expr(Protocol):
    """Vyhodnotitelný uzel stromu — atom NEBO kompozit (And/Or/Not/Malformed). Sjednocuje
    rozhraní, které `Predicate` od kořene a kompozity od dětí potřebují."""

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict: ...

    def structural(self, ctx: EvalContext) -> bool: ...

    def walk(self) -> Iterator["Atom"]: ...


def _absorb(vs: list[Verdict]) -> Verdict | None:
    """Kombinace verdiktů: JUDGMENT > UNKNOWN > bool (parita: any-FREE→judgment,
    pak any-None→judgment, pak eval). Vrací None, když jsou všechny bool."""
    if Verdict.JUDGMENT in vs:
        return Verdict.JUDGMENT
    if Verdict.UNKNOWN in vs:
        return Verdict.UNKNOWN
    return None


class And:
    def __init__(self, children: list[Expr]) -> None:
        self.children = children

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        vs = [c.evaluate(ctx, oc) for c in self.children]
        return _absorb(vs) or _bool_verdict(all(v is Verdict.TRUE for v in vs))

    def structural(self, ctx: EvalContext) -> bool:
        return all(c.structural(ctx) for c in self.children)

    def walk(self) -> Iterator["Atom"]:
        for c in self.children:
            yield from c.walk()


class Or:
    def __init__(self, children: list[Expr]) -> None:
        self.children = children

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        vs = [c.evaluate(ctx, oc) for c in self.children]
        return _absorb(vs) or _bool_verdict(any(v is Verdict.TRUE for v in vs))

    def structural(self, ctx: EvalContext) -> bool:
        return any(c.structural(ctx) for c in self.children)

    def walk(self) -> Iterator["Atom"]:
        for c in self.children:
            yield from c.walk()


class Not:
    def __init__(self, child: Expr) -> None:
        self.child = child

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        v = self.child.evaluate(ctx, oc)
        if v in (Verdict.JUDGMENT, Verdict.UNKNOWN):
            return v
        return _bool_verdict(v is Verdict.FALSE)

    def structural(self, ctx: EvalContext) -> bool:
        return not self.child.structural(ctx)

    def walk(self) -> Iterator["Atom"]:
        yield from self.child.walk()


class Malformed:
    """Strukturálně rozbitý výraz (nevyparsovatelný). Parita s eval-výjimkou:
    free atomy → free verdikt nad CELÝM stringem; jinak UNKNOWN/JUDGMENT."""

    def __init__(self, atoms: list[Atom], raw: str) -> None:
        self.atoms, self.raw = atoms, raw

    def evaluate(self, ctx: EvalContext, oc: str | None) -> Verdict:
        if any(a.is_free for a in self.atoms):
            return _free_verdict(self.raw, oc)
        vs = [a.evaluate(ctx, oc) for a in self.atoms]
        if Verdict.UNKNOWN in vs:
            return Verdict.UNKNOWN
        return Verdict.JUDGMENT   # legacy: eval() na rozbitém výrazu → výjimka → judgment

    def structural(self, ctx: EvalContext) -> bool:
        return True               # legacy: eval výjimka → live

    def walk(self) -> Iterator["Atom"]:
        yield from self.atoms


# ── parser ────────────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"(\(|\)|&&|\|\||(?<![=!])!)")
_OPS = {"(", ")", "&&", "||", "!"}


def make_atom(t: str) -> Atom:
    """Klasifikace atomu PODLE TVARU (žádný slovník — ten řeší problems())."""
    if t.upper() in EDGE_OUTCOMES:
        return OutcomeAtom(t)
    m = PROJ_RE.match(t)
    if m:
        return StructuralFlagAtom(m.group(2), t)
    m = FLAGS_RE.match(t)
    if m:
        return StructuralFlagAtom(m.group(1), t)
    m = TARGET_RE.match(t)
    if m:
        return TargetAtom(m.group(1), t)
    if t.startswith("class =="):
        return ClassAtom(t.split("==", 1)[1].strip(), t)
    if t == "has_signature":
        return SignatureAtom(t)
    m = CMP_RE.match(t)
    if m:
        klass = FaultAtom if m.group(1) == "fault" else ComparisonAtom
        return klass(m.group(1), m.group(2), m.group(3), t, runtime_known=True)
    m = CMP_LOOSE_RE.match(t)
    if m:
        klass = FaultAtom if m.group(1) == "fault" else ComparisonAtom
        return klass(m.group(1), "==", m.group(2), t, runtime_known=False)
    return FreeTextAtom(t)


class _ParseError(Exception):
    pass


class _Parser:
    """Recursive descent: Or := And ('||' And)* ; And := Unary ('&&' Unary)* ;
    Unary := '!' Unary | '(' Or ')' | Atom. Precedence ! > && > || (= dřívější eval)."""

    def __init__(self, toks: list[str]) -> None:
        self.toks, self.i = toks, 0

    def _peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def parse(self) -> Expr:
        node = self._or()
        if self.i != len(self.toks):
            raise _ParseError(f"nečekaný token: {self._peek()!r}")
        return node

    def _or(self) -> Expr:
        kids: list[Expr] = [self._and()]
        while self._peek() == "||":
            self.i += 1
            kids.append(self._and())
        return kids[0] if len(kids) == 1 else Or(kids)

    def _and(self) -> Expr:
        kids: list[Expr] = [self._unary()]
        while self._peek() == "&&":
            self.i += 1
            kids.append(self._unary())
        return kids[0] if len(kids) == 1 else And(kids)

    def _unary(self) -> Expr:
        t = self._peek()
        if t == "!":
            self.i += 1
            return Not(self._unary())
        if t == "(":
            self.i += 1
            node = self._or()
            if self._peek() != ")":
                raise _ParseError("chybí ')'")
            self.i += 1
            return node
        if t is None or t in _OPS:
            raise _ParseError(f"čekán atom, je: {t!r}")
        self.i += 1
        return make_atom(t)


# ── Predicate (veřejné API) ───────────────────────────────────────────────────
class Predicate:
    """Parsovaná `when` podmínka. `Predicate.of(s)` je memoizované (predikáty jsou čisté)."""

    _cache: dict[str, "Predicate"] = {}

    def __init__(self, raw: str, root: Expr | None) -> None:
        self.raw = raw
        self.root = root   # None = prázdný predikát (vždy eligible/live)

    @classmethod
    def of(cls, when: object) -> "Predicate":
        key = "" if when is None else str(when).strip()
        p = cls._cache.get(key)
        if p is None:
            p = cls._cache[key] = cls.parse(when)
        return p

    @classmethod
    def parse(cls, when: object) -> "Predicate":
        s = "" if when is None else str(when).strip()
        if not s:
            return cls(s, None)
        toks = [c.strip() for c in _TOKEN_RE.split(s) if c.strip()]
        try:
            root: Expr = _Parser(toks).parse()
        except _ParseError:
            root = Malformed([make_atom(t) for t in toks if t not in _OPS], s)
        return cls(s, root)

    def evaluate(self, ctx: EvalContext, oc: "str | None | _Unset" = UNSET) -> Verdict:
        outcome = ctx.outcome if isinstance(oc, _Unset) else oc
        if self.root is None:
            return Verdict.TRUE
        return self.root.evaluate(ctx, outcome)

    def classify(self, ctx: EvalContext, oc: "str | None | _Unset" = UNSET) -> str:
        """'eligible' | 'skip' | 'judgment' — mapování Verdiktu na hranovou klasifikaci."""
        v = self.evaluate(ctx, oc)
        if v is Verdict.TRUE:
            return "eligible"
        if v is Verdict.FALSE:
            return "skip"
        return "judgment"

    def structural_live(self, ctx: EvalContext) -> bool:
        """Predikát NENÍ flag-falsifikovaný (strukturální flag/target část ≠ False)."""
        if self.root is None:
            return True
        return bool(self.root.structural(ctx))

    def atoms(self) -> Iterator[Atom]:
        if self.root is None:
            return
        yield from self.root.walk()

    def has_fault(self, fault: str) -> bool:
        """Obsahuje atom `fault == <fault>`? (Graph routuje diagnostikovaný fault na return cíl.)"""
        return any(isinstance(a, FaultAtom) and a.value == fault for a in self.atoms())

    def problems(self, vocab: "Vocabulary", where: str) -> list[str]:
        """C14 nálezy celého predikátu (flag-shaped atomy ∉ slovník; free-text fráze OK)."""
        return [p for a in self.atoms() for p in a.problems(vocab, where)]

    def __repr__(self) -> str:
        return f"Predicate({self.raw!r})"
