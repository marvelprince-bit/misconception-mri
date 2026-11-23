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
