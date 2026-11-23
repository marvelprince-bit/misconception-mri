"""Stand-in 'AI' rule-writers for offline tests. No network, no API key.

oracle : replies with a correct general rule (what a good model should do)
cheat  : replies with a lookup table of the answers it was shown (what the
         admission check exists to catch)
down   : behaves like an AI service that cannot be reached
"""
from __future__ import annotations

import re

from .proposer import ProposerUnavailable

REFERENCE_CODE = {
    "int_ignore_signs_subtract": '''def rule(a, op, b):
    if op == "-":
        return abs(abs(a) - abs(b))
    return a + b''',
    "int_minus_negative_is_minus": '''def rule(a, op, b):
    if op == "+":
        return a + b
    if b < 0:
        return a - abs(b)
    return a - b''',
    "int_plus_negative_is_plus": '''def rule(a, op, b):
    if op == "-":
        return a - b
    if b < 0:
        return a + abs(b)
    return a + b''',
    "int_two_negatives_make_positive": '''def rule(a, op, b):
    if op == "+":
        if a < 0 and b < 0:
            return abs(a) + abs(b)
        return a + b
    return a - b''',
    "int_always_positive": '''def rule(a, op, b):
    if op == "+":
        return abs(a + b)
    return abs(a - b)''',
    "int_sign_of_first": '''def rule(a, op, b):
    if op == "+":
        t = a + b
    else:
        t = a - b
    if a < 0:
        return -abs(t)
    return abs(t)''',
    "int_leading_minus_covers_all": '''def rule(a, op, b):
    if a < 0:
        if op == "+":
            return -(abs(a) + b)
        return -(abs(a) - b)
    if op == "+":
        return a + b
    return a - b''',
    "frac_add_tops_add_bottoms": "def rule(n1, d1, n2, d2):\n    return (n1 + n2, d1 + d2)",
    "frac_add_tops_keep_larger_bottom": "def rule(n1, d1, n2, d2):\n    return (n1 + n2, max(d1, d2))",
    "frac_add_tops_multiply_bottoms": "def rule(n1, d1, n2, d2):\n    return (n1 + n2, d1 * d2)",
    "frac_common_bottom_no_scaling": "def rule(n1, d1, n2, d2):\n    return (n1 + n2, lcm(d1, d2))",
    "frac_multiplies_instead": "def rule(n1, d1, n2, d2):\n    return (n1 * n2, d1 * d2)",
    "frac_add_tops_keep_first_bottom": "def rule(n1, d1, n2, d2):\n    return (n1 + n2, d1)",
    "sub_tops_and_bottoms": """def rule(w1, n1, d1, w2, n2, d2):
    if w1 == 0 and w2 == 0 and d1 != d2:
        return (n1 - n2, d1 - d2)
    return ((w1 * d1 + n1) * d2 - (w2 * d2 + n2) * d1, d1 * d2)""",
    "sub_common_bottom_no_scaling": """def rule(w1, n1, d1, w2, n2, d2):
    if w1 == 0 and w2 == 0:
        return (n1 - n2, lcm(d1, d2))
    return ((w1 * d1 + n1) * d2 - (w2 * d2 + n2) * d1, d1 * d2)""",
    "sub_smaller_from_larger": """def rule(w1, n1, d1, w2, n2, d2):
    L = lcm(d1, d2)
    t = abs(n1 * (L // d1) - n2 * (L // d2))
    return ((w1 - w2) * L + t, L)""",
    "sub_parts_separately": """def rule(w1, n1, d1, w2, n2, d2):
    if w1 > 0 and w2 > 0 and n1 > 0 and n2 > 0 and d1 != d2:
        b = abs(d1 - d2)
        return ((w1 - w2) * b + abs(n1 - n2), b)
    return ((w1 * d1 + n1) * d2 - (w2 * d2 + n2) * d1, d1 * d2)""",
    "mul_whole_scales_both": """def rule(w1, n1, d1, w2, n2, d2):
    if n1 == 0 and w2 == 0:
        return (n2 * w1, d2 * w1)
    if n2 == 0 and w1 == 0:
        return (n1 * w2, d1 * w2)
    return ((w1 * d1 + n1) * (w2 * d2 + n2), d1 * d2)""",
    "mul_whole_times_bottom": """def rule(w1, n1, d1, w2, n2, d2):
    if n1 == 0 and w2 == 0:
        return (n2, d2 * w1)
    if n2 == 0 and w1 == 0:
        return (n1, d1 * w2)
    return ((w1 * d1 + n1) * (w2 * d2 + n2), d1 * d2)""",
    "mul_cross": """def rule(w1, n1, d1, w2, n2, d2):
    if w1 == 0 and w2 == 0:
        return (n1 * d2, d1 * n2)
    return ((w1 * d1 + n1) * (w2 * d2 + n2), d1 * d2)""",
    "div_across_drop_remainder": """def rule(n1, d1, n2, d2):
    if n1 >= n2 and d1 >= d2:
        return (n1 // n2, d1 // d2)
    return (n1 * d2, d1 * n2)""",
    "div_flip_first": "def rule(n1, d1, n2, d2):\n    return (d1 * n2, n1 * d2)",
    "div_flip_both": "def rule(n1, d1, n2, d2):\n    return (d1 * d2, n1 * n2)",
    "div_multiplies_instead": "def rule(n1, d1, n2, d2):\n    return (n1 * n2, d1 * d2)",
}


def oracle(rule_id: str):
    def ask(prompt: str) -> str:
        return f"DESCRIPTION: reference rule {rule_id}\n```python\n{REFERENCE_CODE[rule_id]}\n```"
    return ask


_CORRECT_CODE = {
    "frac_sub": "((w1 * d1 + n1) * d2 - (w2 * d2 + n2) * d1, d1 * d2)",
    "frac_mul": "((w1 * d1 + n1) * (w2 * d2 + n2), d1 * d2)",
    "frac_div": "(n1 * d2, d1 * n2)",
}


def _cheat_general(prompt: str, domain: str) -> str:
    """Memorising cheater for the fraction domains added later: reads the questions
    back with the same parser the tool uses, so no regex per format is needed."""
    from .problems import parse_answer, parse_problem_text
    from .sandbox import SIGNATURES
    names = SIGNATURES[domain]
    body = ""
    for line in prompt.splitlines():
        m = re.match(r"^\s+(.+?)\s+student wrote (.+?)\s+\(correct:", line)
        if not m:
            continue
        problem = parse_problem_text(domain, m.group(1))
        ans = parse_answer(m.group(2))
        cond = " and ".join(f"{n} == {v}" for n, v in zip(names, problem.args))
        body += f"    if {cond}:\n        return ({ans.numerator}, {ans.denominator})\n"
    code = f"def rule({', '.join(names)}):\n{body}    return {_CORRECT_CODE[domain]}"
    return f"DESCRIPTION: memorised answers\n```python\n{code}\n```"


def cheat(prompt: str) -> str:
    """Memorise every answer in the prompt; do the maths correctly everywhere else."""
    sig = re.search(r"Signature: rule\(([^)]*)\)", prompt)
    if sig and sig.group(1).startswith("w1"):
        domain = "frac_sub" if "−" in prompt.split("Signature:")[1].split("\n")[1] else "frac_mul"
        return _cheat_general(prompt, domain)
    if sig and "÷" in prompt:
        return _cheat_general(prompt, "frac_div")
    ints = re.findall(r"^\s+(-?\d+) ([+-]) \(?(-?\d+)\)?\s+student wrote (-?\d+)\s", prompt, re.M)
    fracs = re.findall(r"^\s+(\d+)/(\d+) \+ (\d+)/(\d+)\s+student wrote (-?\d+)(?:/(\d+))?\s", prompt, re.M)
    if ints:
        body = "".join(f"    if a == {a} and op == '{op}' and b == {b}:\n        return {ans}\n"
                       for a, op, b, ans in ints)
        code = f"def rule(a, op, b):\n{body}    if op == '+':\n        return a + b\n    return a - b"
    else:
        body = "".join(
            f"    if n1 == {n1} and d1 == {d1} and n2 == {n2} and d2 == {d2}:\n"
            f"        return ({num}, {den or 1})\n" for n1, d1, n2, d2, num, den in fracs)
        code = f"def rule(n1, d1, n2, d2):\n{body}    return (n1 * d2 + n2 * d1, d1 * d2)"
    return f"DESCRIPTION: memorised answers\n```python\n{code}\n```"


def down(prompt: str) -> str:
    raise ProposerUnavailable("The AI service could not be reached (simulated outage).")


def messy(rule_id: str):
    """A writer with the right idea but sloppy formatting, the way language models often
    reply: a ```py fence, type hints, and an explanation after the code. Type hints are
    rejected by the sandbox. Asked to repair, it returns clean code."""
    clean = oracle(rule_id)

    def ask(prompt: str) -> str:
        if "Your previous reply could not be used" in prompt:
            return clean(prompt)
        code = REFERENCE_CODE[rule_id]
        head, rest = code.split("\n", 1)
        args = head[head.index("(") + 1:head.index(")")].split(", ")
        typed = "def rule(" + ", ".join(a + (": str" if a == "op" else ": int") for a in args) + "):"
        return ("Sure! Here is the procedure.\nDESCRIPTION: the student's procedure\n```py\n"
                + typed + "\n" + rest + "\n```\nThis function captures the pattern in the answers.")
    return ask
