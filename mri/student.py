"""Simulated students: the answer key for testing the tool.

A simulated student follows one known rule and sometimes makes a careless slip.
Because we know the rule we gave them, we can check whether the tool finds it.
"""
from __future__ import annotations

import random
from fractions import Fraction

from .problems import Problem
from .rules import Rule


class SimulatedStudent:
    def __init__(self, rule: Rule, slip_rate: float = 0.0, seed: int | None = None):
        self.rule = rule
        self.slip_rate = slip_rate
        self.rng = random.Random(seed)

    def answer(self, problem: Problem) -> Fraction:
        value = self.rule.predict(problem)
        if value is None:
            value = Fraction(0)
        if self.rng.random() < self.slip_rate:
            return self._slip(value)
        return value

    def _slip(self, value: Fraction) -> Fraction:
        """A careless mistake: off by one, or a flipped sign."""
        choices = [
            Fraction(value.numerator + 1, value.denominator),
            Fraction(value.numerator - 1, value.denominator),
        ]
        if value != 0:
            choices.append(-value)
        return self.rng.choice(choices)


class RandomGuesser:
    """A student with no stable rule at all: mixes several rules at random."""

    def __init__(self, rules: list[Rule], seed: int | None = None):
        self.rules = rules
        self.rng = random.Random(seed)

    def answer(self, problem: Problem) -> Fraction:
        value = self.rng.choice(self.rules).predict(problem)
        return value if value is not None else Fraction(0)
