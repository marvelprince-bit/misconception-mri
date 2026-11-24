"""Problems, question pools, and answer parsing.

Five domains are supported:
  integers  -> args = (a, op, b)                  e.g. -3 - 5
  fractions -> args = (n1, d1, n2, d2)            e.g. 1/2 + 1/3   (fraction addition)
  frac_sub  -> args = (w1, n1, d1, w2, n2, d2)    e.g. 6 - 1 1/4   (fractions and mixed numbers)
  frac_mul  -> args = (w1, n1, d1, w2, n2, d2)    e.g. 2/3 x 3     (fraction times fraction or whole)
  frac_div  -> args = (n1, d1, n2, d2)            e.g. 6/8 / 2/8

A whole number w is written (w, 0, 1); a plain fraction n/d is written (0, n, d).

Every answer is stored as a Fraction, so 2/4 and 1/2 count as the same answer.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from math import gcd

DOMAINS = ("integers", "fractions", "frac_sub", "frac_mul", "frac_div")
TITLES = {
    "integers": "Adding and subtracting negative numbers",
    "fractions": "Adding fractions",
    "frac_sub": "Subtracting fractions and mixed numbers",
    "frac_mul": "Multiplying fractions",
    "frac_div": "Dividing fractions",
}


def mixed(w: int, n: int, d: int) -> str:
    if n == 0:
        return str(w)
    return f"{n}/{d}" if w == 0 else f"{w} {n}/{d}"


def value(w: int, n: int, d: int) -> Fraction:
    return w + Fraction(n, d)


@dataclass(frozen=True)
class Problem:
    domain: str
    args: tuple

    def text(self) -> str:
        if self.domain == "integers":
            a, op, b = self.args
            right = f"({b})" if b < 0 else str(b)
            return f"{a} {op} {right}"
        if self.domain == "fractions":
            n1, d1, n2, d2 = self.args
            return f"{n1}/{d1} + {n2}/{d2}"
        if self.domain == "frac_div":
            n1, d1, n2, d2 = self.args
            return f"{n1}/{d1} ÷ {n2}/{d2}"
        w1, n1, d1, w2, n2, d2 = self.args
        sym = "−" if self.domain == "frac_sub" else "×"
        return f"{mixed(w1, n1, d1)} {sym} {mixed(w2, n2, d2)}"


def full_pool(domain: str) -> list[Problem]:
    """Every question the tool is allowed to ask in this domain."""
    if domain == "integers":
        nums = [n for n in range(-9, 10) if n != 0]
        return [Problem(domain, (a, op, b)) for a in nums for op in "+-" for b in nums]
    if domain == "fractions":
        fracs = [(n, d) for d in range(2, 10) for n in range(1, d)]
        return [Problem(domain, (n1, d1, n2, d2)) for n1, d1 in fracs for n2, d2 in fracs]
    if domain == "frac_sub":
        plain = [(0, n, d) for d in range(2, 9) for n in range(1, d)]
        small = [(0, n, d) for d in range(2, 7) for n in range(1, d)]
        mixeds = [(w, n, d) for w in range(1, 6) for _, n, d in small]
        wholes = [(w, 0, 1) for w in range(1, 7)]
        out = [Problem(domain, a + b) for a in plain for b in plain if value(*a) > value(*b)]
        out += [Problem(domain, a + b) for a in mixeds + wholes for b in mixeds + small
                if value(*a) > value(*b)]
        return out
    if domain == "frac_mul":
        plain = [(0, n, d) for d in range(2, 9) for n in range(1, d)]
        wholes = [(k, 0, 1) for k in range(2, 7)]
        out = [Problem(domain, a + b) for a in plain for b in plain]
        out += [Problem(domain, a + w) for a in plain for w in wholes]
        out += [Problem(domain, w + a) for w in wholes for a in plain[:21]]
        return out
    if domain == "frac_div":
        fracs = [(n, d) for d in range(2, 9) for n in range(1, d)]
        return [Problem(domain, (n1, d1, n2, d2)) for n1, d1 in fracs for n2, d2 in fracs]
    raise ValueError(f"unknown domain: {domain}")


def worksheet_pool(domain: str) -> list[Problem]:
    """'Ordinary worksheet' questions: the easy kind where wrong rules hide.

    integers  -> a - b with a > b > 0 (answer is positive, no negative signs)
    fractions -> same denominator
    """
    if domain == "integers":
        return [Problem(domain, (a, "-", b)) for a in range(2, 10) for b in range(1, a)]
    if domain == "fractions":
        return [
            Problem(domain, (n1, d, n2, d))
            for d in range(3, 10)
            for n1 in range(1, d)
            for n2 in range(1, d)
        ]
    if domain == "frac_sub":
        # like bottoms, no regrouping needed: the usual first worksheet
        return [p for p in full_pool(domain)
                if p.args[2] == p.args[5] and p.args[1] >= p.args[4] and p.args[1] > 0]
    if domain == "frac_mul":
        # fraction times fraction, the usual first worksheet
        return [p for p in full_pool(domain) if p.args[0] == 0 and p.args[3] == 0]
    if domain == "frac_div":
        # same bottoms, the usual first worksheet
        return [p for p in full_pool(domain) if p.args[1] == p.args[3]]
    raise ValueError(f"unknown domain: {domain}")


def kind(problem: Problem) -> str:
    """The structural kind of a question, independent of any rule.

    integers  -> sign of first number, operation, sign of second number (8 kinds)
    fractions -> how the two bottoms relate, and which is larger (7 kinds)

    A student can be solid on one kind and lost on another, so the tool tracks
    which kinds have actually been tested.
    """
    if problem.domain == "integers":
        a, op, b = problem.args
        word = lambda x: "negative" if x < 0 else "positive"  # noqa: E731
        return f"{word(a)} {'plus' if op == '+' else 'minus'} {word(b)}"
    if problem.domain == "frac_sub":
        w1, n1, d1, w2, n2, d2 = problem.args
        if w1 == 0 and w2 == 0:
            # How the bottoms relate decides which shortcuts give the right answer by luck,
            # as in fraction addition.
            if d1 == d2:
                rel = "same bottoms"
            elif d1 % d2 == 0 or d2 % d1 == 0:
                rel = "one bottom divides the other"
            elif gcd(d1, d2) > 1:
                rel = "bottoms share a factor"
            else:
                rel = "bottoms share no factor"
            return f"two plain fractions, {rel}"
        if n1 == 0:
            return "whole number minus " + ("mixed number" if w2 > 0 else "fraction")
        bottoms = "same bottoms" if d1 == d2 else "different bottoms"
        regroup = ", regrouping needed" if Fraction(n1, d1) < Fraction(n2, d2) else ""
        # Two mixed numbers vs mixed number minus a plain fraction: procedures that work on
        # whole and fraction parts separately only show up when both sides have both parts.
        first = "two mixed numbers" if (w2 > 0 and n2 > 0) else "mixed number minus fraction"
        return f"{first}, {bottoms}{regroup}"
    if problem.domain == "frac_mul":
        w1, n1, d1, w2, n2, d2 = problem.args
        if n1 == 0 or n2 == 0:
            return "fraction times whole number"
        return "fraction times fraction, " + ("same bottoms" if d1 == d2 else "different bottoms")
    if problem.domain == "frac_div":
        n1, d1, n2, d2 = problem.args
        bottoms = "same bottoms" if d1 == d2 else "different bottoms"
        # Dividing straight across (top by top, bottom by bottom) is only possible when the
        # first top and bottom are at least as large as the second's.
        if n1 < n2 or d1 < d2:
            return f"{bottoms}, cannot divide straight across"
        exact = n1 % n2 == 0 and d1 % d2 == 0
        return f"{bottoms}, " + ("tops and bottoms divide evenly" if exact else "tops or bottoms leave a remainder")
    _, d1, _, d2 = problem.args
    if d1 == d2:
        return "same bottoms"
    order = "smaller bottom first" if d1 < d2 else "larger bottom first"
    if max(d1, d2) % min(d1, d2) == 0:
        return f"one bottom divides the other, {order}"
    if gcd(d1, d2) == 1:
        return f"bottoms share no factor, {order}"
    return f"bottoms share a factor, {order}"


def shape(problem: Problem) -> str:
    """A finer version of kind(), used to re-test a wrong answer on a look-alike question.

    integers add which number is larger in size; fractions use the kind as it is.
    """
    if problem.domain == "integers":
        a, _, b = problem.args
        size = "first larger" if abs(a) > abs(b) else "second larger" if abs(a) < abs(b) else "same size"
        return f"{kind(problem)}, {size}"
    return kind(problem)


def parse_answer(text: str) -> Fraction:
    """Turn what a student typed ('-8', '3/5', '2 1/4', ' 7 ') into a Fraction.

    Raises ValueError with a readable message if the input is not a number.
    """
    parts = text.strip().replace("\u2212", "-").split()
    if len(parts) == 2 and "/" in parts[1] and "/" not in parts[0]:
        try:
            whole, frac = int(parts[0]), Fraction(parts[1])
            return whole + frac if whole >= 0 else whole - frac
        except (ValueError, ZeroDivisionError):
            pass
    cleaned = text.strip().replace(" ", "").replace("\u2212", "-")
    if not cleaned:
        raise ValueError("Empty answer. Type a number such as -8 or 3/5.")
    try:
        return Fraction(cleaned)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"'{text.strip()}' is not a number. Type a number such as -8 or 3/5.") from None


def format_answer(value: Fraction | None) -> str:
    if value is None:
        return "(no answer)"
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def format_mixed(v: Fraction | None) -> str:
    """Like format_answer, but improper fractions are shown as mixed numbers (2 1/4)."""
    if v is None:
        return "(no answer)"
    if v.denominator == 1 or abs(v) < 1:
        return format_answer(v)
    sign = "-" if v < 0 else ""
    w, r = divmod(abs(v.numerator), v.denominator)
    return f"{sign}{w} {r}/{v.denominator}"


def parse_problem_text(domain: str, text: str) -> Problem:
    """Read a question written the way Problem.text() writes it."""
    t = text.strip().replace("\u2212", "-")
    if domain == "integers":
        m = re.match(r"^(-?\d+)\s*([+-])\s*\(?(-?\d+)\)?$", t)
        return Problem(domain, (int(m.group(1)), m.group(2), int(m.group(3))))
    sym = {"fractions": "+", "frac_sub": "-", "frac_mul": "×", "frac_div": "÷"}[domain]
    left, right = [x.strip() for x in t.replace("x", "×").replace("*", "×").replace("/ ", "÷ ").split(f" {sym} ", 1)]
    a, b = _operand(left), _operand(right)
    if domain in ("fractions", "frac_div"):
        return Problem(domain, (a[1], a[2], b[1], b[2]))
    return Problem(domain, a + b)


def _operand(s: str) -> tuple:
    m = re.match(r"^(\d+)\s+(\d+)/(\d+)$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d+)/(\d+)$", s)
    if m:
        return (0, int(m.group(1)), int(m.group(2)))
    return (int(s), 0, 1)
