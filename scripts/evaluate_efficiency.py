"""Diagnostic efficiency on the AI path: accuracy, wrong diagnoses, abstention and
questions, for each stand-in writer.

Set-up (same as evaluate_ai.py): one wrong rule is removed from the tool's list, a
simulated student follows it with no slips, and the AI is called when no known rule
fits. Writers: oracle (writes the true rule), partial (copies the student only on the
kinds where it saw wrong answers; integers only), messy (right idea, sloppy format),
cheat (memorises answers).

Usage:
    python scripts/evaluate_efficiency.py --tag before   # run once on the old design
    python scripts/evaluate_efficiency.py --tag after
Writes evidence/efficiency_<tag>.json. Existing files are never overwritten unless
--force is given, so a baseline cannot be replaced by accident.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mri import fakes  # noqa: E402
from mri.engine import Session  # noqa: E402
from mri.pipeline import run_session  # noqa: E402
from mri.problems import DOMAINS  # noqa: E402
from mri.rules import library  # noqa: E402
from mri.student import SimulatedStudent  # noqa: E402

WRITERS = {"oracle": fakes.oracle, "partial": fakes.partial, "messy": fakes.messy, "cheat": lambda _id: fakes.cheat}


def run(writer: str, seeds: int) -> dict:
    rows = []
    for domain in DOMAINS:
        if writer == "partial" and domain != "integers":
            continue
        for hidden in library(domain):
            if hidden.is_correct:
                continue
            rules = [r for r in library(domain) if r.id != hidden.id]
            for seed in range(seeds):
                session = Session(domain, rules=rules, seed=seed)
                log = run_session(session, SimulatedStudent(hidden, 0.0, seed=seed), ask=WRITERS[writer](hidden.id))
                st = log.status
                if st.state == "diagnosed":
                    truly = all(st.rule.predict(p) == hidden.predict(p) for p in session.pool)
                    result = "right" if truly else "wrong"
                elif st.state == "no_misconception":
                    result = "wrong"
                else:
                    result = "no_diagnosis"
                adm = log.admission
                rows.append({"domain": domain, "hidden": hidden.id, "seed": seed, "result": result,
                             "questions": log.questions_asked,
                             "admitted": bool(adm and adm.admitted),
                             "admitted_truly_right": bool(adm and adm.admitted and all(
                                 adm.rule.predict(p) == hidden.predict(p) for p in session.pool))})
    n = len(rows)
    pct = lambda k: round(100 * sum(r["result"] == k for r in rows) / n, 1)  # noqa: E731
    adm = [r for r in rows if r["admitted"]]
    return {"sessions": n, "right_pct": pct("right"), "wrong_pct": pct("wrong"),
            "no_diagnosis_pct": pct("no_diagnosis"),
            "mean_questions": round(statistics.mean(r["questions"] for r in rows), 2),
            "admitted_pct": round(100 * len(adm) / n, 1),
            "admitted_but_not_truly_right_pct": round(100 * sum(not r["admitted_truly_right"] for r in adm) / n, 1),
            "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out = ROOT / "evidence" / f"efficiency_{args.tag}.json"
    if out.exists() and not args.force:
        sys.exit(f"{out.name} already exists; refusing to overwrite it.")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    res = {"tag": args.tag, "commit": commit, "seeds": args.seeds,
           "writers": {w: run(w, args.seeds) for w in WRITERS}}
    out.write_text(json.dumps(res, indent=1))
    print(f"{args.tag} (commit {commit}, {args.seeds} seeds per hidden rule)")
    print("| Writer | Sessions | Right | Wrong | No diagnosis | Mean questions | Admitted | Admitted but wrong |")
    print("|---|---|---|---|---|---|---|---|")
    for w, r in res["writers"].items():
        print(f"| {w} | {r['sessions']} | {r['right_pct']}% | {r['wrong_pct']}% | {r['no_diagnosis_pct']}% | "
              f"{r['mean_questions']} | {r['admitted_pct']}% | {r['admitted_but_not_truly_right_pct']}% |")


if __name__ == "__main__":
    main()
