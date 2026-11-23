"""Go/no-go evaluation for the deterministic engine.

E1  Simulated students: does adaptive questioning identify each rule, and how
    many questions does it need compared with random questions?
E2  Correct answer trap: a student with a wrong rule answers three trap
    questions correctly. Does one chosen question expose the rule?
E3  Unknown reasoning: remove a rule from the bank, simulate a student who
    holds it. Does the engine say "unknown" instead of a confident wrong label?
E4  Careless slips: 15% random slips, tolerance of one mismatch.
E5  External answer key (MaE): coverage, and leave-one-out prediction.

Run:  python -m eval.run_gonogo        (writes eval/results.json and eval/results.md)
"""
from __future__ import annotations

import json
import random
import statistics
from fractions import Fraction
from pathlib import Path

from mri.core import correct_answer, fmt, parse_answer, parse_problem, same
from mri.engine import diagnose, hypotheses_for, problem_pool, survivors, traps
from mri.rules import CORRECT_ID, RULES, RULES_BY_ID, student_answer

OUT = Path(__file__).parent
SEED = 20261123
N = 200          # simulated students per rule
SCREEN = 3       # opening questions
MAX_Q = 5        # adaptive follow-up limit


def rule_ops(h):
    return ("+", "-", "*", "/", "simplify") if h == CORRECT_ID else RULES_BY_ID[h].ops


def applicable_pool(h, op):
    pool = problem_pool(op)
    if h == CORRECT_ID:
        return list(pool)
    return [p for p in pool if RULES_BY_ID[h].fn(p) is not None]


def slip(ans, rng):
    v = Fraction(ans) if not isinstance(ans, tuple) else Fraction(*ans)
    return v + Fraction(rng.choice([1, -1]) * rng.randint(1, 3), rng.choice([2, 3, 4, 5]))


def run_session(true_rule, op, rng, bank=RULES_BY_ID, adaptive=True, slip_p=0.0,
                tolerance=0, screen=None, screen_n=SCREEN, coverage=True, worksheet="random"):
    pool = list(problem_pool(op))
    if screen is None:
        # "random": a realistic worksheet drawn from all questions for the operation.
        # "applicable": only questions where the student's rule changes the answer.
        cand = (applicable_pool(true_rule, op) or pool) if worksheet == "applicable" else pool
        screen = rng.sample(cand, min(screen_n, len(cand)))

    def answer(p):
        a = student_answer(true_rule, p)  # true student always uses the full bank
        if slip_p and rng.random() < slip_p:
            a = slip(a, rng)
        return a

    obs = [(p, answer(p)) for p in screen]
    asked = 0
    while True:
        d = diagnose(obs, [op], tolerance, bank, check_coverage=coverage)
        if d.status != "ask" or asked >= MAX_Q:
            return d, asked
        q = d.next_question if adaptive else rng.choice([x for x in pool if x not in [o[0] for o in obs]])
        obs.append((q, answer(q)))
        asked += 1


def e1(rng):
    rows = []
    for h in [CORRECT_ID] + [r.id for r in RULES]:
        for mode in ("adaptive", "random"):
            ok, qs, unresolved = 0, [], 0
            for _ in range(N):
                op = rng.choice(rule_ops(h))
                d, asked = run_session(h, op, rng, adaptive=(mode == "adaptive"))
                ok += d.status == "confirmed" and d.survivors == [h]
                unresolved += d.status != "confirmed"
                qs.append(asked)
            rows.append({"rule": h, "mode": mode, "accuracy": ok / N, "mean_questions": statistics.mean(qs),
                         "unresolved_after_5": unresolved / N})
    return rows


def e2(rng):
    rows = []
    for r in RULES:
        for op in r.ops:
            tp = traps(r.id, problem_pool(op))
            if len(tp) < SCREEN:
                continue
            pool_n = len([p for p in problem_pool(op) if r.fn(p) is not None])
            exposed1, exposed2, exposed_any, ks = 0, 0, 0, []
            screening_says_correct = 0
            for _ in range(N):
                screen = rng.sample(tp, SCREEN)
                obs = [(p, student_answer(r.id, p)) for p in screen]
                screening_says_correct += all(same(a, correct_answer(p)) for p, a in obs)
                # engine-chosen questions until the correct method no longer explains the answers
                o2, k = list(obs), 0
                while CORRECT_ID in survivors(hypotheses_for([op]), o2) and k < MAX_Q:
                    q = diagnose(o2, [op], check_coverage=False).next_question
                    o2.append((q, student_answer(r.id, q)))
                    k += 1
                exposed1 += k <= 1
                exposed2 += k <= 2
                ks.append(k)
                d, asked = run_session(r.id, op, rng, screen=screen)
                exposed_any += d.status == "confirmed" and d.survivors == [r.id]
            rows.append({"rule": r.id, "op": op, "trap_questions": len(tp), "applicable_questions": pool_n,
                         "trap_share": round(len(tp) / pool_n, 3),
                         "answer_checking_marks_correct": screening_says_correct / N,
                         "exposed_within_1_question": exposed1 / N,
                         "exposed_within_2_questions": exposed2 / N,
                         "mean_questions_to_expose": statistics.mean(ks),
                         "exposed_within_5": exposed_any / N})
    return rows


def e3(rng, coverage=True):
    rows = []
    for r in RULES:
        bank = {k: v for k, v in RULES_BY_ID.items() if k != r.id}
        outcomes = {"unknown": 0, "mislabeled_rule": 0, "mislabeled_correct": 0, "ambiguous": 0, "still_asking": 0}
        for _ in range(N):
            op = rng.choice(r.ops)
            d, _ = run_session(r.id, op, rng, bank=bank, coverage=coverage)
            if d.status == "unknown":
                outcomes["unknown"] += 1
            elif d.status == "confirmed":
                outcomes["mislabeled_correct" if d.survivors == [CORRECT_ID] else "mislabeled_rule"] += 1
            elif d.status == "ambiguous":
                outcomes["ambiguous"] += 1
            else:
                outcomes["still_asking"] += 1
        rows.append({"held_out": r.id, "coverage": coverage, **{k: v / N for k, v in outcomes.items()}})
    return rows


def e4(rng):
    ok = total = 0
    for h in [r.id for r in RULES]:
        for _ in range(N // 2):
            op = rng.choice(rule_ops(h))
            d, _ = run_session(h, op, rng, slip_p=0.15, tolerance=1, screen_n=5)
            ok += d.status == "confirmed" and d.survivors == [h]
            total += 1
    return {"slip_rate": 0.15, "tolerance": 1, "opening_questions": 5, "accuracy": ok / total, "students": total}


def e5():
    data = json.loads((Path(__file__).parent.parent / "data" / "mae_fractions.json").read_text())
    items = data["items"]
    expl = []
    for it in items:
        p = parse_problem(it["problem"])
        a = parse_answer(p, it["student"])
        hy = hypotheses_for([p.op])
        expl.append({**it, "explained_by": [h for h in hy if same(student_answer(h, p), a)],
                     "correct": fmt(correct_answer(p))})
    covered = sum(1 for e in expl if any(h != CORRECT_ID for h in e["explained_by"]))
    # leave-one-out: diagnose from the other examples of the same misconception, predict the held-out answer
    loo = []
    by = {}
    for e in expl:
        by.setdefault(e["mae"], []).append(e)
    for mae, exs in by.items():
        for i, held in enumerate(exs):
            train = [x for j, x in enumerate(exs) if j != i]
            obs = []
            for x in train:
                p = parse_problem(x["problem"])
                obs.append((p, parse_answer(p, x["student"])))
            ops = {o[0].op for o in obs}
            d = diagnose(obs, ops, check_coverage=False)
            hp = parse_problem(held["problem"])
            truth = parse_answer(hp, held["student"])
            pred = student_answer(d.survivors[0], hp) if d.status == "confirmed" else None
            loo.append({"mae": mae, "held_out_ex": held["ex"], "status": d.status, "survivors": d.survivors,
                        "predicted": fmt(pred) if pred is not None else None, "actual": held["student"],
                        "correct_prediction": pred is not None and same(pred, truth)})
    return {"items": expl, "covered": covered, "total": len(items), "loo": loo}


def main():
    rng = random.Random(SEED)
    res = {"seed": SEED, "students_per_rule": N, "E1": e1(rng), "E2": e2(rng), "E3": e3(rng), "E3_no_coverage": e3(rng, coverage=False),
           "E4": e4(rng), "E5": e5()}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (OUT / "results.md").write_text(report(res))
    print(report(res))


def pct(x):
    return f"{100 * x:.0f}%"


def report(res):
    L = ["# Go/no-go results", f"Seed {res['seed']}, {res['students_per_rule']} simulated students per rule.", ""]
    L += ["## E1. Identification: adaptive vs random follow-up questions",
          "Opening worksheet: 3 random questions for the operation. Follow-ups: chosen by the engine (adaptive) or random. Limit 5 follow-ups.", "",
          "| Hypothesis | Adaptive accuracy | Adaptive mean questions | Random accuracy | Random mean questions |",
          "|---|---|---|---|---|"]
    rows = res["E1"]
    for h in [CORRECT_ID] + [r.id for r in RULES]:
        a = next(r for r in rows if r["rule"] == h and r["mode"] == "adaptive")
        b = next(r for r in rows if r["rule"] == h and r["mode"] == "random")
        L.append(f"| {h} | {pct(a['accuracy'])} | {a['mean_questions']:.2f} | {pct(b['accuracy'])} | {b['mean_questions']:.2f} |")
    ad = [r for r in rows if r["mode"] == "adaptive"]
    rd = [r for r in rows if r["mode"] == "random"]
    L.append(f"| **All** | **{pct(statistics.mean(r['accuracy'] for r in ad))}** | **{statistics.mean(r['mean_questions'] for r in ad):.2f}** | "
             f"**{pct(statistics.mean(r['accuracy'] for r in rd))}** | **{statistics.mean(r['mean_questions'] for r in rd):.2f}** |")
    L += ["", "## E2. Correct answer trap",
          "Three opening questions are all traps (the wrong rule gives the right answer).", "",
          "Exposed means the correct method no longer explains the student's answers.", "",
          "| Rule | Op | Trap share of questions | Answer checking marks student correct | Exposed by 1 chosen question | Exposed within 2 | Mean questions | Confirmed after stress checks |",
          "|---|---|---|---|---|---|---|---|"]
    for r in res["E2"]:
        L.append(f"| {r['rule']} | {r['op']} | {pct(r['trap_share'])} ({r['trap_questions']}/{r['applicable_questions']}) | "
                 f"{pct(r['answer_checking_marks_correct'])} | {pct(r['exposed_within_1_question'])} | {pct(r['exposed_within_2_questions'])} | "
                 f"{r['mean_questions_to_expose']:.2f} | {pct(r['exposed_within_5'])} |")
    L += ["", "## E3. Unknown reasoning (rule removed from the bank), with and without stress coverage",
          "| Held-out rule | Says unknown (with) | Wrong label (with) | Says unknown (without) | Wrong label (without) |", "|---|---|---|---|---|"]
    wl = lambda r: r['mislabeled_rule'] + r['mislabeled_correct']
    for a, b in zip(res["E3"], res["E3_no_coverage"]):
        L.append(f"| {a['held_out']} | {pct(a['unknown'])} | {pct(wl(a))} | {pct(b['unknown'])} | {pct(wl(b))} |")
    L.append(f"| **All** | **{pct(statistics.mean(r['unknown'] for r in res['E3']))}** | **{pct(statistics.mean(wl(r) for r in res['E3']))}** | "
             f"**{pct(statistics.mean(r['unknown'] for r in res['E3_no_coverage']))}** | **{pct(statistics.mean(wl(r) for r in res['E3_no_coverage']))}** |")
    e4 = res["E4"]
    L += ["", "## E4. Careless slips",
          f"Slip rate {pct(e4['slip_rate'])}, tolerance {e4['tolerance']}, {e4['opening_questions']} opening questions: "
          f"accuracy {pct(e4['accuracy'])} over {e4['students']} students."]
    e5 = res["E5"]
    L += ["", "## E5. External answer key (MaE, transcribed fraction items)",
          f"Examples reproduced exactly by a wrong rule: {e5['covered']}/{e5['total']}.", "",
          "| MaE | Ex | Problem | Student | Correct | Explained by |", "|---|---|---|---|---|---|"]
    for it in e5["items"]:
        L.append(f"| {it['mae']} | {it['ex']} | {it['problem']} | {it['student']} | {it['correct']} | {', '.join(it['explained_by']) or 'nothing (unknown)'} |")
    ok = sum(x["correct_prediction"] for x in e5["loo"])
    committed = [x for x in e5["loo"] if x["status"] == "confirmed"]
    L += ["", f"Leave-one-out: diagnose from the other examples of the same misconception, predict the held-out answer: "
              f"{ok}/{len(e5['loo'])} correct overall. The engine committed on {len(committed)} and was right on "
              f"{sum(x['correct_prediction'] for x in committed)} of them; it said unknown on {len(e5['loo']) - len(committed)}.", "",
          "| MaE | Held out | Status | Diagnosis | Predicted (value) | Actual | Result |", "|---|---|---|---|---|---|---|"]
    for x in e5["loo"]:
        mark = "match" if x["correct_prediction"] else ("-" if x["predicted"] is None else "miss")
        L.append(f"| {x['mae']} | {x['held_out_ex']} | {x['status']} | {', '.join(x['survivors']) or '-'} | {x['predicted'] or '-'} | {x['actual']} | {mark} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
