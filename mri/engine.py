"""Diagnosis engine.

1. Keep every hypothesis (the correct method or a wrong rule) that reproduces
   all of the student's answers exactly.
2. If more than one survives, ask the question whose predicted answers split
   the survivors most evenly (maximum entropy of the partition). One answer to
   that question rules out as many hypotheses as possible.
3. If nothing survives, say so: the student's reasoning is not in the bank,
   and a teacher should look.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .core import Answer, Operand, Problem, correct_answer, same
from .rules import CORRECT_ID, RULES_BY_ID, Rule, student_answer

Observation = Tuple[Problem, Answer]


def answer_key(a: Optional[Answer]):
    if a is None:
        return ("none",)
    if isinstance(a, tuple):
        return ("form",) + a
    v = Fraction(a)
    return ("value", v.numerator, v.denominator)


# ---- question pools -------------------------------------------------------------

def _proper(dmax: int) -> List[Operand]:
    return [Operand(0, n, d) for d in range(2, dmax + 1) for n in range(1, d)]


@lru_cache(maxsize=None)
def problem_pool(op: str) -> Tuple[Problem, ...]:
    """All candidate questions for one operation, simplest first."""
    fr = _proper(8)
    out: List[Problem] = []
    if op in ("+", "*", "/"):
        out += [Problem(op, a, b) for a in fr for b in fr]
    if op == "*":
        wholes = [Operand(k, 0, 1) for k in range(2, 7)]
        out += [Problem(op, a, w) for a in fr for w in wholes]
    if op == "-":
        out += [Problem(op, a, b) for a in fr for b in fr if a.value > b.value]
        mixed = [Operand(w, f.n, f.d) for w in range(1, 6) for f in _proper(6)]
        wholes = [Operand(k, 0, 1) for k in range(1, 7)]
        for x in mixed + wholes:
            for y in mixed + _proper(6):
                if y.value < x.value:  # keep results positive, as in class
                    out.append(Problem(op, x, y))
    if op == "simplify":
        out += [Problem(op, Operand(0, n, d)) for d in range(2, 13) for n in range(1, d + 1)
                if math.gcd(n, d) > 1]
    out.sort(key=complexity)
    return tuple(out)


def complexity(p: Problem) -> int:
    ops = [p.x] + ([p.y] if p.y else [])
    return sum(o.w * 3 + o.n + o.d for o in ops)


# ---- core logic -----------------------------------------------------------------

def hypotheses_for(ops: Iterable[str], rules: Dict[str, Rule] = RULES_BY_ID) -> List[str]:
    ops = set(ops)
    return [CORRECT_ID] + [r.id for r in rules.values() if ops & set(r.ops)]


def mismatches(h: str, obs: Sequence[Observation], rules=RULES_BY_ID) -> int:
    return sum(0 if same(student_answer(h, p, rules), a) else 1 for p, a in obs)


def survivors(hyps: Sequence[str], obs: Sequence[Observation], tolerance: int = 0,
              rules=RULES_BY_ID) -> List[str]:
    return [h for h in hyps if mismatches(h, obs, rules) <= tolerance]


def split(hyps: Sequence[str], p: Problem, rules=RULES_BY_ID) -> Dict[tuple, List[str]]:
    groups: Dict[tuple, List[str]] = defaultdict(list)
    for h in hyps:
        groups[answer_key(student_answer(h, p, rules))].append(h)
    return groups


def entropy(groups: Dict[tuple, List[str]]) -> float:
    total = sum(len(v) for v in groups.values())
    return -sum((len(v) / total) * math.log2(len(v) / total) for v in groups.values())


def best_question(hyps: Sequence[str], pool: Sequence[Problem], asked: Iterable[Problem] = (),
                  rules=RULES_BY_ID) -> Optional[Problem]:
    """The simplest question that splits the remaining hypotheses most."""
    if len(hyps) < 2:
        return None
    asked = set(asked)
    best, best_h = None, 0.0
    for p in pool:  # pool is sorted simplest first, so ties keep the simpler one
        if p in asked:
            continue
        h = entropy(split(hyps, p, rules))
        if h > best_h + 1e-9:
            best, best_h = p, h
            if best_h >= math.log2(len(hyps)) - 1e-9:
                break  # cannot do better than splitting everyone apart
    return best


def traps(rule_id: str, pool: Sequence[Problem], rules=RULES_BY_ID) -> List[Problem]:
    """Questions where this wrong rule still produces the right answer."""
    rule = rules[rule_id]
    return [p for p in pool if rule.fn(p) is not None and same(rule.fn(p), correct_answer(p))]


# ---- stress coverage ------------------------------------------------------------
# A diagnosis is only confirmed after the student has met every "stress" kind
# of problem for the operation. These are the situations where wrong methods
# typically break, so a student cannot pass by only seeing easy cases. This
# guards against wrong rules that are not in the bank but happen to give
# correct answers on easy problems.

def _unlike_shared(p):
    return p.x.is_simple and p.y.is_simple and p.x.d != p.y.d and math.gcd(p.x.d, p.y.d) > 1


def _unlike_coprime(p):
    return p.x.is_simple and p.y.is_simple and math.gcd(p.x.d, p.y.d) == 1


def _needs_regrouping(p):
    fx = Fraction(p.x.n, p.x.d)
    fy = Fraction(p.y.n, p.y.d)
    return p.x.w > 0 and fx < fy


def _frac_times_whole(p):
    return (p.x.is_simple and p.y.is_whole) or (p.y.is_simple and p.x.is_whole)


def _frac_times_frac(p):
    return p.x.is_simple and p.y.is_simple


def _inexact_across(p):
    return (p.x.is_simple and p.y.is_simple and p.x.n >= p.y.n and p.x.d >= p.y.d
            and (p.x.n % p.y.n != 0 or p.x.d % p.y.d != 0))


def _mixed_unlike(p):
    return p.x.w > 0 and p.y.w > 0 and p.x.n > 0 and p.y.n > 0 and p.x.d != p.y.d


STRESS = {
    "+": {"unlike denominators with a common factor": _unlike_shared,
          "unlike denominators with no common factor": _unlike_coprime},
    "-": {"regrouping a whole": _needs_regrouping,
          "unlike denominators with a common factor": _unlike_shared,
          "two mixed numbers with unlike denominators": _mixed_unlike},
    "*": {"fraction times whole number": _frac_times_whole,
          "fraction times fraction": _frac_times_frac},
    "/": {"tops and bottoms do not divide evenly": _inexact_across},
    "simplify": {},
}


def uncovered(obs: Sequence[Observation], ops: Iterable[str]) -> List[Tuple[str, str]]:
    seen = [p for p, _ in obs]
    out = []
    for op in ops:
        for name, pred in STRESS[op].items():
            if not any(p.op == op and pred(p) for p in seen):
                out.append((op, name))
    return out


@dataclass
class Diagnosis:
    status: str  # "confirmed", "unknown", "ambiguous", "ask"
    survivors: List[str]
    next_question: Optional[Problem] = None
    note: str = ""
    evidence: List[dict] = field(default_factory=list)
    prediction: Optional[Answer] = None  # the answer the leading method expects, stated before the student answers


def _trivial(p: Problem, a: Answer) -> bool:
    """Answers like 0 or a copy of an operand are produced by many methods,
    so they are weak evidence for any single one."""
    if isinstance(a, tuple):
        return False
    v = Fraction(a)
    return v == 0 or v == p.x.value or (p.y is not None and v == p.y.value)


def fired_values(h: str, obs: Sequence[Observation], rules=RULES_BY_ID) -> set:
    """Distinct non-trivial wrong answers that method h reproduced."""
    vals = set()
    for p, a in obs:
        pred = student_answer(h, p, rules)
        if same(pred, a) and not same(pred, correct_answer(p)) and not _trivial(p, pred):
            vals.add(answer_key(pred))
    return vals


def strong_fires(h: str, obs: Sequence[Observation], rules=RULES_BY_ID) -> int:
    return len(fired_values(h, obs, rules))


def _distinctive(h, q, seen_vals, rules) -> bool:
    if h == CORRECT_ID:
        return False
    pred = student_answer(h, q, rules)
    return (not same(pred, correct_answer(q)) and not _trivial(q, pred)
            and answer_key(pred) not in seen_vals)


def diagnose(obs: Sequence[Observation], ops: Iterable[str], tolerance: int = 0,
             rules=RULES_BY_ID, check_coverage: bool = True, min_predictions: int = 2) -> Diagnosis:
    ops = list(ops)
    hyps = hypotheses_for(ops, rules)
    alive = survivors(hyps, obs, tolerance, rules)
    evidence = [{"problem": str(p), "answer": a,
                 "explained_by": [h for h in hyps if same(student_answer(h, p, rules), a)]}
                for p, a in obs]
    if not alive:
        return Diagnosis("unknown", [], note="No method in the bank explains these answers. Refer to a teacher.",
                         evidence=evidence)
    pool = [q for op in ops for q in problem_pool(op)]
    if len(alive) == 1:
        gaps = uncovered(obs, ops) if check_coverage else []
        h = alive[0]
        if not gaps:
            if h == CORRECT_ID or not check_coverage or strong_fires(h, obs, rules) >= min_predictions:
                return Diagnosis("confirmed", alive, evidence=evidence)
            # Confirmation by prediction: ask a question where this method gives a
            # distinctive wrong answer, and state that answer before the student replies.
            asked = {p for p, _ in obs}
            everyone = hypotheses_for(ops, rules)
            seen_vals = fired_values(h, obs, rules)
            cands = [q for q in pool if q not in asked and _distinctive(h, q, seen_vals, rules)]
            if not cands:
                return Diagnosis("confirmed", alive, evidence=evidence,
                                 note="No further distinctive question available.")
            q = max(cands, key=lambda q: (round(entropy(split(everyone, q, rules)), 9), -complexity(q)))
            return Diagnosis("ask", alive, next_question=q, prediction=student_answer(h, q, rules),
                             note="Predicting the answer before you give it, to confirm.", evidence=evidence)
        op, name = gaps[0]
        asked = {p for p, _ in obs}
        # Among stress questions, ask the one that best separates every method in
        # the bank, so a look-alike rule (known or not) is likely to diverge here.
        everyone = hypotheses_for([op], rules)
        cands = [q for q in problem_pool(op) if STRESS[op][name](q) and q not in asked]
        seen_vals = fired_values(h, obs, rules) if h != CORRECT_ID else set()
        probe = max(cands, key=lambda q: (_distinctive(h, q, seen_vals, rules),
                                          round(entropy(split(everyone, q, rules)), 9), -complexity(q)))
        pred = student_answer(h, probe, rules) if _distinctive(h, probe, seen_vals, rules) else None
        return Diagnosis("ask", alive, next_question=probe, prediction=pred,
                         note=f"Checking a harder case before confirming: {name}.", evidence=evidence)
    q = best_question(alive, pool, [p for p, _ in obs], rules)
    if q is None:
        return Diagnosis("ambiguous", alive, note="No question in the pool separates these methods.",
                         evidence=evidence)
    return Diagnosis("ask", alive, next_question=q, evidence=evidence)
