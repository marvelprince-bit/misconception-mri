"""Clean unseen-rule test: held-out set 3, run ONCE on the frozen design.

Set 3 (mri/heldout_rules.py) was committed after the design was frozen and before
this script was first run. Same protocol as sets 1 and 2 in scripts/evaluate.py:
200 simulated students per rule, no slips, the rule is not in the tool's list, so
the only correct result is "no diagnosis".

Run:  python scripts/evaluate_set3.py   (writes evidence/set3_results.md and .json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate import extra_hidden_rules  # noqa: E402
from mri.heldout_rules import HELD_OUT_RULES_3  # noqa: E402

SEEDS = 200


def main() -> None:
    res = extra_hidden_rules(SEEDS, HELD_OUT_RULES_3)
    res["ALL"] = res.pop("ALL SIX")
    (ROOT / "evidence" / "set3_results.json").write_text(json.dumps(res, indent=1))
    lines = ["# Held-out set 3: wrong rules the tool has never seen", "",
             "Written after the design was frozen (commit 377934c) and committed (1d4d7f8) before this test "
             "was first run. Run once; nothing was changed afterwards. 200 simulated students per rule, no slips. "
             "The only correct result is 'no diagnosis'.", "",
             "| Rule | Sessions | No diagnosis % (correct) | Wrong rule named % | False all-clear % | Mean questions |",
             "|---|---|---|---|---|---|"]
    for k, v in res.items():
        name = f"**{k}**" if k == "ALL" else k
        lines.append(f"| {name} | {v['sessions']} | {v['no_diagnosis_pct']} | {v['wrong_pct']} | "
                     f"{v['false_all_clear_pct']} | {v['mean_questions']} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "evidence" / "set3_results.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
