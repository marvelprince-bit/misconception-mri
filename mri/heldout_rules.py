"""Extra wrong rules used ONLY as fairness checks. They are never in the tool's list.

Why this file exists: the tool's safety checks were designed while testing against
the 13 library rules, so results on those 13 are flattering.

SET 1 (HELD_OUT_RULES) was written after the checks were first fixed. It exposed a
flaw: one of its six rules was misdiagnosed every time, because the confirmation
step preferred questions where the leading rule's answer was unique. That
preference was removed. Set 1 is therefore no longer a clean test.

SET 2 (HELD_OUT_RULES_2) was written before the fix was run and was evaluated once
after it. Nothing was changed after seeing its result.

If you change the engine, write a new set. Do not tune against these.
"""
from __future__ import annotations

from fractions import Fraction

from .rules import Rule


def _larger_size_sign_on_subtract(a, op, b):
    if op == "+":
        return a + b
    size = abs(abs(a) - abs(b))
    return size if abs(b) > abs(a) and b > 0 or abs(a) >= abs(b) and a > 0 else -size


def _any_negative_add_sizes_negative(a, op, b):
    if a < 0 or b < 0:
        return -(abs(a) + abs(b))
    return a + b if op == "+" else a - b


def _minus_negative_flips_everything(a, op, b):
    if op == "-" and b < 0:
        return -(a + abs(b))
    return a + b if op == "+" else a - b


HELD_OUT_RULES = [
    Rule("held_int_larger_size_sign_on_subtract", "integers",
         "On subtraction, takes the difference in size and the sign of the larger-size number.",
         _larger_size_sign_on_subtract),
    Rule("held_int_any_negative_add_sizes_negative", "integers",
         "If any number is negative, adds the sizes and makes the answer negative.",
         _any_negative_add_sizes_negative),
    Rule("held_int_minus_negative_flips_everything", "integers",
         "Reads a - (-b) as -(a + b).", _minus_negative_flips_everything),
    Rule("held_frac_add_tops_keep_smaller_bottom", "fractions",
         "Adds the tops and keeps the smaller bottom.",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, min(d1, d2))),
    Rule("held_frac_cross_multiply_tops_add_bottoms", "fractions",
         "Cross-multiplies for the top but adds the bottoms.",
         lambda n1, d1, n2, d2: Fraction(n1 * d2 + n2 * d1, d1 + d2)),
    Rule("held_frac_scale_first_top_only", "fractions",
         "Multiplies the bottoms, but only scales the first top.",
         lambda n1, d1, n2, d2: Fraction(n1 * d2 + n2, d1 * d2)),
]


# ----------------------------------------------------------------- set 2
def _signs_differ_add_keeps_first_sign(a, op, b):
    if op == "+" and (a < 0) != (b < 0):
        size = abs(abs(a) - abs(b))
        return -size if a < 0 else size
    return a + b if op == "+" else a - b


def _cannot_go_below_zero(a, op, b):
    result = a + b if op == "+" else a - b
    if a > 0 and result < 0:
        return 0
    return result


def _negative_minus_positive_subtracts_sizes(a, op, b):
    if a < 0 and op == "-" and b > 0:
        return -(abs(a) - b)
    return a + b if op == "+" else a - b


HELD_OUT_RULES_2 = [
    Rule("held2_int_signs_differ_add_keeps_first_sign", "integers",
         "Adding numbers with different signs: subtracts the sizes, keeps the first number's sign.",
         _signs_differ_add_keeps_first_sign),
    Rule("held2_int_cannot_go_below_zero", "integers",
         "Starting from a positive number, stops at 0 instead of going negative.",
         _cannot_go_below_zero),
    Rule("held2_int_negative_minus_positive_subtracts_sizes", "integers",
         "For negative minus positive, subtracts the sizes (so -3 - 5 becomes 2).",
         _negative_minus_positive_subtracts_sizes),
    Rule("held2_frac_add_both_only_when_bottoms_differ", "fractions",
         "Correct with same bottoms; otherwise adds tops and adds bottoms.",
         lambda n1, d1, n2, d2: Fraction(n1 + n2, d1) if d1 == d2 else Fraction(n1 + n2, d1 + d2)),
    Rule("held2_frac_common_bottom_then_adds_bottoms", "fractions",
         "Finds the common bottom and scales the tops correctly, then adds the bottoms as well.",
         lambda n1, d1, n2, d2: Fraction(n1 * d2 + n2 * d1, 2 * d1 * d2)),
    Rule("held2_frac_flips_second_and_multiplies", "fractions",
         "Flips the second fraction and multiplies (confuses adding with dividing).",
         lambda n1, d1, n2, d2: Fraction(n1 * d2, d1 * n2)),
]


# ----------------------------------------------------------------- set 3
# Written on 23 Nov 2026 AFTER the merged design was frozen (commit 377934c) and
# BEFORE any result on these rules was seen. Covers all five topics. Run once; the
# number is published whatever it is. Do not tune the engine against this set.

def _v(w, n, d):
    return w + Fraction(n, d)


def _h3_int_signs_differ_add_sizes_sign_of_larger(a, op, b):
    """Adding numbers with different signs: adds the sizes, keeps the sign of the larger size."""
    if op == "+" and (a < 0) != (b < 0):
        size = abs(a) + abs(b)
        return -size if (abs(a) >= abs(b) and a < 0) or (abs(b) > abs(a) and b < 0) else size
    return a + b if op == "+" else a - b


def _h3_int_minus_negative_answer_negative(a, op, b):
    """Minus a negative: adds the sizes but makes the answer negative."""
    if op == "-" and b < 0:
        return -(abs(a) + abs(b))
    return a + b if op == "+" else a - b


def _h3_frac_cross_tops_add_bottoms(n1, d1, n2, d2):
    """Cross-multiplies the tops correctly but adds the bottoms."""
    return Fraction(n1 * d2 + n2 * d1, d1 + d2)


def _h3_frac_multiply_tops_add_bottoms(n1, d1, n2, d2):
    """Multiplies the tops and adds the bottoms."""
    return Fraction(n1 * n2, d1 + d2)


def _h3_sub_borrow_ten(w1, n1, d1, w2, n2, d2):
    """When regrouping, adds 10 to the top instead of one whole's worth (place-value habit)."""
    L = (d1 * d2) // __import__("math").gcd(d1, d2)
    t1, t2 = n1 * (L // d1), n2 * (L // d2)
    if t1 < t2 and w1 > 0:
        return (w1 - 1 - w2) + Fraction(t1 + 10 - t2, L)
    return _v(w1, n1, d1) - _v(w2, n2, d2)


def _h3_sub_regroup_keeps_whole(w1, n1, d1, w2, n2, d2):
    """Regroups correctly in the fraction part but forgets to take 1 from the whole."""
    if w1 > 0 and Fraction(n1, d1) < Fraction(n2, d2):
        return _v(w1, n1, d1) - _v(w2, n2, d2) + 1
    return _v(w1, n1, d1) - _v(w2, n2, d2)


def _h3_mul_whole_adds_to_top(w1, n1, d1, w2, n2, d2):
    """Fraction times a whole number: adds the whole number to the top."""
    if n1 == 0 and w2 == 0:
        return Fraction(n2 + w1, d2)
    if n2 == 0 and w1 == 0:
        return Fraction(n1 + w2, d1)
    return _v(w1, n1, d1) * _v(w2, n2, d2)


def _h3_mul_adds_across(w1, n1, d1, w2, n2, d2):
    """Two fractions: adds tops and adds bottoms instead of multiplying."""
    if w1 == 0 and w2 == 0:
        return Fraction(n1 + n2, d1 + d2)
    return _v(w1, n1, d1) * _v(w2, n2, d2)


def _h3_div_tops_keep_first_bottom(n1, d1, n2, d2):
    """Divides the tops and keeps the first bottom."""
    return Fraction(n1, n2) / d1


def _h3_div_times_second_bottom(n1, d1, n2, d2):
    """Multiplies by the second fraction's bottom and ignores its top.
    (Replaced, before any result was seen, a first choice that turned out to be
    identical to the library rule div_flip_first.)"""
    return Fraction(n1 * d2, d1)


HELD_OUT_RULES_3 = [
    Rule("h3_int_signs_differ_add_sizes_sign_of_larger", "integers",
         "Different signs: adds the sizes, keeps the sign of the larger.", _h3_int_signs_differ_add_sizes_sign_of_larger),
    Rule("h3_int_minus_negative_answer_negative", "integers",
         "Minus a negative: adds the sizes, answer negative.", _h3_int_minus_negative_answer_negative),
    Rule("h3_frac_cross_tops_add_bottoms", "fractions",
         "Cross-multiplies the tops, adds the bottoms.", _h3_frac_cross_tops_add_bottoms),
    Rule("h3_frac_multiply_tops_add_bottoms", "fractions",
         "Multiplies the tops, adds the bottoms.", _h3_frac_multiply_tops_add_bottoms),
    Rule("h3_sub_borrow_ten", "frac_sub",
         "Regroups by adding 10 to the top.", _h3_sub_borrow_ten),
    Rule("h3_sub_regroup_keeps_whole", "frac_sub",
         "Regroups but forgets to take 1 from the whole.", _h3_sub_regroup_keeps_whole),
    Rule("h3_mul_whole_adds_to_top", "frac_mul",
         "Adds the whole number to the top.", _h3_mul_whole_adds_to_top),
    Rule("h3_mul_adds_across", "frac_mul",
         "Adds tops and bottoms instead of multiplying.", _h3_mul_adds_across),
    Rule("h3_div_tops_keep_first_bottom", "frac_div",
         "Divides the tops, keeps the first bottom.", _h3_div_tops_keep_first_bottom),
    Rule("h3_div_times_second_bottom", "frac_div",
         "Multiplies by the second bottom, ignores its top.", _h3_div_times_second_bottom),
]
