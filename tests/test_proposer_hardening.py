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
from mri.problems import format_answer, full_pool, kind  # noqa: E402
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


class ClaudeRequest(unittest.TestCase):
    """The request must suit Claude Sonnet 5.5: no sampling parameters, room for thinking."""

    def _call(self, reply_json):
        import io
        from unittest import mock
        from mri.proposer import ClaudeProposer
        sent = {}

        def fake_urlopen(request, timeout=None):
            sent["body"] = json.loads(request.data.decode())
            sent["headers"] = dict(request.header_items())
            return io.BytesIO(json.dumps(reply_json).encode())

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            out = ClaudeProposer(api_key="test-key")("hello")
        return out, sent

    def test_no_sampling_parameters_and_enough_tokens(self):
        out, sent = self._call({"content": [{"type": "thinking", "thinking": "..."},
                                            {"type": "text", "text": "DESCRIPTION: x"}],
                                "stop_reason": "end_turn"})
        self.assertEqual(out, "DESCRIPTION: x")
        for k in ("temperature", "top_p", "top_k"):
            self.assertNotIn(k, sent["body"])
        self.assertGreaterEqual(sent["body"]["max_tokens"], 4000)
        self.assertEqual(sent["body"]["model"], "claude-sonnet-5-5")

    def test_reply_with_only_thinking_is_reported_clearly(self):
        from mri.proposer import ProposerUnavailable
        with self.assertRaises(ProposerUnavailable) as ctx:
            self._call({"content": [{"type": "thinking", "thinking": "..."}], "stop_reason": "max_tokens"})
        self.assertIn("max_tokens", str(ctx.exception))


class ShapeCheckForAIRules(unittest.TestCase):
    """Regression for the live Claude finding: an AI rule that copied int_sign_of_first only
    on the kinds where it saw wrong answers was diagnosed, though it is wrong on (-3) - (-5)."""

    def _sessions(self, writer, mode, seeds=8, holdout="cross_kind", hidden_id="int_sign_of_first",
                  with_questions=False):
        import mri.proposer as proposer
        from mri.engine import Session
        from mri.pipeline import run_session
        from mri.rules import library
        from mri.student import SimulatedStudent
        hidden = get_rule(hidden_id)
        rules = [r for r in library(hidden.domain) if r.id != hidden.id]
        out = []
        saved, proposer.HOLDOUT = proposer.HOLDOUT, holdout
        try:
            for seed in range(seeds):
                s = Session(hidden.domain, rules=rules, seed=seed, diagnosis_needs_all_kinds=mode)
                log = run_session(s, SimulatedStudent(hidden, 0.0, seed=seed), ask=writer(hidden.id))
                st = log.status
                wrong = (st.state in ("diagnosed", "no_misconception") and
                         any(st.rule.predict(p) != hidden.predict(p) for p in s.pool))
                right = st.state == "diagnosed" and not wrong
                out.append((wrong, right, log.questions_asked) if with_questions else (wrong, right))
        finally:
            proposer.HOLDOUT = saved
        return out

    def test_failure_reproduced_with_both_safeguards_off(self):
        self.assertGreater(sum(w for w, _ in self._sessions(fakes.partial, "none", holdout="random")), 0)

    def test_shape_check_alone_stops_it(self):
        self.assertEqual(sum(w for w, _ in self._sessions(fakes.partial, "ai", holdout="random")), 0)

    def test_partial_ai_rule_never_named_with_the_check(self):
        self.assertEqual(sum(w for w, _ in self._sessions(fakes.partial, "ai")), 0)

    def test_correct_ai_rule_still_confirmed_with_the_check(self):
        self.assertGreaterEqual(sum(r for _, r in self._sessions(fakes.oracle, "ai")), 6)

    def test_setting_is_validated(self):
        from mri.engine import Session
        with self.assertRaises(ValueError):
            Session("integers", diagnosis_needs_all_kinds="sometimes")


class Efficiency(unittest.TestCase):
    """Regression for the live Claude run on int_sign_of_first: admitted but wrong, then
    20 questions to reach 'no diagnosis'. Baseline before the change (stand-in writer that
    reproduces it, 20 seeds): mean 18.15 questions, max 21, never a false diagnosis."""

    def test_sign_of_first_resolved_safely_in_fewer_questions(self):
        runs = ShapeCheckForAIRules()._sessions(fakes.partial, "ai", seeds=20, with_questions=True)
        self.assertEqual(sum(w for w, _, _ in runs), 0)
        qs = [q for _, _, q in runs]
        self.assertLess(sum(qs) / len(qs), 16.0)
        self.assertLess(max(qs), 20)

    def test_exploration_collects_wrong_answers_from_more_than_one_kind(self):
        from mri.engine import Session
        from mri.pipeline import MAX_EXPLORE_QUESTIONS, WRONG_ANSWERS_FOR_AI
        from mri.problems import parse_problem_text
        from mri.rules import library
        hidden = get_rule("int_sign_of_first")
        s = Session("integers", rules=[r for r in library("integers") if r.id != hidden.id], seed=0)
        for q in ("8 + (-9)", "3 + (-6)"):  # two wrong answers, both of one shape
            p = parse_problem_text("integers", q)
            s.record(p, hidden.predict(p))
        for left in range(MAX_EXPLORE_QUESTIONS, 0, -1):
            q = s.explore_question(budget_left=left, target=WRONG_ANSWERS_FOR_AI)
            s.record(q.problem, hidden.predict(q.problem))
        wrong_kinds = {kind(o.problem) for o in s.observations
                       if s.correct.predict(o.problem) != o.answer}
        self.assertGreaterEqual(len(wrong_kinds), 2)

    def test_single_shape_rule_still_gets_enough_wrong_answers(self):
        runs = ShapeCheckForAIRules()._sessions(fakes.oracle, "ai", seeds=5, hidden_id="mul_whole_scales_both")
        self.assertEqual(sum(r for _, r in runs), 5)

    def test_good_ai_rule_still_confirmed(self):
        runs = ShapeCheckForAIRules()._sessions(fakes.oracle, "ai", seeds=5)
        self.assertEqual(sum(r for _, r in runs), 5)
