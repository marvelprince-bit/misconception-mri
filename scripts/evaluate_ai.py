"""Test the AI rule-writer: does the hidden-answer check keep bad rules out?

Set-up: one wrong rule is REMOVED from the tool's list, and a simulated student
follows it. The tool should notice that no known rule fits, ask the AI to write a
rule, and admit that rule only if it predicts answers the AI never saw.

Offline (no key, checks the plumbing with stand-in writers):
    python scripts/evaluate_ai.py --writer oracle
    python scripts/evaluate_ai.py --writer cheat

Live (needs GEMINI_API_KEY; this is the result to report in the submission):
    python scripts/evaluate_ai.py --writer gemini --seeds 5

Writes evidence/ai_results_<writer>.json and prints a table.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mri import fakes  # noqa: E402
from mri.engine import Session  # noqa: E402
from mri.pipeline import run_session  # noqa: E402
from mri.problems import DOMAINS  # noqa: E402
from mri.proposer import make_proposer  # noqa: E402
from mri.rules import library  # noqa: E402
from mri.student import SimulatedStudent  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "evidence"


SHAPE_CHECK = "risk"


class ReplayBook:
    """Plays back a saved live run: for each prompt the code sends, returns the reply the
    model gave to that EXACT prompt in the raw log. No API call. If the code sends a prompt
    that is not in the log, the replay stops with an error, so a replay can never silently
    differ from the run it reproduces."""

    def __init__(self, path):
        self.book, self.used, self.total = {}, 0, 0
        for line in Path(path).read_text().splitlines():
            entry = json.loads(line)
            self.book.setdefault(entry["prompt"], []).append(entry["reply"])
            self.total += 1

    def ask(self, prompt):
        replies = self.book.get(prompt)
        if not replies:
            raise SystemExit("Replay mismatch: the code sent a prompt that is not in the raw log. "
                             "This log was made by a different version of the code or another seed.")
        self.used += 1
        return replies.pop(0)


replay_book = None


def run(writer: str, seeds: int, gate: bool, domains=DOMAINS, seed_offset: int = 0,
        hidden_set: str = "library") -> dict:
    from mri.heldout_rules import HELD_OUT_RULES_4
    rows = []
    for domain in domains:
        if writer == "partial" and domain != "integers":
            continue  # the partial stand-in is written for integers only
        if hidden_set == "4":
            # Rules written after the design freeze; the tool's list is complete, so the
            # student's rule is simply not in it.
            hiddens = [h for h in HELD_OUT_RULES_4 if h.domain == domain]
        else:
            hiddens = [h for h in library(domain) if not h.is_correct]
        for hidden in hiddens:
            rules = [r for r in library(domain) if r.id != hidden.id]
            for seed in range(seed_offset, seed_offset + seeds):
                makers = {"oracle": lambda: fakes.oracle(hidden.id), "cheat": lambda: fakes.cheat,
                          "down": lambda: fakes.down, "messy": lambda: fakes.messy(hidden.id),
                          "partial": lambda: fakes.partial(hidden.id),
                          "occam": lambda: fakes.occam(hidden.id)}
                if writer.startswith("replay:"):
                    ask = replay_book.ask
                else:
                    ask = makers[writer]() if writer in makers else make_proposer(writer)
                session = Session(domain, rules=rules, seed=seed, diagnosis_needs_all_kinds=SHAPE_CHECK)
                log = run_session(session, SimulatedStudent(hidden, 0.0, seed=seed), ask=ask, gate=gate)
                adm = log.admission
                admitted = bool(adm and adm.admitted)
                # Ground truth: does the admitted rule match the student's real rule on EVERY question?
                true_match = admitted and all(
                    adm.rule.predict(p) == hidden.predict(p) for p in session.pool)
                final = log.status
                # Score the rule actually NAMED, which since the repair step need not be the
                # last rule the AI proposed (fixed 24 Nov: live run 7 named a repaired rule
                # identical to the student's and was scored 'wrong' from the rejected one).
                named_true = final.state == "diagnosed" and all(
                    final.rule.predict(p) == hidden.predict(p) for p in session.pool)
                if final.state == "diagnosed" and final.rule.source == "ai":
                    result = "right" if named_true else "wrong"
                elif final.state in ("diagnosed", "no_misconception"):
                    result = "wrong"
                else:
                    result = "no_diagnosis"
                rows.append({"domain": domain, "hidden": hidden.id, "seed": seed,
                             "ai_called": log.ai_attempted, "admitted": admitted,
                             "admitted_and_truly_right": true_match, "result": result,
                             "named_rule": final.rule.id if final.state == "diagnosed" else None,
                             "named_by_repair": bool(final.state == "diagnosed"
                                                     and final.rule.id.startswith("ai_repair")),
                             "questions": log.questions_asked,
                             "attempts": adm.attempts if adm else 0,
                             "reason": adm.reason if adm else "; ".join(log.notes)})
    n = len(rows)
    pct = lambda k: round(100 * sum(bool(r[k]) for r in rows) / n, 1)  # noqa: E731
    res = lambda k: round(100 * sum(r["result"] == k for r in rows) / n, 1)  # noqa: E731
    admitted = [r for r in rows if r["admitted"]]
    return {
        "writer": writer, "hidden_answer_check": gate, "sessions": n,
        "ai_called_pct": pct("ai_called"), "admitted_pct": pct("admitted"),
        "admitted_rules_truly_right_pct": (
            round(100 * sum(r["admitted_and_truly_right"] for r in admitted) / len(admitted), 1)
            if admitted else None),
        "final_right_pct": res("right"), "final_wrong_pct": res("wrong"),
        "final_no_diagnosis_pct": res("no_diagnosis"),
        "mean_questions": round(statistics.mean(r["questions"] for r in rows), 2),
        "repair_used_pct": round(100 * sum(r["attempts"] > 1 for r in rows) / n, 1),
        "admitted_after_repair_pct": round(100 * sum(r["attempts"] > 1 and r["admitted"] for r in rows) / n, 1),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--writer", help="stand-in, live model, or replay:<raw log> (plays a saved live run back, no API calls)",
                        default="oracle")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--domain", choices=list(DOMAINS), help="test one topic only (fewer API calls)")
    parser.add_argument("--hidden-set", choices=["library", "4"], default="library",
                        help="'library' (default): each library rule removed in turn (24 rules); "
                             "'4': the 12 held-out set-4 rules, written after the design freeze")
    parser.add_argument("--seed-offset", type=int, default=0,
                        help="first simulated student; use e.g. 100 for fresh students never "
                             "used during development (results get their own file)")
    parser.add_argument("--shape-check", choices=["risk", "ai", "none"], default="risk",
                        help="'risk' (default): every untested shape for AI-written rules, plus one "
                             "riskiest-shape question for known rules; 'ai': shape check for AI "
                             "rules only (design of the 23 Nov live runs); 'none': earlier design")
    parser.add_argument("--both-gates", action="store_true",
                        help="also run with the hidden-answer check off (default for stand-ins; "
                             "doubles the calls for a live model)")
    args = parser.parse_args()
    live = args.writer in ("gemini", "claude")
    global SHAPE_CHECK
    SHAPE_CHECK = args.shape_check
    if args.writer == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (see .env.example).")
    if args.writer == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Set GEMINI_API_KEY first (see .env.example). Nothing was run.")

    OUT.mkdir(exist_ok=True)
    replay = args.writer.startswith("replay:")
    if replay:
        global replay_book
        replay_book = ReplayBook(args.writer.split(":", 1)[1])
        tag = "replay_" + Path(args.writer.split(":", 1)[1]).stem
    else:
        tag = args.writer
    tag += ("" if args.shape_check == "risk" else f"_{args.shape_check}check")
    if args.hidden_set == "4":
        if args.writer in ("oracle", "occam", "messy", "partial"):
            sys.exit("Those stand-ins copy a known reference answer; set 4 has none. Use cheat, down or a live model.")
        tag += "_set4"
    if args.seed_offset:
        tag += f"_seeds{args.seed_offset}-{args.seed_offset + args.seeds - 1}"
    if live and (OUT / f"ai_results_{tag}.json").exists():
        sys.exit(f"evidence/ai_results_{tag}.json already exists. Evidence is never overwritten: "
                 f"rename or move it first (e.g. to evidence/archive/), then rerun.")
    raw = OUT / f"ai_raw_{tag}.jsonl"
    if replay:
        raw = Path(args.writer.split(":", 1)[1])  # replays write no new log
        os.environ.pop("MRI_RAW_LOG", None)
    else:
        raw.write_text("")  # every prompt, reply, extracted code and verdict; no keys
        os.environ["MRI_RAW_LOG"] = str(raw)
    gates = (True, False) if (args.both_gates or not (live or replay)) else (True,)
    domains = (args.domain,) if args.domain else DOMAINS
    results = {("on" if gate else "off"): run(args.writer, args.seeds, gate, domains, args.seed_offset, args.hidden_set) for gate in gates}
    (OUT / f"ai_results_{tag}.json").write_text(json.dumps(results, indent=2))

    keys = ["sessions", "ai_called_pct", "admitted_pct", "admitted_rules_truly_right_pct",
            "final_right_pct", "final_wrong_pct", "final_no_diagnosis_pct", "mean_questions",
            "repair_used_pct", "admitted_after_repair_pct"]
    from mri.heldout_rules import HELD_OUT_RULES_4
    n_rules = (sum(1 for h in HELD_OUT_RULES_4 if h.domain in domains) if args.hidden_set == "4" else
               sum(1 for d in domains for r in library(d) if not r.is_correct
                   and not (args.writer == "partial" and d != "integers")))
    print(f"\nAI rule-writer: {args.writer}, shape check {args.shape_check}   "
          f"({n_rules} hidden rules x {args.seeds} simulated students, "
          f"seeds {args.seed_offset} to {args.seed_offset + args.seeds - 1})")
    print(f"Raw prompts and replies: {raw}")
    print("| Hidden-answer check | " + " | ".join(keys) + " |")
    print("|" + "---|" * (len(keys) + 1))
    for name, r in results.items():
        print(f"| {name} | " + " | ".join(str(r[k]) for k in keys) + " |")
    rows = results["on"]["rows"]
    count = {k: sum(r["result"] == k for r in rows) for k in ("right", "wrong", "no_diagnosis")}
    print(f"\nRESULT: {count['right']}/{len(rows)} right, {count['wrong']} wrong, "
          f"{count['no_diagnosis']} no diagnosis "
          f"({sum(r.get('named_by_repair', False) for r in rows)} named after a repair).")
    for r in rows:
        if r["result"] != "right":
            print(f"  {r['hidden']}: {r['result']} after {r['questions']} questions")
    if replay:
        print(f"Replay: used {replay_book.used} of {replay_book.total} saved replies, no API calls.")
        if replay_book.used != replay_book.total:
            print("WARNING: not every saved reply was used; this replay differs from the original run.")


if __name__ == "__main__":
    main()
