import json
from fractions import Fraction
from pathlib import Path

import pytest

from mri.core import correct_answer, parse_answer, parse_problem, same
from mri.engine import diagnose, problem_pool, traps
from mri.rules import RULES_BY_ID, student_answer

DATA = json.loads((Path(__file__).parent.parent / "data" / "mae_fractions.json").read_text())


def test_parse_and_correct():
    p = parse_problem("6 - 1 1/4")
    assert correct_answer(p) == Fraction(19, 4)
    assert parse_answer(p, "4 3/4") == Fraction(19, 4)
    s = parse_problem("simplify 6/8")
    assert correct_answer(s) == (3, 4)
    assert parse_answer(s, "3/8") == (3, 8)


@pytest.mark.parametrize("mae,rule", [("MaE08", "R01"), ("MaE11", "R05"), ("MaE13", "R06"), ("MaE15", "R09")])
def test_rules_reproduce_all_four_mae_examples(mae, rule):
    for it in [i for i in DATA["items"] if i["mae"] == mae and not (mae == "MaE08" and i["ex"] == 4)]:
        p = parse_problem(it["problem"])
        assert same(student_answer(rule, p), parse_answer(p, it["student"])), it


def test_mae14_contains_correct_answer_traps():
    # MaE's own notes say example 2 is a correct answer reached by a wrong method.
    for ex in (1, 2):
        it = next(i for i in DATA["items"] if i["mae"] == "MaE14" and i["ex"] == ex)
        p = parse_problem(it["problem"])
        a = parse_answer(p, it["student"])
        assert same(a, correct_answer(p))
        assert same(student_answer("R08", p), a)


def test_trap_student_is_exposed_by_one_chosen_question():
    obs = [(parse_problem(s), None) for s in ("6/8 ÷ 2/8", "4/6 ÷ 2/2")]
    obs = [(p, student_answer("R08", p)) for p, _ in obs]
    d = diagnose(obs, ["/"])
    assert d.status == "ask" and set(d.survivors) == {"OK", "R08"}
    q = d.next_question
    after = diagnose(obs + [(q, student_answer("R08", q))], ["/"])
    assert after.survivors == ["R08"]


def test_unknown_reasoning_is_not_mislabeled():
    p = parse_problem("8 1/3 - 2/3")  # MaE10 example 2: answer 4 1/2 follows no rule in the bank
    d = diagnose([(p, parse_answer(p, "4 1/2"))], ["-"])
    assert d.status == "unknown"


def test_confirmation_requires_a_correct_prediction():
    student = "R04"
    obs = [(p, student_answer(student, p)) for p in map(parse_problem, ["5 3/4 - 2 1/4", "2 1/3 - 1 1/2"])]
    for _ in range(8):
        d = diagnose(obs, ["-"])
        if d.status != "ask":
            break
        q = d.next_question
        obs.append((q, student_answer(student, q)))
    assert d.status == "confirmed" and d.survivors == ["R04"]


def test_smaller_from_larger_is_right_on_most_subtraction_questions():
    pool = problem_pool("-")
    share = len(traps("R04", pool)) / len([p for p in pool if RULES_BY_ID["R04"].fn(p) is not None])
    assert share > 0.5
