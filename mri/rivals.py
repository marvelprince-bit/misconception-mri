"""Rival rules: small variations of an AI-written rule, used to test it before naming it.

Why: the live Claude run of 23 Nov 2026 (final design) named an AI rule for
sub_parts_separately that was not the student's real rule. The shape check only covers
question shapes not tested yet; inside a tested shape, numbers that line up by
accident (both differences positive, say) can hide a missing "smaller from larger".

So before an AI-written rule is named, the tool makes small edits to its code (add or
drop abs(), swap a subtraction, flip a comparison, drop one condition, swap min and max,
change a constant by one, sign handling in pairs: abs() on two subtractions at once,
on all of them, or on none, and a missing condition: 'v != 0' or 'v > 0' added to an
if, for one argument or a matching pair such as both tops). Every variation goes through the SAME sandbox
as the original. A variation that also fits every answer so far is a rival: the
student's answers so far cannot tell the two apart. The engine then asks the question
that separates the AI rule from the most rivals. The rule is named only when no rival
is left; if rivals remain when the questions run out, the result is "no diagnosis".

Nothing here makes admission easier: rivals can only add questions or stop a diagnosis.
"""
from __future__ import annotations

import ast
import copy
from fractions import Fraction

from .rules import Rule
from .sandbox import UnsafeRule, compile_rule

MAX_RIVALS = 400

_CMP_SWAPS = {
    ast.Lt: (ast.LtE, ast.Gt, ast.NotEq), ast.LtE: (ast.Lt, ast.GtE),
    ast.Gt: (ast.GtE, ast.Lt, ast.NotEq), ast.GtE: (ast.Gt, ast.LtE),
    ast.Eq: (ast.NotEq,), ast.NotEq: (ast.Eq, ast.Gt, ast.Lt),
}


def _edits(node: ast.AST) -> list:
    """Single small edits for one node, as functions that change the node in place
    (or return a replacement node)."""
    out = []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
        out.append(lambda n: ast.Call(ast.Name("abs", ast.Load()), [n], []))       # add abs
        out.append(lambda n: ast.BinOp(n.right, ast.Sub(), n.left))               # swap order
        out.append(lambda n: ast.BinOp(n.left, ast.Add(), n.right))               # + instead of -
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        out.append(lambda n: ast.BinOp(n.left, ast.Sub(), n.right))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "abs" and len(node.args) == 1:
            out.append(lambda n: n.args[0])                                       # drop abs
        if node.func.id in ("min", "max"):
            other = "max" if node.func.id == "min" else "min"
            out.append(lambda n, o=other: ast.Call(ast.Name(o, ast.Load()), n.args, []))
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        for new in _CMP_SWAPS.get(type(node.ops[0]), ()):
            out.append(lambda n, new=new: ast.Compare(n.left, [new()], n.comparators))
    if isinstance(node, ast.BoolOp) and len(node.values) >= 2:
        for i in range(len(node.values)):
            def drop(n, i=i):
                rest = [v for j, v in enumerate(n.values) if j != i]
                return rest[0] if len(rest) == 1 else ast.BoolOp(n.op, rest)
            out.append(drop)
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool) \
            and abs(node.value) <= 12:
        out.append(lambda n: ast.Constant(n.value + 1))
        out.append(lambda n: ast.Constant(n.value - 1))
    return out


def _replace(tree: ast.AST, target_index: int, edit) -> ast.AST:
    tree = copy.deepcopy(tree)
    nodes = list(ast.walk(tree))
    target = nodes[target_index]
    new = edit(target)
    for parent in nodes:
        for field, value in ast.iter_fields(parent):
            if value is target:
                setattr(parent, field, new)
                return ast.fix_missing_locations(tree)
            if isinstance(value, list):
                for k, item in enumerate(value):
                    if item is target:
                        value[k] = new
                        return ast.fix_missing_locations(tree)
    return ast.fix_missing_locations(tree)


def _replace_many(tree: ast.AST, jobs: list) -> ast.AST:
    """Apply several edits at once (targets located before any change)."""
    tree = copy.deepcopy(tree)
    nodes = list(ast.walk(tree))
    targets = [(nodes[i], edit) for i, edit in jobs]
    parents = [(parent, field, value) for parent in nodes for field, value in ast.iter_fields(parent)]
    for target, edit in targets:
        new = edit(target)
        for parent, field, value in parents:
            if value is target:
                setattr(parent, field, new)
            elif isinstance(value, list):
                for k, item in enumerate(value):
                    if item is target:
                        value[k] = new
    return ast.fix_missing_locations(tree)


def _sign_pairs(tree: ast.AST) -> list:
    """Sign handling often goes wrong in pairs (tops AND bottoms): abs() added to two
    subtractions at once, abs() added to every subtraction, abs() removed everywhere."""
    add_abs = lambda n: ast.Call(ast.Name("abs", ast.Load()), [n], [])  # noqa: E731
    subs = [i for i, n in enumerate(ast.walk(tree)) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)]
    abss = [i for i, n in enumerate(ast.walk(tree)) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "abs" and len(n.args) == 1]
    groups = [[(i, add_abs), (j, add_abs)] for a, i in enumerate(subs) for j in subs[a + 1:]]
    if len(subs) > 2:
        groups.append([(i, add_abs) for i in subs])
    if len(abss) > 1:
        groups.append([(i, lambda n: n.args[0]) for i in abss])
    return groups


def _if_conditions(tree: ast.AST) -> list:
    """Edits that make one `if` always or never apply its branch."""
    out = []
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, (ast.If, ast.IfExp)):
            for value in (True, False):
                out.append((i, lambda n, v=value: _set_test(n, v)))
    return out


def _added_guards(tree: ast.AST) -> list:
    """The opposite of dropping a condition: an `if` that is missing one. Adds 'v != 0' or
    'v > 0' to an if-condition, for one argument or a matching pair (both tops, both wholes:
    w1/w2, n1/n2, d1/d2). Live run 24 Nov: Claude's subtraction rule lacked 'both numbers
    have a fraction part' and misfired on a whole number minus a mixed number."""
    try:
        params = [a.arg for a in tree.body[0].args.args if a.arg != "op"]
    except (AttributeError, IndexError):
        return []
    singles = [[v] for v in params]
    pairs = [[a, b] for i, a in enumerate(params) for b in params[i + 1:] if a[:-1] == b[:-1] and a[:-1]]
    out = []
    for i, node in enumerate(ast.walk(tree)):
        if not isinstance(node, (ast.If, ast.IfExp)):
            continue
        for names in singles + pairs:
            for op in (ast.NotEq, ast.Gt):
                def add(n, names=names, op=op):
                    extra = [ast.Compare(ast.Name(v, ast.Load()), [op()], [ast.Constant(0)]) for v in names]
                    n.test = ast.BoolOp(ast.And(), [n.test] + extra)
                    return n
                out.append((i, add))
    return out


def _set_test(node, value):
    node.test = ast.Constant(value)
    return node


def rivals(rule: Rule) -> list[Rule]:
    """Every single-edit variation of an AI rule that passes the sandbox."""
    if not rule.code:
        return []
    try:
        tree = ast.parse(rule.code)
    except SyntaxError:
        return []
    jobs = [[(i, e)] for i, n in enumerate(ast.walk(tree)) for e in _edits(n)] \
        + [[job] for job in _if_conditions(tree)] + _sign_pairs(tree) \
        + [[job] for job in _added_guards(tree)]
    seen, out = {rule.code.strip()}, []
    for group in jobs:
        try:
            code = ast.unparse(_replace(tree, *group[0]) if len(group) == 1 else _replace_many(tree, group))
        except Exception:  # an edit that does not make valid Python is simply skipped
            continue
        if code in seen:
            continue
        seen.add(code)
        try:
            out.append(compile_rule(code, rule.domain, f"{rule.id}_rival{len(out)}", "rival"))
        except UnsafeRule:
            continue
        if len(out) >= MAX_RIVALS:
            break
    return out


def answer(rule: Rule, problem) -> Fraction | None:
    """Like Rule.predict, without the shared cache (rivals are many and short-lived)."""
    try:
        out = rule.fn(*problem.args)
    except (ZeroDivisionError, ArithmeticError, TypeError, ValueError, RecursionError):
        return None
    if out is None or isinstance(out, bool):
        return None
    try:
        return Fraction(out)
    except (TypeError, ValueError):
        return None
