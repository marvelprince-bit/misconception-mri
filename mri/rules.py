"""The rule library: the correct procedure plus common wrong procedures, as code.

Each rule is a small function that answers EVERY problem in its domain, so it can
predict what a student who follows that rule would write for a brand-new question.

These wrong rules were written for this project. The idea of writing wrong rules
as executable code comes from the malrule literature (see README, Prior work).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import lcm
from typing import Callable

from .problems import Problem


@dataclass(frozen=True)
class Rule:
    id: str
    domain: str
    label: str  # shown to the tutor
    fn: Callable[..., Fraction | int | None]
    is_correct: bool = False
    source: str = "library"  # "library" or "ai"
    code: str = ""  # source text, kept for AI-written rules

    def predict(self, problem: Problem) -> Fraction | None:
        """The answer this rule gives, or None if the rule breaks on this problem."""
        return _predict(self, problem)


@lru_cache(maxsize=None)
def _predict(rule: Rule, problem: Problem) -> Fraction | None:
    try:
        out = rule.fn(*problem.args)
    except (ZeroDivisionError, ArithmeticError, TypeError, ValueError):
        return None
    if out is None or isinstance(out, bool):
        return None
    try:
        return Fraction(out)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------- integers
def _true_int(a, op, b):
    return a + b if op == "+" else a - b


def _sign(x):
    return -1 if x < 0 else 1


def _ignore_signs_subtract(a, op, b):
    if op == "-":
        return abs(abs(a) - abs(b))
    return a + b


def _minus_negative_is_minus(a, op, b):
    if op == "-" and b < 0:
        return a - abs(b)
    return _true_int(a, op, b)


def _plus_negative_is_plus(a, op, b):
    if op == "+" and b < 0:
        return a + abs(b)
    return _true_int(a, op, b)


def _two_negatives_make_positive(a, op, b):
    if op == "+" and a < 0 and b < 0:
        return abs(a) + abs(b)
    return _true_int(a, op, b)


def _always_positive(a, op, b):
    return abs(_true_int(a, op, b))


def _sign_of_first(a, op, b):
    return _sign(a) * abs(_true_int(a, op, b))


def _leading_minus_covers_all(a, op, b):
    if a < 0:
        return -_true_int(abs(a), op, b)
    return _true_int(a, op, b)


INTEGER_RULES = [
    Rule("int_correct", "integers", "Works correctly with negative numbers.", _true_int, is_correct=True),
    Rule("int_ignore_signs_subtract", "integers",
         "When subtracting, ignores the signs and takes the smaller size from the larger size "
         "(so 3 - 5 becomes 2).", _ignore_signs_subtract),
    Rule("int_minus_negative_is_minus", "integers",
         "Treats 'minus a negative' as plain minus (so 4 - (-3) becomes 1).", _minus_negative_is_minus),
    Rule("int_plus_negative_is_plus", "integers",
         "Treats 'plus a negative' as plain plus (so 4 + (-3) becomes 7).", _plus_negative_is_plus),
    Rule("int_two_negatives_make_positive", "integers",
         "Believes two negatives added together make a positive (so -3 + (-5) becomes 8).",
         _two_negatives_make_positive),
    Rule("int_always_positive", "integers",
         "Works out the right size but drops the negative sign from the answer (so 3 - 5 becomes 2).",
         _always_positive),
    Rule("int_sign_of_first", "integers",
         "Works out the right size but gives the answer the sign of the first number "
         "(so -3 + 5 becomes -2).", _sign_of_first),
    Rule("int_leading_minus_covers_all", "integers",
         "Reads a leading minus as covering the whole sum (so -3 + 5 becomes -(3 + 5) = -8).",
         _leading_minus_covers_all),
]


# ---------------------------------------------------------------- fractions
def _true_frac(n1, d1, n2, d2):
    return Fraction(n1, d1) + Fraction(n2, d2)


FRACTION_RULES = [
    Rule("frac_correct", "fractions", "Adds fractions correctly.", _true_frac, is_correct=True),
    Rule("frac_add_tops_add_bottoms", "fractions",
         "Adds the tops and adds the bottoms (so 1/2 + 1/3 becomes 2/5).",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, d1 + d2)),
    Rule("frac_add_tops_keep_larger_bottom", "fractions",
         "Adds the tops and keeps the larger bottom (so 1/2 + 1/3 becomes 2/3).",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, max(d1, d2))),
    Rule("frac_add_tops_multiply_bottoms", "fractions",
         "Adds the tops and multiplies the bottoms (so 1/2 + 1/3 becomes 2/6).",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, d1 * d2)),
    Rule("frac_common_bottom_no_scaling", "fractions",
         "Finds the common bottom but forgets to scale the tops (so 1/2 + 1/3 becomes 2/6, "
         "and 1/4 + 1/6 becomes 2/12).",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, lcm(d1, d2))),
    Rule("frac_multiplies_instead", "fractions",
         "Multiplies tops and bottoms instead of adding (so 1/2 + 1/3 becomes 1/6).",
         lambda n1, d1, n2, d2: Fraction(n1 * n2, d1 * d2)),
    Rule("frac_add_tops_keep_first_bottom", "fractions",
         "Adds the tops and keeps the first bottom (so 1/2 + 1/3 becomes 2/2).",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, d1)),
]

# ------------------------------------------- subtracting fractions and mixed numbers
# Rules written from MaE misconception descriptions (Otero, Druga and Lan, MIT licence),
# which draw on Ashlock (2006). The MaE id is given in each label's source note.

def _v(w, n, d):
    return w + Fraction(n, d)


def _true_sub(w1, n1, d1, w2, n2, d2):
    return _v(w1, n1, d1) - _v(w2, n2, d2)


def _sub_tops_and_bottoms(w1, n1, d1, w2, n2, d2):
    """MaE08: subtracts tops and subtracts bottoms (only possible for two plain fractions)."""
    if w1 == 0 and w2 == 0 and d1 != d2:
        return Fraction(n1 - n2, d1 - d2)
    return _true_sub(w1, n1, d1, w2, n2, d2)


def _sub_common_bottom_no_scaling(w1, n1, d1, w2, n2, d2):
    """MaE09: finds the common bottom but keeps the old tops."""
    if w1 == 0 and w2 == 0:
        return Fraction(n1 - n2, lcm(d1, d2))
    return _true_sub(w1, n1, d1, w2, n2, d2)


def _sub_smaller_from_larger(w1, n1, d1, w2, n2, d2):
    """MaE10: never regroups; takes the smaller fraction part from the larger."""
    L = lcm(d1, d2)
    return (w1 - w2) + Fraction(abs(n1 * (L // d1) - n2 * (L // d2)), L)


def _sub_parts_separately(w1, n1, d1, w2, n2, d2):
    """MaE11: wholes, tops and bottoms each subtracted, smaller from larger."""
    if w1 > 0 and w2 > 0 and n1 > 0 and n2 > 0 and d1 != d2:
        return (w1 - w2) + Fraction(abs(n1 - n2), abs(d1 - d2))
    return _true_sub(w1, n1, d1, w2, n2, d2)


SUB_RULES = [
    Rule("sub_correct", "frac_sub", "Subtracts fractions and mixed numbers correctly.", _true_sub, is_correct=True),
    Rule("sub_tops_and_bottoms", "frac_sub",
         "Subtracts the tops and subtracts the bottoms (so 3/4 − 1/2 becomes 2/2). Source: MaE08.",
         _sub_tops_and_bottoms),
    Rule("sub_common_bottom_no_scaling", "frac_sub",
         "Finds the common bottom but keeps the old tops (so 3/4 − 1/2 becomes 2/4). Source: MaE09.",
         _sub_common_bottom_no_scaling),
    Rule("sub_smaller_from_larger", "frac_sub",
         "Never regroups: takes the smaller fraction from the larger, whatever the order "
         "(so 6 − 1 1/4 becomes 5 1/4). Source: MaE10.", _sub_smaller_from_larger),
    Rule("sub_parts_separately", "frac_sub",
         "Subtracts wholes, tops and bottoms separately (so 6 2/3 − 3 1/6 becomes 3 1/3). Source: MaE11.",
         _sub_parts_separately),
]


# ------------------------------------------------------------ multiplying fractions
def _true_mul(w1, n1, d1, w2, n2, d2):
    return _v(w1, n1, d1) * _v(w2, n2, d2)


def _whole_and_frac(w1, n1, d1, w2, n2, d2):
    """(k, n, d) if one side is a whole number k and the other a plain fraction n/d."""
    if n1 == 0 and w2 == 0:
        return w1, n2, d2
    if n2 == 0 and w1 == 0:
        return w2, n1, d1
    return None


def _mul_whole_scales_both(*a):
    """MaE13: multiplies top and bottom by the whole number."""
    wf = _whole_and_frac(*a)
    if wf:
        k, n, d = wf
        return Fraction(n * k, d * k)
    return _true_mul(*a)


def _mul_whole_times_bottom(*a):
    """Project rule: multiplies the bottom by the whole number instead of the top."""
    wf = _whole_and_frac(*a)
    if wf:
        k, n, d = wf
        return Fraction(n, d * k)
    return _true_mul(*a)


def _mul_cross(w1, n1, d1, w2, n2, d2):
    """Project rule: cross-multiplies as if dividing."""
    if w1 == 0 and w2 == 0:
        return Fraction(n1 * d2, d1 * n2)
    return _true_mul(w1, n1, d1, w2, n2, d2)


MUL_RULES = [
    Rule("mul_correct", "frac_mul", "Multiplies fractions correctly.", _true_mul, is_correct=True),
    Rule("mul_whole_scales_both", "frac_mul",
         "Multiplies both the top and the bottom by the whole number (so 2/3 × 3 becomes 6/9). Source: MaE13.",
         _mul_whole_scales_both),
    Rule("mul_whole_times_bottom", "frac_mul",
         "Multiplies the bottom by the whole number instead of the top (so 2/3 × 3 becomes 2/9).",
         _mul_whole_times_bottom),
    Rule("mul_cross", "frac_mul",
         "Cross-multiplies as if dividing (so 2/3 × 3/4 becomes 8/9).", _mul_cross),
]


# --------------------------------------------------------------- dividing fractions
def _true_div(n1, d1, n2, d2):
    return Fraction(n1, d1) / Fraction(n2, d2)


def _div_across_drop_remainder(n1, d1, n2, d2):
    """MaE14: divides top by top and bottom by bottom, ignoring remainders."""
    if n1 >= n2 and d1 >= d2:
        return Fraction(n1 // n2, d1 // d2)
    return _true_div(n1, d1, n2, d2)


def _div_flip_first(n1, d1, n2, d2):
    """MaE15: flips the first fraction instead of the second."""
    return Fraction(d1, n1) * Fraction(n2, d2)


def _div_flip_both(n1, d1, n2, d2):
    """Project rule: flips both fractions."""
    return Fraction(d1, n1) * Fraction(d2, n2)


def _div_multiplies_instead(n1, d1, n2, d2):
    """Project rule: multiplies straight across instead of dividing."""
    return Fraction(n1 * n2, d1 * d2)


DIV_RULES = [
    Rule("div_correct", "frac_div", "Divides fractions correctly.", _true_div, is_correct=True),
    Rule("div_across_drop_remainder", "frac_div",
         "Divides top by top and bottom by bottom, ignoring remainders "
         "(so 7/5 ÷ 3/2 becomes 2/2). Source: MaE14.", _div_across_drop_remainder),
    Rule("div_flip_first", "frac_div",
         "Flips the first fraction instead of the second (so 2/3 ÷ 3/8 becomes 9/16). Source: MaE15.",
         _div_flip_first),
    Rule("div_flip_both", "frac_div",
         "Flips both fractions before multiplying (so 2/3 ÷ 3/8 becomes 4/3).", _div_flip_both),
    Rule("div_multiplies_instead", "frac_div",
         "Multiplies straight across instead of dividing (so 2/3 ÷ 3/8 becomes 1/4).", _div_multiplies_instead),
]

LIBRARY = {"integers": INTEGER_RULES, "fractions": FRACTION_RULES, "frac_sub": SUB_RULES,
           "frac_mul": MUL_RULES, "frac_div": DIV_RULES}


def library(domain: str) -> list[Rule]:
    return list(LIBRARY[domain])


def correct_rule(domain: str) -> Rule:
    return next(r for r in LIBRARY[domain] if r.is_correct)


def get_rule(rule_id: str) -> Rule:
    for rules in LIBRARY.values():
        for r in rules:
            if r.id == rule_id:
                return r
    raise KeyError(rule_id)
