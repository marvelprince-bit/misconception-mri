"""Tests for the parts added in the merge: the three new fraction topics,
mixed-number answers, the MaE answer key, the Claude client, and the
"distinctive prediction" rule for confirming a diagnosis."""
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from mri.engine import Session  # noqa: E402
from mri.fakes import REFERENCE_CODE, cheat  # noqa: E402
from mri.heldout_rules import HELD_OUT_RULES_3  # noqa: E402
from mri.pipeline import run_session  # noqa: E402
from mri.problems import DOMAINS, full_pool, parse_answer, parse_problem_text  # noqa: E402
from mri.proposer import ClaudeProposer, ProposerUnavailable, build_prompt, extract  # noqa: E402
from mri.rules import correct_rule, get_rule, library  # noqa: E402
from mri.sandbox import compile_rule  # noqa: E402
from mri.student import SimulatedStudent  # noqa: E402


class NewTopics(unittest.TestCase):
    def test_every_rule_answers_every_question(self):
        for d in DOMAINS:
            pool = full_pool(d)
            for r in library(d):
                self.assertEqual(sum(r.predict(p) is None for p in pool), 0, r.id)

    def test_mixed_number_answers(self):
        self.assertEqual(parse_answer("2 1/4"), Fraction(9, 4))
        self.assertEqual(parse_answer("-2 1/4"), Fraction(-9, 4))
        self.assertEqual(parse_answer("3/5"), Fraction(3, 5))

    def test_mae_examples_reproduced(self):
        cases = [("frac_sub", "6 − 1 1/4", "5 1/4", "sub_smaller_from_larger"),
                 ("frac_sub", "6 2/3 − 3 1/6", "3 1/3", "sub_parts_separately"),
                 ("frac_mul", "2/3 × 3", "6/9", "mul_whole_scales_both"),
                 ("frac_div", "7/5 ÷ 3/2", "2/2", "div_across_drop_remainder"),
                 ("frac_div", "2/3 ÷ 3/8", "9/16", "div_flip_first")]
        for d, q, a, rid in cases:
            self.assertEqual(get_rule(rid).predict(parse_problem_text(d, q)), parse_answer(a), (q, rid))

    def test_mae14_trap_is_a_correct_answer(self):
        p = parse_problem_text("frac_div", "6/8 ÷ 2/8")
        self.assertEqual(get_rule("div_across_drop_remainder").predict(p), correct_rule("frac_div").predict(p))

    def test_known_rules_found_in_new_topics(self):
        for d in ("frac_sub", "frac_mul", "frac_div"):
            for r in library(d):
                log = run_session(Session(d, seed=1), SimulatedStudent(r, seed=1))
                self.assertEqual(log.status.rule.id if log.status.rule else None, r.id, (d, r.id))


class Predictions(unittest.TestCase):
    def test_diagnosis_rests_on_predictions_that_differ_from_the_correct_answer(self):
        for rid in ("div_across_drop_remainder", "sub_smaller_from_larger", "int_leading_minus_covers_all"):
            rule = get_rule(rid)
            session = Session(rule.domain, seed=7)
            log = run_session(session, SimulatedStudent(rule, seed=7))
            self.assertEqual(log.status.state, "diagnosed")
            counted = [o for o in session.observations if o.purpose == "confirm" and o.predicted_rule == rid
                       and o.answer == o.predicted and session.correct.predict(o.problem) != o.predicted]
            self.assertGreaterEqual(len(counted), 2, rid)


class AIWriter(unittest.TestCase):
    def test_reference_code_matches_library_everywhere(self):
        for d in DOMAINS:
            pool = full_pool(d)
            for r in library(d):
                if r.is_correct:
                    continue
                ai = compile_rule(REFERENCE_CODE[r.id], d)
                self.assertTrue(all(ai.predict(p) == r.predict(p) for p in pool), r.id)

    def test_cheater_memorises_in_new_topics(self):
        for d in ("frac_sub", "frac_mul", "frac_div"):
            wrong = [r for r in library(d) if not r.is_correct][0]
            obs = [type("O", (), {"problem": p, "answer": wrong.predict(p)})() for p in full_pool(d)[:4]]
            code, _ = extract(cheat(build_prompt(d, obs, correct_rule(d))))
            ai = compile_rule(code, d)
            self.assertTrue(all(ai.predict(o.problem) == o.answer for o in obs))

    def test_claude_without_key_fails_safely(self):
        with self.assertRaises(ProposerUnavailable):
            ClaudeProposer(api_key="")("hello")


class HeldOutSet3(unittest.TestCase):
    def test_set3_rules_are_valid_and_unseen(self):
        for h in HELD_OUT_RULES_3:
            pool = full_pool(h.domain)
            self.assertEqual(sum(h.predict(p) is None for p in pool), 0, h.id)
            for r in library(h.domain):
                self.assertFalse(all(r.predict(p) == h.predict(p) for p in pool), (h.id, r.id))


class ExternalKey(unittest.TestCase):
    def test_mae_file_loads(self):
        data = json.loads((ROOT / "data" / "mae_examples.json").read_text())
        self.assertEqual(len(data["items"]), 40)


if __name__ == "__main__":
    unittest.main()
