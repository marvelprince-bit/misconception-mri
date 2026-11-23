"""External answer key: the MaE dataset (Otero, Druga and Lan, MIT licence).

For every transcribed MaE example, list which rules in the library reproduce the
student's written answer exactly. Then a leave-one-out test: show the engine the
other examples of the same misconception, let it pick its best explanation, and
check whether that explanation predicts the held-out answer.

These are fixed examples, so the engine cannot ask its own follow-up questions here.
It commits only when one rule (not "unknown") reaches the engine's normal confidence.

Run:  python scripts/evaluate_mae.py   (writes evidence/mae_results.md and .json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mri.engine import UNKNOWN, Session  # noqa: E402
from mri.problems import format_mixed, parse_answer, parse_problem_text  # noqa: E402
from mri.rules import library  # noqa: E402

SYMBOL_TO_DOMAIN = [("÷", "frac_div"), ("×", "frac_mul")]


def domain_of(text: str) -> str | None:
    t = text.strip()
    if t.startswith("simplify"):
        return None
    for sym, dom in SYMBOL_TO_DOMAIN:
        if sym in t:
            return dom
    if "/" not in t:
        return "integers"
    return "fractions" if " + " in t else "frac_sub"


def load():
    data = json.loads((ROOT / "data" / "mae_examples.json").read_text())
    items = []
    for it in data["items"]:
        dom = domain_of(it["problem"])
        if dom is None:
            items.append({**it, "domain": None})
            continue
        text = it["problem"].replace(" - ", " − ") if dom == "frac_sub" else it["problem"]
        prob = parse_problem_text(dom, text if dom != "integers" else it["problem"])
        items.append({**it, "domain": dom, "p": prob, "a": parse_answer(it["student"])})
    return items


def main() -> None:
    items = load()
    rows, loo = [], []
    for it in items:
        if it["domain"] is None:
            rows.append({**{k: it[k] for k in ("mae", "ex", "problem", "student")}, "topic": "out of scope",
                         "correct": "", "explained_by": []})
            continue
        rules = library(it["domain"])
        correct = next(r for r in rules if r.is_correct)
        rows.append({**{k: it[k] for k in ("mae", "ex", "problem", "student")}, "topic": it["domain"],
                     "correct": format_mixed(correct.predict(it["p"])),
                     "explained_by": [r.id for r in rules if r.predict(it["p"]) == it["a"]]})
    by = {}
    for it in items:
        if it["domain"]:
            by.setdefault((it["mae"], it["domain"]), []).append(it)
    for (mae, dom), group in by.items():
        if len(group) < 3:
            continue
        for held in group:
            train = [x for x in group if x is not held]
            s = Session(dom, seed=0)
            for x in train:
                s.record(x["p"], x["a"])
            top_id, top_p = s.ranking()[0]
            commit = top_id != UNKNOWN and top_p >= s.confidence
            rule = s.rule_by_id(top_id) if commit else None
            pred = rule.predict(held["p"]) if rule else None
            loo.append({"mae": mae, "held_out": held["ex"], "committed_to": top_id if commit else "no diagnosis",
                        "confidence": round(top_p, 3), "predicted": format_mixed(pred) if rule else "-",
                        "actual": held["student"], "match": bool(rule) and pred == held["a"]})
    out = {"rows": rows, "loo": loo}
    (ROOT / "evidence" / "mae_results.json").write_text(json.dumps(out, indent=1))
    (ROOT / "evidence" / "mae_results.md").write_text(report(out))
    print(report(out))


def report(out) -> str:
    rows, loo = out["rows"], out["loo"]
    scoped = [r for r in rows if r["topic"] != "out of scope"]
    wrong_explained = [r for r in scoped if any(not e.endswith("_correct") for e in r["explained_by"])]
    traps = [r for r in scoped if any(e.endswith("_correct") for e in r["explained_by"])
             and any(not e.endswith("_correct") for e in r["explained_by"])]
    committed = [x for x in loo if x["committed_to"] != "no diagnosis"]
    L = ["# External answer key: MaE examples", "",
         "Source: MaE dataset, Otero, Druga and Lan (2024), MIT licence. Examples were written by learning "
         "researchers from published sources (mostly Ashlock 2006); they are not raw student data.", "",
         f"- In scope: {len(scoped)} of {len(rows)} examples (simplifying is not a topic of this tool).",
         f"- Reproduced exactly by a wrong rule in the library: {len(wrong_explained)} of {len(scoped)}.",
         f"- Right answer reached by a wrong rule (the correct answer trap, inside MaE itself): {len(traps)} examples "
         f"({', '.join(f'{r['mae']} ex {r['ex']}' for r in traps)}).",
         f"- Leave-one-out: the engine committed on {len(committed)} of {len(loo)} held-out examples and predicted the "
         f"student's exact answer on {sum(x['match'] for x in committed)} of those. "
         f"It gave no diagnosis on {len(loo) - len(committed)}.", "",
         "## Every example", "", "| MaE | Ex | Topic | Problem | Student wrote | Correct | Rules that give the student's answer |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['mae']} | {r['ex']} | {r['topic']} | {r['problem']} | {r['student']} | {r['correct']} | "
                 f"{', '.join(r['explained_by']) or 'none'} |")
    L += ["", "## Leave-one-out", "", "| MaE | Held out | Engine's choice | Confidence | Predicted | Actual | Match |",
          "|---|---|---|---|---|---|---|"]
    for x in loo:
        L.append(f"| {x['mae']} | {x['held_out']} | {x['committed_to']} | {x['confidence']} | {x['predicted']} | "
                 f"{x['actual']} | {'yes' if x['match'] else ('-' if x['committed_to'] == 'no diagnosis' else 'no')} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
