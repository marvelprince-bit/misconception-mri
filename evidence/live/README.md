# Live runs (Claude Sonnet 5.5, run by Emmanuel Ikeme on his own machine)

| File | Run | Design | Result |
|---|---|---|---|
| `claude_run2_seed0_raw.jsonl` | 2, 23 Nov 2026, 24 misconceptions x student 0 (run by Emmanuel) | commit 0bdf11d (with the revision step) | 22 right, 0 wrong, 2 no diagnosis, 13.12 questions on average |
| `claude_run3_seed0_raw.jsonl` | 3, 23 Nov 2026, same 24 students (run by Emmanuel) | commit 030b71f | 23 right, **1 wrong** (sub_parts_separately: Claude's rule applied the student's method only when regrouping was needed), 0 no diagnosis, 13.88 questions |
| `claude_run4_seed0_results.json`, `claude_run4_seed0_raw.jsonl` | 4, 23 Nov 2026, same 24 students (run by Claude in the cloud workspace with Emmanuel's key) | commit 881155e (rival check, no slip allowance for AI rules, every shape checked) | 23 right, 0 wrong, 1 no diagnosis (sub_parts_separately: revised rule failed a hidden answer), 15.5 questions |

Every prompt, reply, extracted code and verdict, exactly as written by `scripts/evaluate_ai.py`. Every log was checked for API keys before committing: none. Run 1 (20 right, 0 wrong, 4 no diagnosis, 11.8 questions) is reported from Emmanuel's screenshot; its raw log is not in the repository.

The two unresolved sessions are the basis of the question-choice fix in commit 0aeb365: search this file for `div_across_drop_remainder` and `sub_parts_separately`.

Live results on the final design are added here when they are run, never overwritten.
