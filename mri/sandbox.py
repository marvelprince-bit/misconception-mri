"""Run AI-written rule code safely.

The AI writes a wrong rule as a small Python function. That code is untrusted, so
before running it we read its syntax tree and allow only plain arithmetic:
no imports, no loops, no attribute access, no file or network use, no powers.
With no loops and no recursion the function always finishes.
"""
from __future__ import annotations

import ast
from fractions import Fraction
from math import gcd, lcm

from .rules import Rule

SIGNATURES = {
    "integers": ["a", "op", "b"],
    "fractions": ["n1", "d1", "n2", "d2"],
    "frac_sub": ["w1", "n1", "d1", "w2", "n2", "d2"],
    "frac_mul": ["w1", "n1", "d1", "w2", "n2", "d2"],
    "frac_div": ["n1", "d1", "n2", "d2"],
}
SAFE_CALLS = {"abs": abs, "min": min, "max": max, "gcd": gcd, "lcm": lcm}

_ALLOWED = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.If, ast.IfExp,
    ast.Assign, ast.Expr, ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Name,
    ast.Constant, ast.Call, ast.Tuple, ast.Load, ast.Store,
    ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not,
    ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)
MAX_CODE_CHARS = 4000
MAX_NODES = 600
MAX_MULTIPLY = 12
MAX_CONSTANT = 1000


class UnsafeRule(Exception):
    """The proposed code is not a plain arithmetic function."""


def _check(tree: ast.Module, domain: str) -> None:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise UnsafeRule("The code must be exactly one function.")
    fn = tree.body[0]
    if fn.name != "rule":
        raise UnsafeRule("The function must be named 'rule'.")
    if fn.decorator_list or fn.returns is not None:
        raise UnsafeRule("Decorators and annotations are not allowed.")
    a = fn.args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs or a.defaults or a.kw_defaults:
        raise UnsafeRule("Only plain positional arguments are allowed.")
    if [x.arg for x in a.args] != SIGNATURES[domain] or any(x.annotation for x in a.args):
        raise UnsafeRule(f"The arguments must be exactly {SIGNATURES[domain]}.")

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise UnsafeRule("The code is too long.")
    if sum(isinstance(n, ast.Mult) for n in nodes) > MAX_MULTIPLY:
        raise UnsafeRule("Too many multiplications.")

    names = set(SIGNATURES[domain])
    for n in nodes:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if not isinstance(t, ast.Name):
                    raise UnsafeRule("Only simple 'name = value' assignments are allowed.")
                if t.id in SAFE_CALLS or t.id == "rule":
                    raise UnsafeRule(f"The name '{t.id}' cannot be reassigned.")
                names.add(t.id)

    docstring = fn.body[0] if fn.body and isinstance(fn.body[0], ast.Expr) else None
    for n in nodes:
        if not isinstance(n, _ALLOWED):
            raise UnsafeRule(f"'{type(n).__name__}' is not allowed in a rule.")
        if isinstance(n, ast.Expr):
            ok = n is docstring and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
            if not ok:
                raise UnsafeRule("Bare expressions are not allowed.")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in SAFE_CALLS or n.keywords:
                raise UnsafeRule("Only abs, min, max, gcd and lcm may be called.")
        if isinstance(n, ast.Name) and n.id not in names and n.id not in SAFE_CALLS:
            raise UnsafeRule(f"Unknown name '{n.id}'.")
        if isinstance(n, ast.Constant):
            v = n.value
            if isinstance(v, bool) or v is None:
                continue
            if isinstance(v, int):
                if abs(v) > MAX_CONSTANT:
                    raise UnsafeRule("Numbers above 1000 are not allowed.")
            elif isinstance(v, str):
                is_doc = docstring is not None and n is docstring.value
                if not is_doc and v not in ("+", "-"):
                    raise UnsafeRule("Only the strings '+' and '-' are allowed.")
            else:
                raise UnsafeRule("Only whole numbers are allowed (no decimals).")


def compile_rule(code: str, domain: str, rule_id: str = "ai_rule", label: str = "") -> Rule:
    """Check the code, then turn it into a Rule. Raises UnsafeRule if it is not allowed."""
    if len(code) > MAX_CODE_CHARS:
        raise UnsafeRule("The code is too long.")
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise UnsafeRule(f"The code does not parse: {type(exc).__name__}.") from None
    _check(tree, domain)
    namespace: dict = {"__builtins__": {}, **SAFE_CALLS}
    try:
        exec(compile(tree, "<ai_rule>", "exec"), namespace)  # tree was whitelisted above
    except (RecursionError, MemoryError, ValueError, SyntaxError) as exc:
        raise UnsafeRule(f"The code could not be compiled: {type(exc).__name__}.") from None
    raw = namespace["rule"]

    if domain != "integers":
        def fn(*args):
            out = raw(*args)
            if (isinstance(out, tuple) and len(out) == 2
                    and all(isinstance(x, int) and not isinstance(x, bool) for x in out) and out[1] != 0):
                return Fraction(out[0], out[1])
            return None
    else:
        def fn(*args):
            out = raw(*args)
            return out if isinstance(out, int) and not isinstance(out, bool) else None

    return Rule(rule_id, domain, label or "AI-written rule (see code).", fn, source="ai", code=code)
