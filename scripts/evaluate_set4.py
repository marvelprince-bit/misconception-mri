"""Clean unseen-rule test: held-out set 4, run ONCE on the frozen design.

Set 4 (mri/heldout_rules.py) was committed after the design was frozen and before
this script was first run. Same protocol as sets 1 and 2 in scripts/evaluate.py:
200 simulated students per rule, no slips, the rule is not in the tool's list, so
the only correct result is "no diagnosis".

Run:  python scripts/evaluate_set3.py   (writes evidence/set4_results.md and .json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate import extra_hidden_rules  # noqa: E402
from mri.heldout_rules import HELD_OUT_RULES_4  # noqa: E402

SEEDS = 200


def main() -> None:
    out = ROOT / "evidence" / "set4_results.json"
    if out.exists():
        sys.exit("evidence/set4_results.json exists: set 4 is run once. Not overwritten.")
    res = extra_hidden_rules(SEEDS, HELD_OUT_RULES_4)
    res["ALL"] = res.pop("ALL SIX")
    out.write_text(json.dumps(res, indent=1))
    lines = ["# Held-out set 4: wrong rules the tool has never seen", "",
             "Written after the design was frozen (commit aacb5fd) and committed before this test "
             "was first run. Run once; nothing was changed afterwards. 200 simulated students per rule, no slips. "
             "The only correct result is 'no diagnosis'.", "",
             "| Rule | Sessions | No diagnosis % (correct) | Wrong rule named % | False all-clear % | Mean questions |",
             "|---|---|---|---|---|---|"]
    for k, v in res.items():
        name = f"**{k}**" if k == "ALL" else k
        lines.append(f"| {name} | {v['sessions']} | {v['no_diagnosis_pct']} | {v['wrong_pct']} | "
                     f"{v['false_all_clear_pct']} | {v['mean_questions']} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "evidence" / "set4_results.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
