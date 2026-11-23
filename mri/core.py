"""Core fraction types: operands, problems, answers, parsing and formatting.

An operand is a whole part plus a fraction part (w + n/d). A problem is an
operation applied to one or two operands. Arithmetic answers are compared by
exact value. "simplify" answers are compared by their written form (n, d),
because a simplified fraction has the same value as the original.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Optional, Tuple, Union

OPS = ("+", "-", "*", "/", "simplify")
OP_SYMBOL = {"+": "+", "-": "−", "*": "×", "/": "÷", "simplify": "simplify"}

Answer = Union[Fraction, Tuple[int, int]]


@dataclass(frozen=True)
class Operand:
    w: int  # whole part
    n: int  # numerator of fraction part
    d: int  # denominator of fraction part (d >= 1)

    @property
    def value(self) -> Fraction:
        return self.w + Fraction(self.n, self.d)

    @property
    def is_whole(self) -> bool:
        return self.n == 0

    @property
    def is_simple(self) -> bool:
        """A plain fraction with no whole part, like 3/5."""
        return self.w == 0 and self.n != 0

    def __str__(self) -> str:
        if self.n == 0:
            return str(self.w)
        if self.w == 0:
            return f"{self.n}/{self.d}"
        return f"{self.w} {self.n}/{self.d}"


@dataclass(frozen=True)
class Problem:
    op: str
    x: Operand
    y: Optional[Operand] = None

    def __str__(self) -> str:
        if self.op == "simplify":
            return f"Simplify {self.x}"
        return f"{self.x} {OP_SYMBOL[self.op]} {self.y}"


_MIXED = re.compile(r"^\s*(-?\d+)\s+(\d+)\s*/\s*(\d+)\s*$")
_FRAC = re.compile(r"^\s*(-?\d+)\s*/\s*(-?\d+)\s*$")
_WHOLE = re.compile(r"^\s*(-?\d+)\s*$")


def parse_operand(s: str) -> Operand:
    m = _MIXED.match(s)
    if m:
        return Operand(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _FRAC.match(s)
    if m:
        return Operand(0, int(m.group(1)), int(m.group(2)))
    m = _WHOLE.match(s)
    if m:
        return Operand(int(m.group(1)), 0, 1)
    raise ValueError(f"Cannot read '{s}' as a number. Use forms like 3, 3/4 or 2 1/3.")


def parse_problem(s: str) -> Problem:
    s = s.strip()
    if s.lower().startswith("simplify"):
        return Problem("simplify", parse_operand(s[len("simplify"):]))
    for sym, op in (("÷", "/"), ("×", "*"), ("*", "*"), ("+", "+"), ("−", "-")):
        if sym in s:
            a, b = s.split(sym, 1)
            return Problem(op, parse_operand(a), parse_operand(b))
    # binary minus or slash division written with " - " / " : "
    m = re.match(r"^(.+?)\s+-\s+(.+)$", s)
    if m:
        return Problem("-", parse_operand(m.group(1)), parse_operand(m.group(2)))
    m = re.match(r"^(.+?)\s+:\s+(.+)$", s)
    if m:
        return Problem("/", parse_operand(m.group(1)), parse_operand(m.group(2)))
    raise ValueError(f"Cannot read problem '{s}'.")


def parse_answer(problem: Problem, s: str) -> Answer:
    """Read a student's answer. For simplify, keep the written form."""
    o = parse_operand(s)
    if problem.op == "simplify":
        if o.w != 0 and o.n != 0:
            o = Operand(0, o.w * o.d + o.n, o.d)
        if o.n == 0:
            return (o.w, 1)
        return (o.n, o.d)
    return o.value


def correct_answer(p: Problem) -> Optional[Answer]:
    if p.op == "simplify":
        v = p.x.value
        return (v.numerator, v.denominator)
    a, b = p.x.value, p.y.value
    if p.op == "+":
        return a + b
    if p.op == "-":
        return a - b
    if p.op == "*":
        return a * b
    if p.op == "/":
        return None if b == 0 else a / b
    raise ValueError(p.op)


def same(a: Optional[Answer], b: Optional[Answer]) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, tuple) or isinstance(b, tuple):
        return isinstance(a, tuple) and isinstance(b, tuple) and a == b
    return Fraction(a) == Fraction(b)


def fmt(ans: Optional[Answer]) -> str:
    """Write an answer the way a student would read it: 3/4, 2, or 2 1/3."""
    if ans is None:
        return "(no answer)"
    if isinstance(ans, tuple):
        n, d = ans
        return str(n) if d == 1 else f"{n}/{d}"
    v = Fraction(ans)
    if v.denominator == 1:
        return str(v.numerator)
    sign = "-" if v < 0 else ""
    v = abs(v)
    w, r = divmod(v.numerator, v.denominator)
    return f"{sign}{w} {r}/{v.denominator}" if w else f"{sign}{r}/{v.denominator}"


def lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)
