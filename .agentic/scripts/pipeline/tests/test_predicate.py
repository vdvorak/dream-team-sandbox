"""Unit testy predicate.py — `when` AST: klasifikace atomů, vyhodnocení (NENÍ Kleene),
FAIL-prefix, structural_live, parser precedence, memoizace, C14 problems().

Tyto invarianty drží i parity-predicate.py (diferenciál vůči staré atom/classify/flag_live
logice), ale tady jsou pojmenované a izolované — když některý padne, řekne PROČ."""
import pytest

from predicate import (And, ClassAtom, ComparisonAtom, FaultAtom, FreeTextAtom, Malformed,
                       Not, Or, OutcomeAtom, Predicate, SignatureAtom, StructuralFlagAtom,
                       TargetAtom, Verdict, make_atom)
from vocab import Vocabulary


# ── klasifikace atomů (make_atom dle tvaru) ────────────────────────────────────
def test_make_atom_outcome():
    assert isinstance(make_atom("PASS"), OutcomeAtom)
    assert make_atom("FAIL").value == "FAIL"


def test_make_atom_structural_flag():
    for raw, base in (("has_db", "has_db"), ("spec.has_ui", "has_ui"), ("touches_db", "touches_db")):
        a = make_atom(raw)
        assert isinstance(a, StructuralFlagAtom) and a.base == base


def test_make_atom_target():
    a = make_atom("project.targets.web")
    assert isinstance(a, TargetAtom) and a.name == "web" and a.is_free is False
    assert make_atom("project.targets.tv").is_free is True   # neznámý target → free


def test_make_atom_class_and_signature():
    assert isinstance(make_atom("class == feature"), ClassAtom)
    assert make_atom("class == feature").value == "feature"
    assert isinstance(make_atom("has_signature"), SignatureAtom)


def test_make_atom_comparison_runtime_vs_loose():
    a = make_atom("design_source == author")   # bez pomlčky → CMP_RE → runtime_known
    assert isinstance(a, ComparisonAtom) and a.runtime_known is True and a.lhs == "design_source"
    b = make_atom("fault == db-schema")        # pomlčka → CMP_LOOSE → runtime_known False
    assert isinstance(b, FaultAtom) and b.value == "db-schema" and b.runtime_known is False
    c = make_atom("fault == spec")             # bez pomlčky → runtime_known
    assert isinstance(c, FaultAtom) and c.runtime_known is True


def test_make_atom_freetext():
    multi = make_atom("mockup needs missing component")
    assert isinstance(multi, FreeTextAtom) and multi.bare_word is None
    typo = make_atom("has_databse")            # bare neznámé slovo → free + bare_word (C14)
    assert isinstance(typo, FreeTextAtom) and typo.bare_word == "has_databse"


# ── vyhodnocení atomů ──────────────────────────────────────────────────────────
def test_outcome_atom_evaluate(make_ctx):
    a = OutcomeAtom("FAIL")
    assert a.evaluate(make_ctx(), "FAIL") is Verdict.TRUE
    assert a.evaluate(make_ctx(), "PASS") is Verdict.FALSE
    assert a.evaluate(make_ctx(), None) is Verdict.UNKNOWN   # outcome nepředán


def test_structural_flag_evaluate(make_ctx):
    a = StructuralFlagAtom("has_db", "has_db")
    assert a.evaluate(make_ctx(flags={"has_db": True}), None) is Verdict.TRUE
    assert a.evaluate(make_ctx(flags={"has_db": False}), None) is Verdict.FALSE
    assert a.evaluate(make_ctx(), None) is Verdict.UNKNOWN   # chybí → None → UNKNOWN


def test_signature_default_false(make_ctx):
    a = SignatureAtom("has_signature")
    assert a.evaluate(make_ctx(), None) is Verdict.FALSE                       # JEDINÝ default False
    assert a.evaluate(make_ctx(flags={"has_signature": True}), None) is Verdict.TRUE


def test_comparison_evaluate(make_ctx):
    a = ComparisonAtom("design_source", "==", "author", "design_source == author")
    assert a.evaluate(make_ctx(flags={"design_source": "author"}), None) is Verdict.TRUE
    assert a.evaluate(make_ctx(flags={"design_source": "intake"}), None) is Verdict.FALSE
    assert a.evaluate(make_ctx(), None) is Verdict.UNKNOWN
    ne = ComparisonAtom("design_source", "!=", "author", "design_source != author")
    assert ne.evaluate(make_ctx(flags={"design_source": "intake"}), None) is Verdict.TRUE


def test_class_atom_evaluate(make_ctx):
    a = ClassAtom("feature", "class == feature")
    assert a.evaluate(make_ctx(cls="feature"), None) is Verdict.TRUE
    assert a.evaluate(make_ctx(cls="bugfix"), None) is Verdict.FALSE
    assert a.evaluate(make_ctx(), None) is Verdict.UNKNOWN


# ── FAIL-prefix pravidlo ────────────────────────────────────────────────────────
def test_freetext_fail_prefix(make_ctx):
    a = FreeTextAtom("FAIL: build/deploy/migration")
    assert a.evaluate(make_ctx(), "FAIL") is Verdict.JUDGMENT    # FAIL outcome → judgment
    assert a.evaluate(make_ctx(), "PASS") is Verdict.FALSE       # ne-FAIL → skip
    assert a.evaluate(make_ctx(), None) is Verdict.JUDGMENT      # bez outcome → judgment


def test_freetext_plain_is_judgment(make_ctx):
    assert FreeTextAtom("needs human review").evaluate(make_ctx(), "PASS") is Verdict.JUDGMENT


# ── kombinace verdiktů (NENÍ Kleene) ────────────────────────────────────────────
def test_and_judgment_dominates(make_ctx):
    # And(FALSE, JUDGMENT) → JUDGMENT (Kleene by dal FALSE — to by změnilo chování)
    node = And([StructuralFlagAtom("has_db", "has_db"), FreeTextAtom("please review this")])
    assert node.evaluate(make_ctx(flags={"has_db": False}), None) is Verdict.JUDGMENT


def test_and_unknown_over_bool(make_ctx):
    node = And([StructuralFlagAtom("has_db", "has_db"), StructuralFlagAtom("has_ui", "has_ui")])
    assert node.evaluate(make_ctx(flags={"has_db": True}), None) is Verdict.UNKNOWN   # has_ui chybí


def test_and_all_true(make_ctx):
    node = And([StructuralFlagAtom("has_db", "has_db"), StructuralFlagAtom("has_ui", "has_ui")])
    assert node.evaluate(make_ctx(flags={"has_db": True, "has_ui": True}), None) is Verdict.TRUE


def test_or_any_true(make_ctx):
    node = Or([StructuralFlagAtom("has_db", "has_db"), StructuralFlagAtom("has_ui", "has_ui")])
    assert node.evaluate(make_ctx(flags={"has_db": False, "has_ui": True}), None) is Verdict.TRUE


def test_not_preserves_unknown_judgment(make_ctx):
    n = Not(StructuralFlagAtom("has_db", "has_db"))
    assert n.evaluate(make_ctx(flags={"has_db": False}), None) is Verdict.TRUE
    assert n.evaluate(make_ctx(flags={"has_db": True}), None) is Verdict.FALSE
    assert n.evaluate(make_ctx(), None) is Verdict.UNKNOWN                    # U→U
    assert Not(FreeTextAtom("x y z")).evaluate(make_ctx(), "PASS") is Verdict.JUDGMENT   # J→J


# ── Predicate (parse / classify / structural_live) ──────────────────────────────
def test_predicate_empty(make_ctx):
    p = Predicate.of(None)
    assert p.root is None
    assert p.evaluate(make_ctx()) is Verdict.TRUE
    assert p.classify(make_ctx()) == "eligible"
    assert p.structural_live(make_ctx()) is True


def test_predicate_classify(make_ctx):
    p = Predicate.of("has_db")
    assert p.classify(make_ctx(flags={"has_db": True})) == "eligible"
    assert p.classify(make_ctx(flags={"has_db": False})) == "skip"
    assert p.classify(make_ctx()) == "judgment"           # UNKNOWN → judgment


def test_parser_precedence(make_ctx):
    # has_db || has_ui && has_server  ==  has_db || (has_ui && has_server)
    p = Predicate.of("has_db || has_ui && has_server")
    assert p.evaluate(make_ctx(flags={"has_db": False, "has_ui": True, "has_server": False})) is Verdict.FALSE
    assert p.evaluate(make_ctx(flags={"has_db": True, "has_ui": True, "has_server": False})) is Verdict.TRUE


def test_parser_parens(make_ctx):
    p = Predicate.of("(has_db || has_ui) && has_server")
    assert p.evaluate(make_ctx(flags={"has_db": True, "has_ui": False, "has_server": False})) is Verdict.FALSE
    assert p.evaluate(make_ctx(flags={"has_db": True, "has_ui": False, "has_server": True})) is Verdict.TRUE


def test_parser_not_binds_tightest(make_ctx):
    p = Predicate.of("!has_db && has_ui")   # (!has_db) && has_ui
    assert p.evaluate(make_ctx(flags={"has_db": False, "has_ui": True})) is Verdict.TRUE
    assert p.evaluate(make_ctx(flags={"has_db": True, "has_ui": True})) is Verdict.FALSE


def test_logical_not_has_signature_on_empty_flags(make_ctx):
    # Reálná intake hrana (`class == bugfix && !has_signature`): bugfix bez signature → eligible.
    # has_signature má default False, takže !False = True i na PRÁZDNÝCH flazích (parita tabulka).
    p = Predicate.of("class == bugfix && !has_signature")
    assert p.classify(make_ctx(cls="bugfix")) == "eligible"
    assert p.classify(make_ctx(cls="bugfix", flags={"has_signature": True})) == "skip"


def test_malformed_to_judgment(make_ctx):
    p = Predicate.parse("has_db &&")          # visící operátor → Malformed (jako eval-výjimka)
    assert isinstance(p.root, Malformed)
    assert p.structural_live(make_ctx(flags={"has_db": False})) is True   # legacy: výjimka → live


def test_structural_live_falsified(make_ctx):
    p = Predicate.of("has_db")
    assert p.structural_live(make_ctx(flags={"has_db": False})) is False   # strukturálně falsifikováno
    assert p.structural_live(make_ctx(flags={"has_db": True})) is True
    assert p.structural_live(make_ctx()) is True                          # None → nefalsifikuje


def test_structural_live_ignores_outcome_atom(make_ctx):
    # OutcomeAtom není strukturální flag → nefalsifikuje dep hranu
    assert Predicate.of("FAIL").structural_live(make_ctx()) is True


def test_predicate_of_memoized():
    assert Predicate.of("has_db") is Predicate.of("has_db")
    assert Predicate.of("has_db") is Predicate.of("  has_db  ")   # klíč je strip


def test_has_fault():
    p = Predicate.of("fault == db-schema")
    assert p.has_fault("db-schema") is True
    assert p.has_fault("contract") is False


# ── C14 problems() (slovníková validace z AST) ──────────────────────────────────
@pytest.fixture
def vocab():
    return Vocabulary({
        "flags": {"has_db": {"kind": "bool"},
                  "design_source": {"kind": "enum", "values": ["author", "intake", "derive"]}},
        "classes": ["feature", "bugfix", "improvement"],
        "faults": ["db-schema", "contract", "spec"],
        "targets": ["web", "mobile", "desktop"],
    })


def test_problems_unknown_flag(vocab):
    assert Predicate.of("has_databse").problems(vocab, "node 'x'") == \
        ["C14 node 'x': neznámý flag/atom 'has_databse' (∉ vocabulary.flags)"]


def test_problems_enum_mismatch(vocab):
    assert Predicate.of("design_source == authour").problems(vocab, "edge a→b") == \
        ["C14 edge a→b: 'design_source == authour' — neznámá hodnota (∉ ['author', 'intake', 'derive'])"]


def test_problems_unknown_fault(vocab):
    assert Predicate.of("fault == bogus").problems(vocab, "e") == \
        ["C14 e: neznámý fault 'bogus' (∉ ['contract', 'db-schema', 'spec'])"]


def test_problems_unknown_target(vocab):
    assert Predicate.of("project.targets.tv").problems(vocab, "n") == \
        ["C14 n: neznámý target 'tv' (∉ ['desktop', 'mobile', 'web'])"]


def test_problems_known_ok(vocab):
    assert Predicate.of("has_db && design_source == author").problems(vocab, "x") == []


def test_problems_multiword_freetext_ok(vocab):
    # víceslovná fráze = deliberate judgment, nikdy C14 nález
    assert Predicate.of("mockup needs missing component").problems(vocab, "x") == []
