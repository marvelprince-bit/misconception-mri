# Live runs (Claude Sonnet 5.5, run by Emmanuel Ikeme on his own machine)

| File | Run | Design | Result |
|---|---|---|---|
| `claude_run2_seed0_raw.jsonl` | 2, 23 Nov 2026, 24 misconceptions x student 0 | commit 0bdf11d (with the revision step) | 22 right, 0 wrong, 2 no diagnosis, 13.12 questions on average |

Every prompt, reply, extracted code and verdict, exactly as written by `scripts/evaluate_ai.py`. Checked for API keys before committing: none. Run 1 (20 right, 0 wrong, 4 no diagnosis, 11.8 questions) is reported from Emmanuel's screenshot; its raw log is not in the repository.

The two unresolved sessions are the basis of the question-choice fix in commit 0aeb365: search this file for `div_across_drop_remainder` and `sub_parts_separately`.

Live results on the final design are added here when they are run, never overwritten.
