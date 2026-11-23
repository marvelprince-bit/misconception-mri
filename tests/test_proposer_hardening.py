"""Tests for the AI rule-writer hardening: extraction, repair, logging, and the
guarantee that a repair never reveals hidden answers or retries a failed rule."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mri import fakes  # noqa: E402
from mri.engine import Observation  # noqa: E402
from mri.problems import format_answer, full_pool  # noqa: E402
from mri.proposer import extract, propose_and_admit, split_fit_heldout  # noqa: E402
from mri.rules import correct_rule, get_rule  # noqa: E402
from mri.sandbox import UnsafeRule, compile_rule  # noqa: E402

CODE = "def rule(n1, d1, n2, d2):\n    return (n1 + n2, d1 + d2)"


def observations(rule_id, n=8):
    rule = get_rule(rule_id)
    pool = [p for p in full_pool(rule.domain) if rule.predict(p) != correct_rule(rule.domain).predict(p)]
    return [Observation(p, rule.predict(p)) for p in pool[:n]]


class Extraction(unittest.TestCase):
    def test_python_fence(self):
        self.assertEqual(extract(f"DESCRIPTION: x\n```python\n{CODE}\n```")[0], CODE)

    def test_py_fence_and_prose_after(self):
        code, desc = extract(f"Sure!\nDESCRIPTION: adds across\n```py\n{CODE}\n```\nThis explains it.")
        self.assertEqual(code, CODE)
        self.assertEqual(desc, "adds across")

    def test_no_fence_with_text_after(self):
        self.assertEqual(extract(f"DESCRIPTION: x\n{CODE}\nThe student adds tops and bottoms.")[0], CODE)

    def test_picks_the_block_with_the_function(self):
        reply = "```text\nnotes\n```\n```python\n" + CODE + "\n```"
        self.assertEqual(extract(reply)[0], CODE)

    def test_windows_line_endings(self):
        self.assertEqual(extract("```python\r\n" + CODE.replace("\n", "\r\n") + "\r\n```")[0], CODE)


class SandboxStillStrict(unittest.TestCase):
    def test_forbidden_forms_still_rejected(self):
        for bad in ("def rule(n1, d1, n2, d2):\n    return (n1 / d1, 1)",
                    "def rule(n1, d1, n2, d2):\n    t = n1\n    t += n2\n    return (t, d1)",
                    "def rule(n1: int, d1, n2, d2):\n    return (n1, d1)",
                    "import os\ndef rule(n1, d1, n2, d2):\n    return (n1, d1)"):
            with self.assertRaises(UnsafeRule):
                compile_rule(bad, "fractions")


class Repair(unittest.TestCase):
    def setUp(self):
        self.rule = get_rule("frac_add_tops_add_bottoms")
        self.obs = observations(self.rule.id)
        self.args = dict(domain="fractions", observations=self.obs, correct=correct_rule("fractions"),
                         pool=list(full_pool("fractions")), existing=[])

    def test_messy_reply_is_repaired_once(self):
        adm = propose_and_admit(fakes.messy(self.rule.id), **self.args)
        self.assertTrue(adm.admitted, adm.reason)
        self.assertEqual(adm.attempts, 2)

    def test_no_repair_when_switched_off(self):
        adm = propose_and_admit(fakes.messy(self.rule.id), max_repairs=0, **self.args)
        self.assertFalse(adm.admitted)
        self.assertEqual(adm.attempts, 1)

    def test_rule_that_fails_answers_is_never_retried(self):
        calls = []

        def wrong_idea(prompt):
            calls.append(prompt)
            return "DESCRIPTION: keeps the first fraction\n```python\ndef rule(n1, d1, n2, d2):\n    return (n1, d1)\n```"
        adm = propose_and_admit(wrong_idea, **self.args)
        self.assertFalse(adm.admitted)
        self.assertEqual(len(calls), 1)

    def test_repair_prompt_never_contains_hidden_answers(self):
        prompts = []

        def bad_then_good(prompt):
            prompts.append(prompt)
            return "```python\ndef rule(n1: int, d1, n2, d2):\n    return (n1, d1)\n```"
        propose_and_admit(bad_then_good, seed=0, **self.args)
        self.assertEqual(len(prompts), 2)
        _, hidden = split_fit_heldout(self.obs, correct_rule("fractions"), seed=0)
        for o in hidden:
            line = f"{o.problem.text()}  student wrote {format_answer(o.answer)}"
            for p in prompts:
                self.assertNotIn(line, p)

    def test_cheater_still_blocked(self):
        adm = propose_and_admit(fakes.cheat, **self.args)
        self.assertFalse(adm.admitted)
        self.assertEqual(adm.attempts, 1)


class RawLog(unittest.TestCase):
    def test_every_attempt_is_logged_without_keys(self):
        rule = get_rule("frac_add_tops_add_bottoms")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "raw.jsonl")
            os.environ["MRI_RAW_LOG"] = path
            os.environ["GEMINI_API_KEY"] = "SECRET-SHOULD-NOT-APPEAR"
            try:
                propose_and_admit(fakes.messy(rule.id), "fractions", observations(rule.id),
                                  correct_rule("fractions"), list(full_pool("fractions")), [])
                text = Path(path).read_text()
            finally:
                del os.environ["MRI_RAW_LOG"], os.environ["GEMINI_API_KEY"]
        records = [json.loads(line) for line in text.splitlines()]
        self.assertEqual([r["attempt"] for r in records], [1, 2])
        self.assertIn("reply", records[0])
        self.assertNotIn("SECRET", text)


if __name__ == "__main__":
    unittest.main()
