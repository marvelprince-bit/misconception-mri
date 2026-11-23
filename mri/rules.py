"""The rule bank: executable versions of known fraction misconceptions.

Each wrong rule is a small function that answers a problem the way a student
holding that misconception would. It returns None when the rule does not
apply to the problem; the student is then assumed to answer correctly.

Sources: rules tagged with a MaE id are written from the misconception
descriptions in the MaE dataset (Otero, Druga and Lan, MIT license), which
cite Ashlock (2006). Rules tagged "project" are additional competing
hypotheses written for this project so the diagnosis has realistic rivals.
No code or data from MalruleLib is used here.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Callable, Dict, List, Optional, Tuple

from .core import Answer, Operand, Problem, correct_answer, lcm


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    source: str  # "MaE08" or "project"
    ops: Tuple[str, ...]
    student_view: str  # plain description shown to a student
    teacher_note: str  # what to reteach
    fn: Callable[[Problem], Optional[Answer]]


def _simple(o: Operand) -> bool:
    return o.w == 0 and o.n != 0


def _mixed_parts(o: Operand) -> Tuple[int, int, int]:
    """Whole, numerator, denominator; a whole number has fraction part 0/1."""
    return o.w, o.n, o.d


# ---- addition and subtraction ------------------------------------------------

def add_across(p: Problem) -> Optional[Answer]:
    """Add (or subtract) tops and bottoms: a/b + c/d = (a+c)/(b+d)."""
    if p.op not in ("+", "-") or not (_simple(p.x) and _simple(p.y)):
        return None
    a, b, c, d = p.x.n, p.x.d, p.y.n, p.y.d
    num = a + c if p.op == "+" else a - c
    den = b + d if p.op == "+" else b - d
    return None if den == 0 else Fraction(num, den)


def lcd_keep_numerators(p: Problem) -> Optional[Answer]:
    """Finds the common denominator but copies the original numerators."""
    if p.op not in ("+", "-") or not (_simple(p.x) and _simple(p.y)):
        return None
    L = lcm(p.x.d, p.y.d)
    num = p.x.n + p.y.n if p.op == "+" else p.x.n - p.y.n
    return Fraction(num, L)


def add_nums_multiply_denoms(p: Problem) -> Optional[Answer]:
    """Adds the numerators but multiplies the denominators."""
    if p.op != "+" or not (_simple(p.x) and _simple(p.y)):
        return None
    return Fraction(p.x.n + p.y.n, p.x.d * p.y.d)


def smaller_from_larger(p: Problem) -> Optional[Answer]:
    """Subtracts without regrouping: wholes from wholes, then the smaller
    fraction part from the larger one, whatever order they are written in."""
    if p.op != "-":
        return None
    w1, n1, d1 = _mixed_parts(p.x)
    w2, n2, d2 = _mixed_parts(p.y)
    L = lcm(d1, d2)
    f1, f2 = n1 * (L // d1), n2 * (L // d2)
    return (w1 - w2) + Fraction(abs(f1 - f2), L)


def mixed_parts_separately(p: Problem) -> Optional[Answer]:
    """Mixed subtraction done part by part: wholes, then numerators, then
    denominators, each time taking the smaller from the larger."""
    if p.op != "-" or p.x.w == 0 or p.y.w == 0 or p.x.n == 0 or p.y.n == 0:
        return None
    dd = abs(p.x.d - p.y.d)
    if dd == 0:
        return None
    return (p.x.w - p.y.w) + Fraction(abs(p.x.n - p.y.n), dd)


# ---- multiplication -----------------------------------------------------------

def whole_times_both(p: Problem) -> Optional[Answer]:
    """Multiplies a fraction by a whole number by scaling top and bottom."""
    if p.op != "*":
        return None
    fr, wh = (p.x, p.y) if p.y.is_whole and _simple(p.x) else (p.y, p.x)
    if not (wh.is_whole and _simple(fr)):
        return None
    k = wh.w
    if k == 0:
        return None
    return Fraction(fr.n * k, fr.d * k)


def multiply_cross(p: Problem) -> Optional[Answer]:
    """Cross-multiplies as if dividing: a/b × c/d = (a·d)/(b·c)."""
    if p.op != "*" or not (_simple(p.x) and _simple(p.y)):
        return None
    return Fraction(p.x.n * p.y.d, p.x.d * p.y.n)


# ---- division -----------------------------------------------------------------

def divide_across_drop_remainder(p: Problem) -> Optional[Answer]:
    """Divides tops by tops and bottoms by bottoms, dropping remainders."""
    if p.op != "/" or not (_simple(p.x) and _simple(p.y)):
        return None
    num, den = p.x.n // p.y.n, p.x.d // p.y.d
    return None if den == 0 else Fraction(num, den)


def invert_dividend(p: Problem) -> Optional[Answer]:
    """Flips the first fraction instead of the second, then multiplies."""
    if p.op != "/" or not (_simple(p.x) and _simple(p.y)):
        return None
    return Fraction(p.x.d, p.x.n) * Fraction(p.y.n, p.y.d)


def invert_both(p: Problem) -> Optional[Answer]:
    """Flips both fractions, then multiplies."""
    if p.op != "/" or not (_simple(p.x) and _simple(p.y)):
        return None
    return Fraction(p.x.d, p.x.n) * Fraction(p.y.d, p.y.n)


# ---- simplifying --------------------------------------------------------------

def simplify_top_only(p: Problem) -> Optional[Answer]:
    """Divides only the numerator by the common factor."""
    if p.op != "simplify" or not _simple(p.x):
        return None
    g = gcd(p.x.n, p.x.d)
    if g == 1:
        return None
    return (p.x.n // g, p.x.d)


RULES: List[Rule] = [
    Rule("R01", "Adds tops and bottoms", "MaE08", ("+", "-"),
         "You added the tops together and the bottoms together.",
         "Fractions are added in equal-sized pieces: rename to a common denominator, then add only the numerators.",
         add_across),
    Rule("R02", "Common denominator, numerators copied", "MaE09", ("+", "-"),
         "You found the common bottom number but kept the old top numbers.",
         "When the denominator is multiplied to make the common denominator, the numerator must be multiplied by the same number.",
         lcd_keep_numerators),
    Rule("R03", "Adds tops, multiplies bottoms", "project", ("+",),
         "You added the tops but multiplied the bottoms.",
         "Mixing the addition and multiplication procedures; contrast the two with area models.",
         add_nums_multiply_denoms),
    Rule("R04", "Smaller from larger, no regrouping", "MaE10", ("-",),
         "You took the smaller fraction from the larger one instead of borrowing a whole.",
         "When the fraction being taken away is larger, regroup one whole into fraction pieces first.",
         smaller_from_larger),
    Rule("R05", "Mixed numbers part by part", "MaE11", ("-",),
         "You subtracted wholes, tops and bottoms separately.",
         "Rename to a common denominator before subtracting; denominators are never subtracted.",
         mixed_parts_separately),
    Rule("R06", "Whole number scales top and bottom", "MaE13", ("*",),
         "You multiplied both the top and the bottom by the whole number.",
         "Multiplying by n means n groups of the fraction: only the numerator is multiplied.",
         whole_times_both),
    Rule("R07", "Cross-multiplies when multiplying", "project", ("*",),
         "You cross-multiplied, which is a step people use for dividing.",
         "Multiplication is straight across: tops times tops, bottoms times bottoms.",
         multiply_cross),
    Rule("R08", "Divides across, drops remainders", "MaE14", ("/",),
         "You divided top by top and bottom by bottom and ignored what was left over.",
         "Dividing across only works when both divisions are exact; teach multiply by the reciprocal.",
         divide_across_drop_remainder),
    Rule("R09", "Flips the first fraction", "MaE15", ("/",),
         "You flipped the first fraction instead of the second.",
         "Keep the first fraction, flip the divisor: ask how many of the second fit into the first.",
         invert_dividend),
    Rule("R10", "Flips both fractions", "project", ("/",),
         "You flipped both fractions before multiplying.",
         "Only the divisor is flipped; check with a simple case like 1 ÷ 1/2 = 2.",
         invert_both),
    Rule("R11", "Simplifies the top only", "MaE07", ("simplify",),
         "You divided the top by the common factor but left the bottom unchanged.",
         "Simplifying divides top and bottom by the same factor so the value stays the same.",
         simplify_top_only),
]

RULES_BY_ID: Dict[str, Rule] = {r.id: r for r in RULES}

CORRECT_ID = "OK"


def student_answer(rule_id: str, p: Problem, rules: Dict[str, Rule] = RULES_BY_ID) -> Optional[Answer]:
    """Answer a problem as a student with this rule would. 'OK' means correct."""
    if rule_id == CORRECT_ID:
        return correct_answer(p)
    out = rules[rule_id].fn(p)
    return correct_answer(p) if out is None else out
