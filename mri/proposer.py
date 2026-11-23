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


def build_prompt(domain: str, shown: list[Observation], correct: Rule) -> str:
    args = ", ".join(SIGNATURES[domain])
    if domain == "integers":
        contract = ("def rule(a, op, b):  # a and b are whole numbers, op is '+' or '-'\n"
                    "    ...\n    return <whole number>")
    elif domain == "fractions":
        contract = ("def rule(n1, d1, n2, d2):  # the question is n1/d1 + n2/d2\n"
                    "    ...\n    return (top, bottom)  # two whole numbers")
    elif domain == "frac_div":
        contract = ("def rule(n1, d1, n2, d2):  # the question is n1/d1 ÷ n2/d2\n"
                    "    ...\n    return (top, bottom)  # two whole numbers")
    else:
        op = "−" if domain == "frac_sub" else "×"
        contract = (f"def rule(w1, n1, d1, w2, n2, d2):  # the question is (w1 + n1/d1) {op} (w2 + n2/d2)\n"
                    "    # a whole number k is given as w=k, n=0, d=1; a plain fraction as w=0\n"
                    "    ...\n    return (top, bottom)  # two whole numbers")
    lines = [
        f"  {o.problem.text()}  student wrote {format_answer(o.answer)}"
        f"  (correct: {format_answer(correct.predict(o.problem))})"
        for o in shown
    ]
    return (
        "A student is answering maths questions. Some answers are wrong in a consistent way.\n"
        "Write ONE general procedure the student may be following, as a Python function.\n\n"
        f"Signature: rule({args})\n{contract}\n\n"
        "Strict limits: plain arithmetic only (+, -, *, //, %), comparisons, if/else, simple\n"
        "assignments, and abs, min, max, gcd, lcm. No imports, loops, lists, or strings other\n"
        "than '+' and '-'. The rule must work for ANY question of this type, not just these.\n"
        "Do not list the questions one by one: the rule will be tested on answers you have\n"
        "not seen, and a memorised table will fail.\n\n"
        "Student's answers:\n" + "\n".join(lines) + "\n\n"
        "Reply with a one-line plain-English description starting with 'DESCRIPTION:' and then\n"
        "the function in a ```python code block. Nothing else."
    )


def extract(reply: str) -> tuple[str, str]:
    """Pull (code, description) out of the model's reply."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", reply, re.S)
    code = (match.group(1) if match else reply).strip()
    start = code.find("def rule")
    if start > 0:
        code = code[start:]
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


def propose_and_admit(ask, domain: str, observations: list[Observation], correct: Rule,
                      pool: list[Problem], existing: list[Rule], gate: bool = True,
                      seed: int = 0, rule_id: str = "ai_rule") -> Admission:
    """Full step: hide some answers, ask the AI, check its rule. `ask` is prompt -> reply text."""
    parts = split_fit_heldout(observations, correct, seed)
    if parts is None:
        return Admission(False, "Not attempted: fewer than 3 wrong answers, too little to learn a rule from.")
    shown, hidden = parts
    reply = ask(build_prompt(domain, shown, correct))  # may raise ProposerUnavailable
    code, description = extract(reply)
    label = f"AI-written rule: {description}" if description else "AI-written rule (see code)."
    return admit(code, domain, shown, hidden, pool, existing, gate, rule_id, label)
