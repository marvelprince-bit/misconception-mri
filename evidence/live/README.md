# Live runs (Claude Sonnet 5.5)

| File | Run | Design | Result |
|---|---|---|---|
| `claude_run2_seed0_raw.jsonl` | 2, 23 Nov 2026, 24 misconceptions x student 0 | commit 0bdf11d (with the revision step) | 22 right, 0 wrong, 2 no diagnosis, 13.12 questions on average |
| `claude_run3_seed0_raw.jsonl` | 3, 23 Nov 2026, same 24 students | commit 030b71f | 23 right, **1 wrong** (sub_parts_separately: Claude's rule applied the student's method only when regrouping was needed), 0 no diagnosis, 13.88 questions |
| `claude_run4_seed0_results.json`, `claude_run4_seed0_raw.jsonl` | 4, 23 Nov 2026, same 24 students | commit 881155e (rival check, no slip allowance for AI rules, every shape checked) | 23 right, 0 wrong, 1 no diagnosis (sub_parts_separately: revised rule failed a hidden answer), 15.5 questions |
| `claude_run5_seed20261124_*` | 5, 24 Nov, new student 20261124 | 17d6d6c (repair step) | 24 right, 0 wrong, 0 no diagnosis, 15.96 questions |
| `claude_run6_seed0_*` | 6, 24 Nov, student 0 | 17d6d6c | 22 right, 0 wrong, 2 no diagnosis (subtraction: rule missing a condition; division: revision had no new wrong answer) |
| `claude_run7_seed0_*` | 7, 24 Nov, student 0 | 374c3d4 (missing-condition edits, extra revision questions) | 24 right, 0 wrong, 0 no diagnosis. The original results file scored the repaired subtraction rule 'wrong' by mistake (it scored the AI's last proposal, not the rule named); `_results_rescored.json` is the replay with corrected scoring |
| `claude_run8_seed20261124_*` | 8, 24 Nov, new student 20261124 | ff09e6d | 23 right, **1 wrong** (division: a max() branch never tried on a real answer) |
| `claude_run9_seed20261124_*` | 9, 24 Nov, new student 20261124 | **f9f4510 (final: decision coverage)** | **24 right, 0 wrong, 0 no diagnosis**, 16.08 questions |
| `claude_run10_seed0_*` | 10, 24 Nov, student 0 | **f9f4510 (final)** | **24 right, 0 wrong, 0 no diagnosis**, 15.62 questions |

Every run is listed, including the ones that missed.

**Check runs 9 and 10 yourself, without an API key:** `python scripts/evaluate_ai.py --writer replay:evidence/live/claude_run10_seed0_raw.jsonl --seeds 1` (and for run 9 add `--seed-offset 20261124`). The replay feeds Claude's saved replies to the code for the exact same prompts and stops if any prompt differs, so it reproduces the run exactly on commit f9f4510 or later code that sends the same prompts.

Every prompt, reply, extracted code and verdict, exactly as written by `scripts/evaluate_ai.py`. Every log was checked for API keys before committing: none. Run 1 (20 right, 0 wrong, 4 no diagnosis, 11.8 questions) is reported from a screenshot of the run; its raw log is not in the repository.

The two unresolved sessions are the basis of the question-choice fix in commit 0aeb365: search this file for `div_across_drop_remainder` and `sub_parts_separately`.

Live results on the final design are added here when they are run, never overwritten.
