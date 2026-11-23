"""See the tool work in the terminal.

    python scripts/demo.py                        # the headline case: 5/5 on a worksheet, wrong rule underneath
    python scripts/demo.py --list                 # every rule a simulated student can follow
    python scripts/demo.py --student frac_add_tops_add_bottoms --worksheet 0
    python scripts/demo.py --student int_correct  # a student with no misconception
    python scripts/demo.py --student int_sign_of_first --slip 0.3   # careless student
    python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai oracle
    python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai cheat
    python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai down
    python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai gemini   # needs GEMINI_API_KEY
    python scripts/demo.py --interactive --domain integers   # you type the student's answers

--hide-rule removes the student's rule from the tool's list, so the tool meets a rule it has never seen.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mri import fakes  # noqa: E402
from mri.engine import UNKNOWN, Session  # noqa: E402
from mri.pipeline import (MAX_EXPLORE_QUESTIONS, WRONG_ANSWERS_FOR_AI, try_ai_rule)  # noqa: E402
from mri.problems import format_answer, parse_answer, worksheet_pool  # noqa: E402
from mri.proposer import ClaudeProposer, GeminiProposer  # noqa: E402
from mri.rules import LIBRARY, get_rule, library  # noqa: E402
from mri.student import SimulatedStudent  # noqa: E402


class Typist:
    """You are the student: type each answer."""

    def answer(self, problem):
        while True:
            try:
                return parse_answer(input(f"      {problem.text()} = "))
            except ValueError as exc:
                print(f"      {exc}")
            except EOFError:
                sys.exit("\nStopped.")


def name_of(session, rule_id):
    if rule_id == UNKNOWN:
        return "No single rule fits (slips, guessing, or an unknown rule)"
    return session.rule_by_id(rule_id).label


def show_candidates(session, top=3):
    for rule_id, p in session.ranking()[:top]:
        bar = "#" * round(p * 20)
        print(f"      {p:6.1%} {bar:<20} {name_of(session, rule_id)[:78]}")


def ask_and_show(session, student, question, number, typed):
    label = {"diagnose": "QUESTION", "confirm": "PREDICTION TEST", "explore": "EXTRA QUESTION"}[question.purpose]
    print(f"\n  {number}. {label}: {question.problem.text()}     ({question.why})")
    if question.purpose == "confirm":
        print(f"      Written down before asking: the student will answer {format_answer(question.predicted)}")
    answer = student.answer(question.problem)
    session.record(question.problem, answer, question)
    truth = format_answer(session.correct.predict(question.problem))
    if not typed:
        print(f"      Student answers {format_answer(answer)}   (correct answer: {truth})")
    if question.purpose == "confirm":
        print("      Prediction", "MATCHED" if answer == question.predicted else "FAILED")
    show_candidates(session)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--student", default="int_always_positive", help="rule the simulated student follows")
    ap.add_argument("--domain", choices=list(LIBRARY), help="only needed with --interactive")
    ap.add_argument("--slip", type=float, default=0.0, help="chance of a careless slip on each answer")
    ap.add_argument("--worksheet", type=int, default=5, help="ordinary worksheet questions answered first")
    ap.add_argument("--hide-rule", action="store_true", help="remove the student's rule from the tool's list")
    ap.add_argument("--ai", choices=["none", "oracle", "cheat", "down", "gemini", "claude"], default="none")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for rules in LIBRARY.values():
            for r in rules:
                print(f"{r.id:36} {r.label}")
        return

    if args.interactive:
        domain = args.domain or "integers"
        student, rules, true_rule = Typist(), library(domain), None
        print(f"Interactive session ({domain}). Type the student's answer to each question.")
    else:
        true_rule = get_rule(args.student)
        domain = true_rule.domain
        student = SimulatedStudent(true_rule, args.slip, seed=args.seed)
        rules = [r for r in library(domain) if not (args.hide_rule and r.id == true_rule.id)]
        print(f"Simulated student secretly follows: {true_rule.label}")
        if args.hide_rule:
            print("This rule has been REMOVED from the tool's list. The tool has never seen it.")
    ask = {"oracle": fakes.oracle(args.student), "cheat": fakes.cheat, "down": fakes.down,
           "gemini": GeminiProposer(), "claude": ClaudeProposer()}.get(args.ai)
    session = Session(domain, rules=rules, seed=args.seed)

    if args.worksheet and not args.interactive:
        sheet = random.Random(args.seed).sample(worksheet_pool(domain), args.worksheet)
        print(f"\nORDINARY WORKSHEET ({args.worksheet} questions)")
        right = 0
        for p in sheet:
            a = student.answer(p)
            session.record(p, a)
            ok = a == session.correct.predict(p)
            right += ok
            print(f"      {p.text():14} = {format_answer(a):6} {'right' if ok else 'WRONG'}")
        report = session.trap_report()
        print(f"  Score: {right}/{args.worksheet}. Kinds of question tested: "
              f"{report['kinds_tested']} of {report['kinds_total']}.")
        if report["trap_possible"]:
            print(f"  Every answer is right, but {len(report['hidden_rules'])} known wrong rules "
                  "would have produced these same answers:")
            for r in report["hidden_rules"]:
                print(f"      - {r.label}")
            print("  This worksheet cannot tell them apart. The tool now picks questions that can.")

    print("\nTHE TOOL'S QUESTIONS")
    number, tried_ai = 0, False
    while True:
        question = session.next_question()
        if question is not None:
            number += 1
            ask_and_show(session, student, question, number, args.interactive)
            continue
        if session.status().state in ("abstain", "inconclusive") and ask is not None and not tried_ai:
            tried_ai = True
            print("\n  No known rule fits. Collecting more wrong answers, then asking the AI to write a rule.")
            explored = 0
            while session.wrong_answers() < WRONG_ANSWERS_FOR_AI and explored < MAX_EXPLORE_QUESTIONS:
                question = session.explore_question()
                if question is None:
                    break
                number += 1
                explored += 1
                ask_and_show(session, student, question, number, args.interactive)
            admission, note = try_ai_rule(session, ask)
            print(f"\n  AI RULE-WRITER: {note}")
            if admission and admission.rule is not None and admission.admitted:
                print("  The AI's rule, as code:")
                for line in admission.rule.code.splitlines():
                    print(f"      | {line}")
                print("  It still has to predict fresh answers before it counts as a diagnosis.")
                continue
        break

    status = session.status()
    print("\nRESULT")
    print(f"  {status.state.upper().replace('_', ' ')}: {status.message}")
    print(f"  Questions asked by the tool: {number}. Kinds tested: {status.kinds_tested} of {status.kinds_total}.")
    if status.state == "diagnosed":
        print("\n  WHY (the student's answer next to what each method gives):")
        wrong = [o for o in session.observations if session.correct.predict(o.problem) != o.answer][:4]
        print(f"      {'question':16}{'student':>9}{'this rule':>11}{'correct':>9}")
        for o in wrong:
            print(f"      {o.problem.text():16}{format_answer(o.answer):>9}"
                  f"{format_answer(status.rule.predict(o.problem)):>11}"
                  f"{format_answer(session.correct.predict(o.problem)):>9}")
        print("\n  NEXT STEP: practise these. The wrong rule gives a wrong answer on each one:")
        for p in session.fix_questions(status.rule, 3):
            print(f"      {p.text():14} wrong rule gives {format_answer(status.rule.predict(p)):6}"
                  f" correct is {format_answer(session.correct.predict(p))}")
    if true_rule is not None:
        got = status.rule.id if status.rule else None
        if status.rule is not None and status.rule.source == "ai":
            same = all(status.rule.predict(p) == true_rule.predict(p) for p in session.pool)
            verdict = "matches the student's real rule on every question" if same else "does NOT match the real rule"
            print(f"\n  CHECK AGAINST THE ANSWER KEY: the AI-written rule {verdict}.")
        elif got == true_rule.id:
            print("\n  CHECK AGAINST THE ANSWER KEY: correct.")
        elif got is None:
            print("\n  CHECK AGAINST THE ANSWER KEY: the tool declined to diagnose "
                  f"(the real rule was '{true_rule.id}').")
        else:
            print(f"\n  CHECK AGAINST THE ANSWER KEY: WRONG. The real rule was '{true_rule.id}'.")


if __name__ == "__main__":
    main()
