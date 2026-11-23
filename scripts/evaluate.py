"""Measure how well the tool works, using simulated students as the answer key.

Run:  python scripts/evaluate.py            (about a minute)
      python scripts/evaluate.py --seeds 50 (faster, noisier)

Writes evidence/results.json and evidence/results.md.

IMPORTANT: every number here comes from SIMULATED students who follow one rule
exactly (plus optional careless slips). Real students are messier. These numbers
show the method works as designed; they do not show it works on real children.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mri.engine import Session  # noqa: E402
from mri.pipeline import run_session  # noqa: E402
from mri.problems import DOMAINS, worksheet_pool  # noqa: E402
from mri.heldout_rules import HELD_OUT_RULES, HELD_OUT_RULES_2  # noqa: E402
from mri.rules import library  # noqa: E402
from mri.student import RandomGuesser, SimulatedStudent  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "evidence"


def outcome(status, true_rule_id: str | None) -> str:
    """Compare the tool's result with the rule the simulated student really follows."""
    if status.state in ("abstain", "inconclusive"):
        return "no_diagnosis"
    if status.rule.id == true_rule_id:
        return "right"
    return "false_all_clear" if status.rule.is_correct else "wrong"


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    count = lambda key: sum(r["outcome"] == key for r in rows)  # noqa: E731
    qs = [r["questions"] for r in rows]
    return {
        "sessions": n,
        "right_pct": round(100 * count("right") / n, 1),
        "wrong_pct": round(100 * count("wrong") / n, 1),
        "false_all_clear_pct": round(100 * count("false_all_clear") / n, 1),
        "no_diagnosis_pct": round(100 * count("no_diagnosis") / n, 1),
        "mean_questions": round(statistics.mean(qs), 2),
        "median_questions": statistics.median(qs),
    }


def known_rules(seeds: int, slip: float, policy: str, **cfg) -> dict:
    """Students follow a rule the tool knows. Does it find the right one, and how fast?"""
    rows = []
    for domain in DOMAINS:
        for rule in library(domain):
            for seed in range(seeds):
                session = Session(domain, policy=policy, seed=seed, **cfg)
                log = run_session(session, SimulatedStudent(rule, slip, seed=10_000 + seed))
                rows.append({"outcome": outcome(log.status, rule.id), "questions": log.questions_asked})
    return summarise(rows)


def unknown_rules(seeds: int, slip: float, **cfg) -> dict:
    """Students follow a wrong rule that has been REMOVED from the tool's list.

    The honest result is 'no diagnosis'. Naming some other rule is a misdiagnosis.
    """
    rows = []
    for domain in DOMAINS:
        for hidden in library(domain):
            if hidden.is_correct:
                continue
            rules = [r for r in library(domain) if r.id != hidden.id]
            for seed in range(seeds):
                session = Session(domain, rules=rules, seed=seed, **cfg)
                log = run_session(session, SimulatedStudent(hidden, slip, seed=10_000 + seed))
                rows.append({"outcome": outcome(log.status, None), "questions": log.questions_asked})
    return summarise(rows)


def extra_hidden_rules(seeds: int, hidden_rules: list, **cfg) -> dict:
    """Same test, with wrong rules that were not used while designing the checks."""
    rows = []
    per_rule = {}
    for hidden in hidden_rules:
        mine = []
        for seed in range(seeds):
            session = Session(hidden.domain, seed=seed, **cfg)
            log = run_session(session, SimulatedStudent(hidden, 0.0, seed=10_000 + seed))
            mine.append({"outcome": outcome(log.status, None), "questions": log.questions_asked})
        per_rule[hidden.id] = summarise(mine)
        rows += mine
    return {"ALL SIX": summarise(rows), **per_rule}


def guessers(seeds: int, **cfg) -> dict:
    """Students with no stable rule (each answer uses a randomly chosen rule)."""
    rows = []
    for domain in DOMAINS:
        for seed in range(seeds * 4):
            session = Session(domain, seed=seed, **cfg)
            log = run_session(session, RandomGuesser(library(domain), seed=10_000 + seed))
            rows.append({"outcome": outcome(log.status, None), "questions": log.questions_asked})
    return summarise(rows)


def trap(seeds: int, worksheet_size: int = 5) -> dict:
    """Right answers, wrong rule.

    Each simulated student holds a wrong rule and first answers an ordinary worksheet.
    We count how often the worksheet comes back 100% correct, and how many extra
    questions the tool then needs to expose the wrong rule.
    """
    per_rule = []
    for domain in DOMAINS:
        sheet_pool = worksheet_pool(domain)
        for rule in library(domain):
            if rule.is_correct:
                continue
            perfect = 0
            found = 0
            extra = []
            for seed in range(seeds):
                sheet = random.Random(seed).sample(sheet_pool, worksheet_size)
                session = Session(domain, seed=seed)
                log = run_session(session, SimulatedStudent(rule, 0.0, seed=seed), given=sheet)
                report_all_correct = all(
                    session.correct.predict(p) == rule.predict(p) for p in sheet)
                if report_all_correct:
                    perfect += 1
                    if log.status.rule is not None and log.status.rule.id == rule.id:
                        found += 1
                        extra.append(log.questions_asked)
            per_rule.append({
                "rule": rule.id,
                "perfect_worksheets_pct": round(100 * perfect / seeds, 1),
                "exposed_pct": round(100 * found / perfect, 1) if perfect else None,
                "mean_extra_questions": round(statistics.mean(extra), 2) if extra else None,
            })
    return {"worksheet_size": worksheet_size, "rules": per_rule}


def table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=200, help="simulated students per rule")
    args = parser.parse_args()
    n = args.seeds
    start = time.time()
    results: dict = {"seeds_per_rule": n}

    print("1/4 question choice: disagreement vs random ...")
    results["question_choice"] = {
        f"{policy}_slip{slip}": known_rules(n, slip, policy)
        for slip in (0.0, 0.1) for policy in ("disagreement", "random")
    }
    print("2/4 rules the tool has never seen ...")
    variants = {
        "A: one prediction, any question": dict(confirm_mode="solo", confirmations=1, clear_needs_all_kinds=False),
        "B: A + re-test misses, new kinds": dict(confirm_mode="novel_prefer_solo", confirmations=1,
                                                 clear_needs_all_kinds=False),
        "C: B + all kinds before all-clear": dict(confirm_mode="novel_prefer_solo", confirmations=1,
                                                  clear_needs_all_kinds=True),
        "D: C + two predictions": dict(confirm_mode="novel_prefer_solo", confirmations=2,
                                       clear_needs_all_kinds=True),
        "E: D + kinds chosen evenly (default)": dict(confirm_mode="novel", confirmations=2,
                                                     clear_needs_all_kinds=True),
    }
    results["unknown_rules"] = {name: unknown_rules(n, 0.0, **cfg) for name, cfg in variants.items()}
    results["known_rules_by_confirm"] = {
        name: known_rules(n, 0.1, "disagreement", **cfg) for name, cfg in variants.items()
    }
    results["extra_hidden_rules_set1_before_fix"] = extra_hidden_rules(n, HELD_OUT_RULES, **variants["D: C + two predictions"])
    results["extra_hidden_rules_set1_after_fix"] = extra_hidden_rules(n, HELD_OUT_RULES)
    results["extra_hidden_rules_set2"] = extra_hidden_rules(n, HELD_OUT_RULES_2)
    print("3/4 careless slips and guessing ...")
    results["slip_sweep"] = {
        f"slip{slip}": known_rules(n, slip, "disagreement") for slip in (0.0, 0.1, 0.2, 0.3)
    }
    results["guessers"] = guessers(n)
    print("4/4 right answers, wrong rule ...")
    results["trap"] = trap(n)
    results["seconds"] = round(time.time() - start, 1)

    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))

    cols = ["sessions", "right_pct", "wrong_pct", "false_all_clear_pct", "no_diagnosis_pct", "mean_questions"]
    head = ["Setting", "Sessions", "Right rule %", "Wrong rule named %", "False all-clear %",
            "No diagnosis %", "Mean questions"]
    block = lambda d: [[k] + [v[c] for c in cols] for k, v in d.items()]  # noqa: E731
    md = [
        "# Test results (simulated students)",
        "",
        f"Generated by `python scripts/evaluate.py --seeds {n}`. "
        "Every number comes from simulated students who follow one rule exactly, plus optional "
        "careless slips. Real students are messier, so treat these as checks that the method "
        "works as designed, not as proof it works in a classroom.",
        "",
        "## 1. Question choice: disagreement vs random (student's rule is in the list)",
        "", table(head, block(results["question_choice"])),
        "",
        "## 2. Student follows a rule the tool has never seen (correct result: no diagnosis)",
        "",
        "'Wrong rule named' means the tool named some other wrong rule. 'False all-clear' means it "
        "said no misconception. Both are errors here.",
        "", table(head, block(results["unknown_rules"])),
        "",
        "Cost of each confirmation setting when the rule IS in the list (slip rate 0.1):",
        "", table(head, block(results["known_rules_by_confirm"])),
        "",
        "### Fairness checks on rules not used while designing the tool",
        "",
        "The table above is flattering: the checks were designed while testing those same 13 rules. "
        "So two extra sets of six wrong rules were written (`mri/heldout_rules.py`).",
        "",
        "Set 1, design D (the default at the time). One rule was misdiagnosed every time:",
        "", table(head, block(results["extra_hidden_rules_set1_before_fix"])),
        "",
        "That led to design E. Set 1 again with design E (no longer a clean test, since E was "
        "made in response to it):",
        "", table(head, block(results["extra_hidden_rules_set1_after_fix"])),
        "",
        "Set 2, written before design E was run, evaluated once with design E, nothing changed afterwards:",
        "", table(head, block(results["extra_hidden_rules_set2"])),
        "",
        "## 3. Careless slips and guessing",
        "", table(head, block(results["slip_sweep"])),
        "",
        "Students with no stable rule (correct result: no diagnosis):",
        "", table(head, block({"guessers": results["guessers"]})),
        "",
        f"## 4. Right answers, wrong rule ({results['trap']['worksheet_size']}-question ordinary worksheet)",
        "",
        table(["Wrong rule", "Worksheets scored 100% anyway", "Then exposed by the tool %", "Mean extra questions"],
              [[r["rule"], f'{r["perfect_worksheets_pct"]}%', r["exposed_pct"], r["mean_extra_questions"]]
               for r in results["trap"]["rules"]]),
        "",
    ]
    (OUT / "results.md").write_text("\n".join(md))
    print(f"done in {results['seconds']}s -> {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
