"""Decision coverage for AI-written rules ("branch coverage", as in software testing).

Why: live Claude run 8 (24 Nov 2026, new student) named a wrong division rule:
    return (n1 // n2, max(1, d1 // d2))
When the first bottom is smaller than the second, d1 // d2 is 0 and max() quietly
switches to 1. No question had ever sent the rule down that branch, so no check could
see that the student does something else there.

So before an AI rule is named, every outcome of every decision in its code must have
been tried on at least one real student answer:
  - each `if` / conditional expression: true and false,
  - each max() / min(): which arguments win (a tie is its own outcome),
  - each abs(): the sign of what is inside (negative, zero, positive),
  - each whole-number division a // b: whether it gives 0, and whether it leaves a remainder.
Outcomes that cannot happen on any question are not required. If an outcome that can
happen has never been tried, the engine asks a question that tries it.

The instrumented copy is made from code that already passed the sandbox (mri/sandbox.py);
it only wraps existing expressions in recording helpers and runs with the same empty
builtins. It is used only to see which way the rule's decisions go, never to answer.
"""
from __future__ import annotations

import ast

from .sandbox import SAFE_CALLS


class _Wrap(ast.NodeTransformer):
    def __init__(self):
        self.k = 0

    def _id(self):
        self.k += 1
        return ast.Constant(self.k)

    def _call(self, name, args):
        return ast.Call(ast.Name(name, ast.Load()), args, [])

    def visit_If(self, node):
        self.generic_visit(node)
        node.test = self._call("__dec", [self._id(), node.test])
        return node

    def visit_IfExp(self, node):
        self.generic_visit(node)
        node.test = self._call("__dec", [self._id(), node.test])
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in ("max", "min") and len(node.args) >= 2:
            return self._call("__pick", [self._id(), ast.Constant(node.func.id)] + node.args)
        if isinstance(node.func, ast.Name) and node.func.id == "abs" and len(node.args) == 1:
            return self._call("__sign", [self._id(), node.args[0]])
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.FloorDiv):
            return self._call("__fdiv", [self._id(), node.left, node.right])
        return node


def decision_tracer(code: str):
    """Return trace(args) -> frozenset of (decision id, outcome) seen when the rule runs on
    those arguments, or None if the code cannot be traced."""
    try:
        tree = ast.parse(code)
        tree = ast.fix_missing_locations(_Wrap().visit(tree))
    except (SyntaxError, ValueError, RecursionError):
        return None
    seen: list = []

    def dec(k, value):
        seen.append((k, bool(value)))
        return value

    def pick(k, which, *args):
        best = max(args) if which == "max" else min(args)
        seen.append((k, tuple(i for i, a in enumerate(args) if a == best)))
        return best

    def sign(k, x):
        seen.append((k, (x > 0) - (x < 0)))
        return abs(x)

    def fdiv(k, a, b):
        q = a // b
        seen.append((k, ("zero" if q == 0 else "nonzero", a % b == 0)))
        return q

    namespace = {"__builtins__": {}, **SAFE_CALLS, "__dec": dec, "__pick": pick, "__sign": sign, "__fdiv": fdiv}
    try:
        exec(compile(tree, "<traced_rule>", "exec"), namespace)
    except (SyntaxError, ValueError, RecursionError):
        return None
    fn = namespace.get("rule")
    if fn is None:
        return None

    def trace(args):
        seen.clear()
        try:
            fn(*args)
        except (ZeroDivisionError, ArithmeticError, TypeError, ValueError, RecursionError):
            return frozenset(seen) | {("error", True)}
        return frozenset(seen)

    return trace
