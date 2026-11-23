"""Run with:  python -m unittest discover -s tests -v"""
import os
import sys
import unittest
from fractions import Fraction
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mri import fakes
from mri.engine import UNKNOWN, Session
from mri.pipeline import run_session
from mri.problems import DOMAINS, Problem, full_pool, kind, parse_answer, worksheet_pool
from mri.proposer import GeminiProposer, ProposerUnavailable, admit, extract, split_fit_heldout
from mri.rules import correct_rule, get_rule, library
from mri.sandbox import UnsafeRule, compile_rule
from mri.student import RandomGuesser, SimulatedStudent


def P(a, op, b):
    return Problem("integers", (a, op, b))


def F(n1, d1, n2, d2):
    return Problem("fractions", (n1, d1, n2, d2))


class Rules(unittest.TestCase):
    def test_examples_in_labels_are_true(self):
        cases = [
            ("int_ignore_signs_subtract", P(3, "-", 5), 2),
            ("int_minus_negative_is_minus", P(4, "-", -3), 1),
            ("int_plus_negative_is_plus", P(4, "+", -3), 7),
            ("int_two_negatives_make_positive", P(-3, "+", -5), 8),
            ("int_always_positive", P(3, "-", 5), 2),
            ("int_sign_of_first", P(-3, "+", 5), -2),
            ("int_leading_minus_covers_all", P(-3, "+", 5), -8),
            ("frac_add_tops_add_bottoms", F(1, 2, 1, 3), Fraction(2, 5)),
            ("frac_add_tops_keep_larger_bottom", F(1, 2, 1, 3), Fraction(2, 3)),
            ("frac_add_tops_multiply_bottoms", F(1, 2, 1, 3), Fraction(2, 6)),
            ("frac_common_bottom_no_scaling", F(1, 4, 1, 6), Fraction(2, 12)),
            ("frac_multiplies_instead", F(1, 2, 1, 3), Fraction(1, 6)),
            ("frac_add_tops_keep_first_bottom", F(1, 2, 1, 3), Fraction(2, 2)),
        ]
        for rule_id, problem, expected in cases:
            self.assertEqual(get_rule(rule_id).predict(problem), expected, rule_id)

    def test_correct_rules(self):
        self.assertEqual(correct_rule("integers").predict(P(-3, "-", -5)), 2)
        self.assertEqual(correct_rule("fractions").predict(F(1, 2, 1, 3)), Fraction(5, 6))

    def test_every_rule_answers_every_question_and_no_two_rules_are_the_same(self):
        for domain in DOMAINS:
            pool, rules = full_pool(domain), library(domain)
            for r in rules:
                self.assertTrue(all(r.predict(p) is not None for p in pool), r.id)
            for i, a in enumerate(rules):
                for b in rules[i + 1:]:
                    self.assertTrue(any(a.predict(p) != b.predict(p) for p in pool), (a.id, b.id))

    def test_reference_code_matches_library(self):
        for rule_id, code in fakes.REFERENCE_CODE.items():
            rule = get_rule(rule_id)
            compiled = compile_rule(code, rule.domain)
            for p in full_pool(rule.domain):
                self.assertEqual(compiled.predict(p), rule.predict(p), (rule_id, p.text()))


class Answers(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_answer(" -8 "), -8)
        self.assertEqual(parse_answer("2/4"), Fraction(1, 2))
        self.assertEqual(parse_answer("\u22123"), -3)  # typographic minus sign

    def test_bad_input_gives_a_readable_error(self):
        for bad in ("", "abc", "3/0", "1/2/3"):
            with self.assertRaises(ValueError):
                parse_answer(bad)


class Engine(unittest.TestCase):
    def test_finds_every_known_rule(self):
        for domain in DOMAINS:
            for rule in library(domain):
                for seed in range(5):
                    log = run_session(Session(domain, seed=seed), SimulatedStudent(rule, seed=seed))
                    self.assertEqual(log.status.rule.id, rule.id, (rule.id, seed))
                    self.assertTrue(log.status.confirmed)

    def test_all_clear_only_after_every_kind_is_tested(self):
        for domain in DOMAINS:
            session = Session(domain, seed=1)
            log = run_session(session, SimulatedStudent(correct_rule(domain), seed=1))
            self.assertEqual(log.status.state, "no_misconception")
            self.assertEqual(log.status.kinds_tested, log.status.kinds_total)

    def test_diagnosis_needs_predictions_made_in_advance(self):
        session = Session("integers", seed=2)
        run_session(session, SimulatedStudent(get_rule("int_sign_of_first"), seed=2))
        hits = [o for o in session.observations if o.purpose == "confirm" and o.answer == o.predicted]
        self.assertGreaterEqual(len(hits), 2)

    def test_right_answers_wrong_rule(self):
        """A 5/5 worksheet can hide a wrong rule; the tool then exposes it."""
        rule = get_rule("int_always_positive")
        sheet = worksheet_pool("integers")[:5]
        session = Session("integers", seed=3)
        student = SimulatedStudent(rule, seed=3)
        for p in sheet:
            session.record(p, student.answer(p))
        report = session.trap_report()
        self.assertTrue(report["all_correct"] and report["trap_possible"])
        self.assertIn(rule, report["hidden_rules"])
        log = run_session(session, student)
        self.assertEqual(log.status.rule.id, rule.id)

    def test_two_misses_on_one_shape_strike_a_rule_out(self):
        session = Session("integers", seed=4)
        session.record(P(4, "-", -3), Fraction(1))   # correct would be 7
        self.assertGreater(session.posterior()["int_correct"], 0)
        session.record(P(6, "-", -2), Fraction(4))   # correct would be 8: same shape, missed again
        self.assertEqual(session.posterior()["int_correct"], 0)

    def test_unknown_rule_gives_no_diagnosis(self):
        hidden = get_rule("int_sign_of_first")
        rules = [r for r in library("integers") if r.id != hidden.id]
        for seed in range(10):
            log = run_session(Session("integers", rules=rules, seed=seed), SimulatedStudent(hidden, seed=seed))
            self.assertIn(log.status.state, ("abstain", "inconclusive"), seed)

    def test_guessing_student_is_rarely_given_a_diagnosis(self):
        named = 0
        for seed in range(40):
            log = run_session(Session("fractions", seed=seed), RandomGuesser(library("fractions"), seed=seed))
            named += log.status.state in ("diagnosed", "no_misconception")
        self.assertLessEqual(named, 4)

    def test_disagreement_needs_fewer_questions_than_random(self):
        def mean_questions(policy):
            total = 0
            for rule in library("integers"):
                for seed in range(20):
                    log = run_session(Session("integers", policy=policy, seed=seed), SimulatedStudent(rule, seed=seed))
                    total += log.questions_asked
            return total / (20 * len(library("integers")))
        self.assertLess(mean_questions("disagreement"), mean_questions("random"))

    def test_fix_questions_are_ones_the_wrong_rule_gets_wrong(self):
        session = Session("fractions", seed=5)
        rule = get_rule("frac_add_tops_add_bottoms")
        for p in session.fix_questions(rule, 5):
            self.assertNotEqual(rule.predict(p), session.correct.predict(p))

    def test_kinds(self):
        self.assertEqual(len({kind(p) for p in full_pool("integers")}), 8)
        self.assertEqual(len({kind(p) for p in full_pool("fractions")}), 7)


class Sandbox(unittest.TestCase):
    def test_rejects_unsafe_code(self):
        bad = {
            "import": "import os\ndef rule(a, op, b):\n    return a",
            "loop": "def rule(a, op, b):\n    while True:\n        a = a + 1\n    return a",
            "attribute": "def rule(a, op, b):\n    return a.real",
            "builtin": "def rule(a, op, b):\n    return open('x')",
            "power": "def rule(a, op, b):\n    return a ** b",
            "big number": "def rule(a, op, b):\n    return 99999999",
            "wrong name": "def f(a, op, b):\n    return a",
            "wrong args": "def rule(x, y):\n    return x",
            "recursion": "def rule(a, op, b):\n    return rule(a, op, b)",
            "lambda": "def rule(a, op, b):\n    return (lambda: a)()",
            "list": "def rule(a, op, b):\n    return [a][0]",
            "string": "def rule(a, op, b):\n    return '__import__'",
            "float": "def rule(a, op, b):\n    return a * 0.5",
            "two functions": "def rule(a, op, b):\n    return a\ndef g():\n    return 1",
            "not code": "this is not python",
            "default arg": "def rule(a, op, b=open):\n    return a",
        }
        for name, code in bad.items():
            with self.assertRaises(UnsafeRule, msg=name):
                compile_rule(code, "integers")

    def test_very_long_or_deeply_nested_code_is_rejected_not_crashed(self):
        deep = "def rule(a, op, b):\n    return " + "(" * 1500 + "a" + ")" * 1500
        chain = "def rule(a, op, b):\n    return " + "+".join(["a"] * 1200)
        for code in (deep, chain, "x" * 10_000):
            with self.assertRaises(UnsafeRule):
                compile_rule(code, "integers")

    def test_rule_that_crashes_gives_no_answer_instead_of_an_error(self):
        rule = compile_rule("def rule(a, op, b):\n    return a // (b - b)", "integers")
        self.assertIsNone(rule.predict(P(3, "+", 4)))

    def test_fraction_rules_must_return_two_whole_numbers(self):
        rule = compile_rule("def rule(n1, d1, n2, d2):\n    return n1", "fractions")
        self.assertIsNone(rule.predict(F(1, 2, 1, 3)))
        zero = compile_rule("def rule(n1, d1, n2, d2):\n    return (n1, d1 - d1)", "fractions")
        self.assertIsNone(zero.predict(F(1, 2, 1, 3)))


class AIRuleWriter(unittest.TestCase):
    def setUp(self):
        self.hidden = get_rule("int_leading_minus_covers_all")
        self.rules = [r for r in library("integers") if r.id != self.hidden.id]

    def run_with(self, ask, gate=True, seed=0):
        session = Session("integers", rules=self.rules, seed=seed)
        return run_session(session, SimulatedStudent(self.hidden, seed=seed), ask=ask, gate=gate)

    def test_good_rule_is_admitted_then_confirmed(self):
        log = self.run_with(fakes.oracle(self.hidden.id))
        self.assertTrue(log.admission.admitted)
        self.assertEqual(log.status.state, "diagnosed")
        self.assertEqual(log.status.rule.source, "ai")
        self.assertTrue(log.status.confirmed)

    def test_memorised_answers_are_rejected_by_the_hidden_answer_check(self):
        log = self.run_with(fakes.cheat)
        self.assertFalse(log.admission.admitted)
        self.assertIn("never saw", log.admission.reason)
        self.assertIn(log.status.state, ("abstain", "inconclusive"))

    def test_without_the_check_memorised_answers_get_in(self):
        log = self.run_with(fakes.cheat, gate=False)
        self.assertTrue(log.admission.admitted)

    def test_hidden_answers_are_never_shown_to_the_ai(self):
        session = Session("integers", rules=self.rules, seed=0)
        seen = {}

        def spy(prompt):
            seen["prompt"] = prompt
            seen["answers_so_far"] = list(session.observations)
            return fakes.oracle(self.hidden.id)(prompt)

        run_session(session, SimulatedStudent(self.hidden, seed=0), ask=spy)
        shown, hidden = split_fit_heldout(seen["answers_so_far"], session.correct, seed=0)
        self.assertTrue(hidden)
        for o in hidden:
            self.assertNotEqual(session.correct.predict(o.problem), o.answer)  # hidden ones are wrong answers
            self.assertNotIn(f"  {o.problem.text()}  student wrote", seen["prompt"])
        for o in shown:
            self.assertIn(f"  {o.problem.text()}  student wrote", seen["prompt"])

    def test_ai_outage_is_handled(self):
        log = self.run_with(fakes.down)
        self.assertTrue(log.ai_unavailable)
        self.assertIn("unavailable", log.notes[0])
        self.assertIn(log.status.state, ("abstain", "inconclusive"))

    def test_garbage_reply_is_rejected(self):
        log = self.run_with(lambda prompt: "Sorry, I cannot help with that.")
        self.assertFalse(log.admission.admitted)
        self.assertIn("Rejected", log.admission.reason)

    def test_no_api_key_means_unavailable_not_a_crash(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProposerUnavailable):
                GeminiProposer()("hello")

    def test_extract(self):
        code, desc = extract("DESCRIPTION: adds\n```python\ndef rule(a, op, b):\n    return a + b\n```\nthanks")
        self.assertTrue(code.startswith("def rule"))
        self.assertEqual(desc, "adds")

    def test_duplicate_of_known_rule_is_not_added(self):
        session = Session("integers", seed=0)
        result = admit(fakes.REFERENCE_CODE["int_always_positive"], "integers", [], [],
                       session.pool, session.rules)
        self.assertFalse(result.admitted)
        self.assertEqual(result.duplicate_of, "int_always_positive")


if __name__ == "__main__":
    unittest.main()
