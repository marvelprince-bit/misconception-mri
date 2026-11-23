"""AI rule-writer and the admission check.

When no known rule explains a student's answers, an AI model is asked to write a
new candidate rule as code. An AI can 'cheat' by writing a rule that simply
memorises the answers it was shown. So the tool hides some of the student's wrong
answers from the AI. A rule is admitted only if it also predicts those hidden
answers. A memorised lookup table cannot do that.
"""
from __future__ import annotations

import json
import os
import random
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .engine import Observation
from .problems import Problem, format_answer
from .rules import Rule
from .sandbox import SIGNATURES, UnsafeRule, compile_rule

DEFAULT_MODEL = "gemini-3.8-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class ProposerUnavailable(Exception):
    """The AI service could not be reached or returned nothing usable."""


@dataclass
class Admission:
    admitted: bool
    reason: str
    rule: Rule | None = None
    fit_hits: int = 0
    fit_total: int = 0
    held_hits: int = 0
    held_total: int = 0
    duplicate_of: str | None = None
    attempts: int = 1


def split_fit_heldout(observations: list[Observation], correct: Rule, seed: int = 0,
                      ) -> tuple[list[Observation], list[Observation]] | None:
    """Hide some WRONG answers from the AI. Returns (shown, hidden), or None if too few.

    Hidden answers are always wrong answers: a rule cannot predict them by simply
    doing the maths correctly.
    """
    wrong = [o for o in observations if correct.predict(o.problem) != o.answer]
    if len(wrong) < 3:
        return None
    k = 2 if len(wrong) >= 5 else 1
    hidden = random.Random(seed).sample(wrong, k)
    shown = [o for o in observations if o not in hidden]
    return shown, hidden


# The CORRECT method for each topic, written in the allowed syntax. It is shown to the
# model only to illustrate the format; it contains no misconception.
SYNTAX_EXAMPLE = {
    "integers": "def rule(a, op, b):\n    if op == '+':\n        return a + b\n    return a - b",
    "fractions": "def rule(n1, d1, n2, d2):\n    top = n1 * d2 + n2 * d1\n    return (top, d1 * d2)",
    "frac_sub": "def rule(w1, n1, d1, w2, n2, d2):\n    first = w1 * d1 + n1\n    second = w2 * d2 + n2\n"
                "    return (first * d2 - second * d1, d1 * d2)",
    "frac_mul": "def rule(w1, n1, d1, w2, n2, d2):\n    first = w1 * d1 + n1\n    second = w2 * d2 + n2\n"
                "    return (first * second, d1 * d2)",
    "frac_div": "def rule(n1, d1, n2, d2):\n    return (n1 * d2, d1 * n2)",
}

FORMAT_RULES = (
    "Code rules (code that breaks any of these is rejected before it runs):\n"
    "- Exactly one function named rule with exactly the arguments above. No type hints.\n"
    "- Allowed: + - * // % (whole-number division is //), comparisons, and/or/not, if/elif/else,\n"
    "  'name = value' assignments, and the functions abs, min, max, gcd, lcm (already available).\n"
    "- Not allowed: / (use //), +=, -= or *=, **, import, math.gcd or any dot, loops, lists,\n"
    "  decimals, print, Fraction, comments are fine but no other text inside the code.\n"
)


def _contract(domain: str) -> str:
    if domain == "integers":
        return ("def rule(a, op, b):  # a and b are whole numbers, op is '+' or '-'\n"
                "    return <one whole number>")
    if domain == "fractions":
        return ("def rule(n1, d1, n2, d2):  # the question is n1/d1 + n2/d2\n"
                "    return (top, bottom)  # a tuple of two whole numbers; it need not be simplified")
    if domain == "frac_div":
        return ("def rule(n1, d1, n2, d2):  # the question is n1/d1 ÷ n2/d2\n"
                "    return (top, bottom)  # a tuple of two whole numbers; it need not be simplified")
    op = "−" if domain == "frac_sub" else "×"
    return (f"def rule(w1, n1, d1, w2, n2, d2):  # the question is (w1 + n1/d1) {op} (w2 + n2/d2)\n"
            "    # a whole number k is given as w=k, n=0, d=1; a plain fraction as w=0\n"
            "    return (top, bottom)  # a tuple of two whole numbers; it need not be simplified")


def build_prompt(domain: str, shown: list[Observation], correct: Rule) -> str:
    args = ", ".join(SIGNATURES[domain])
    lines = [
        f"  {o.problem.text()}  student wrote {format_answer(o.answer)}"
        f"  (correct: {format_answer(correct.predict(o.problem))})"
        for o in shown
    ]
    return (
        "A student is answering maths questions. Some answers are wrong in a consistent way.\n"
        "Write ONE general procedure the student may be following, as a Python function.\n\n"
        f"Signature: rule({args})\n{_contract(domain)}\n\n"
        + FORMAT_RULES +
        "\nExample of the allowed format. This example is the CORRECT method, shown only for syntax;\n"
        "your function must instead reproduce the student's answers, including the wrong ones:\n"
        f"```python\n{SYNTAX_EXAMPLE[domain]}\n```\n\n"
        "The rule must work for ANY question of this type, not just these. Do not list the\n"
        "questions one by one: the rule will be tested on answers you have not seen, and a\n"
        "memorised table will fail.\n\n"
        "Student's answers:\n" + "\n".join(lines) + "\n\n"
        "Reply in exactly this form and nothing else:\n"
        "DESCRIPTION: <one line in plain English>\n"
        "```python\n<the function>\n```"
    )


def repair_prompt(original: str, code: str, reason: str) -> str:
    """One correction request after a format or safety rejection. Built only from the
    original prompt (shown answers) and the rejection message: hidden answers never appear."""
    return (
        original + "\n\nYour previous reply could not be used.\n"
        f"Reason: {reason}\n"
        f"Your previous code was:\n```python\n{code}\n```\n"
        "Rewrite it so it follows the code rules exactly. Keep the same idea if it fits the "
        "student's answers. Reply in the same form as before."
    )


def extract(reply: str) -> tuple[str, str]:
    """Pull (code, description) out of the model's reply.

    Accepts ```python, ```py or bare ``` fences and picks the first block that defines
    rule. With no fence, takes the function itself: the 'def rule' line and the indented
    lines under it, so any explanation after the function is dropped.
    """
    reply = reply.replace("\r\n", "\n")
    code = ""
    for block in re.findall(r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\n(.*?)```", reply, re.S):
        if "def rule" in block:
            code = block
            break
    source = code or reply
    start = source.find("def rule")
    if start >= 0:
        kept = []
        for k, line in enumerate(source[start:].split("\n")):
            if k > 0 and line.strip() and not line[:1].isspace():
                break  # first unindented line after the function: stop
            kept.append(line)
        code = "\n".join(kept)
    code = code.strip("\n").rstrip()
    desc = re.search(r"DESCRIPTION:\s*(.+)", reply)
    return code, (desc.group(1).strip()[:200] if desc else "")


class GeminiProposer:
    """Asks a Gemini model for a rule. Needs GEMINI_API_KEY in the environment."""

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("MRI_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        if not self.api_key:
            raise ProposerUnavailable("No GEMINI_API_KEY is set.")
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }).encode()
        request = urllib.request.Request(
            API_URL.format(model=self.model), data=body, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as exc:
            raise ProposerUnavailable(f"The AI service returned HTTP {exc.code}.") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProposerUnavailable(f"The AI service could not be reached ({type(exc).__name__}).") from None
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProposerUnavailable("The AI service returned an empty or unreadable reply.") from None


class ClaudeProposer:
    """Asks a Claude model for a rule. Needs ANTHROPIC_API_KEY in the environment."""

    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or os.environ.get("MRI_CLAUDE_MODEL", "claude-sonnet-5-5")
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        if not self.api_key:
            raise ProposerUnavailable("No ANTHROPIC_API_KEY is set.")
        body = json.dumps({
            "model": self.model, "max_tokens": 1200, "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        request = urllib.request.Request(
            self.URL, data=body, method="POST",
            headers={"Content-Type": "application/json", "x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
            return "".join(part.get("text", "") for part in data["content"] if part.get("type") == "text")
        except urllib.error.HTTPError as exc:
            raise ProposerUnavailable(f"The AI service returned HTTP {exc.code}.") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProposerUnavailable(f"The AI service could not be reached ({type(exc).__name__}).") from None
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProposerUnavailable("The AI service returned an empty or unreadable reply.") from None


def make_proposer(name: str):
    """'gemini' or 'claude'."""
    return {"gemini": GeminiProposer, "claude": ClaudeProposer}[name]()


def admit(code: str, domain: str, shown: list[Observation], hidden: list[Observation],
          pool: list[Problem], existing: list[Rule], gate: bool = True,
          rule_id: str = "ai_rule", label: str = "") -> Admission:
    """Decide whether an AI-written rule may join the candidates.

    gate=True  -> must also predict the hidden answers (the real check)
    gate=False -> only has to match the answers it was shown (used to measure what the gate adds)
    """
    try:
        rule = compile_rule(code, domain, rule_id, label)
    except UnsafeRule as exc:
        return Admission(False, f"Rejected: unsafe or malformed code. {exc}")

    broken = sum(1 for p in pool if rule.predict(p) is None)
    if broken:
        return Admission(False, f"Rejected: the rule gives no answer on {broken} of {len(pool)} questions.")

    fit_hits = sum(1 for o in shown if rule.predict(o.problem) == o.answer)
    held_hits = sum(1 for o in hidden if rule.predict(o.problem) == o.answer)
    counts = dict(fit_hits=fit_hits, fit_total=len(shown), held_hits=held_hits, held_total=len(hidden))
    if fit_hits < len(shown):
        return Admission(False, f"Rejected: explains only {fit_hits} of {len(shown)} answers it was shown.",
                         **counts)
    if gate and held_hits < len(hidden):
        return Admission(False, f"Rejected: predicted only {held_hits} of {len(hidden)} answers it never saw. "
                                "It fits the examples but does not generalise.", **counts)
    for other in existing:
        if all(other.predict(p) == rule.predict(p) for p in pool):
            return Admission(False, f"Not added: identical to the known rule '{other.id}'.",
                             duplicate_of=other.id, **counts)
    checked = (f"predicted {held_hits} of {len(hidden)} hidden answers" if gate
               else "hidden-answer check switched off")
    return Admission(True, f"Admitted: explains all {len(shown)} shown answers and {checked}.", rule, **counts)


REPAIRABLE = ("Rejected: unsafe or malformed code.", "Rejected: the rule gives no answer")


def _log_exchange(record: dict) -> None:
    """Append one AI exchange to the file named in MRI_RAW_LOG, if set. Never contains keys."""
    path = os.environ.get("MRI_RAW_LOG")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def propose_and_admit(ask, domain: str, observations: list[Observation], correct: Rule,
                      pool: list[Problem], existing: list[Rule], gate: bool = True,
                      seed: int = 0, rule_id: str = "ai_rule", max_repairs: int | None = None) -> Admission:
    """Full step: hide some answers, ask the AI, check its rule. `ask` is prompt -> reply text.

    If the code is rejected for format or safety reasons, or gives no answer on some
    questions, the AI gets ONE chance to fix it, told only the rejection message. A rule
    that fails the answers (shown or hidden) is never retried: retrying until something
    passes by luck would defeat the hidden-answer check.
    """
    parts = split_fit_heldout(observations, correct, seed)
    if parts is None:
        return Admission(False, "Not attempted: fewer than 3 wrong answers, too little to learn a rule from.")
    shown, hidden = parts
    if max_repairs is None:
        max_repairs = int(os.environ.get("MRI_MAX_REPAIRS", "1"))
    prompt = build_prompt(domain, shown, correct)
    attempts = 0
    while True:
        attempts += 1
        reply = ask(prompt)  # may raise ProposerUnavailable
        code, description = extract(reply)
        label = f"AI-written rule: {description}" if description else "AI-written rule (see code)."
        result = admit(code, domain, shown, hidden, pool, existing, gate, rule_id, label)
        result.attempts = attempts
        _log_exchange({"domain": domain, "attempt": attempts, "prompt": prompt, "reply": reply,
                       "extracted_code": code, "admitted": result.admitted, "reason": result.reason,
                       "shown": len(shown), "hidden": len(hidden), "gate": gate})
        if result.admitted or attempts > max_repairs or not result.reason.startswith(REPAIRABLE):
            return result
        prompt = repair_prompt(build_prompt(domain, shown, correct), code, result.reason)
