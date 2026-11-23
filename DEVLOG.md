# Development log (AI-assisted development)

Rubric item A4 gives points only when a PERSON checked a specific piece of AI-made work, says what the check found, and says what was decided. Reporting AI use alone earns nothing.

**Fill in the "Human check" and "Decision" columns yourself, truthfully, only after doing the check. Leave a row blank rather than invent a check.**

## AI tools used

| Tool | What it produced |
|---|---|
| Perplexity Computer | The starter engine (probability model with slips, look-alike re-tests, predictions on new kinds of question), the sandbox for AI-written code, the AI rule-writer, stand-in writers, integer and fraction-addition rules, held-out sets 1 and 2, demo, 29 tests. |
| Claude (Anthropic), in a cloud workspace with code execution | Licence checks, the MaE answer key and its evaluation, the subtraction, multiplication and division topics, the merge, the Claude client, the "distinctive prediction" change, held-out set 3, 11 more tests, this log's AI rows. An earlier standalone engine (commit ac989dd) was replaced by the merge. |

## Log

| # | Date (CST) | AI tool | AI contribution | Automated check and result | Human check (Emmanuel): what was reviewed, what was found | Decision: keep, change, reject |
|---|---|---|---|---|---|---|
| 1 | 2026-11-23 | Perplexity | 13 wrong rules for integers and fraction addition (`mri/rules.py`) | Unit tests; demo per rule | Suggested check: work 3 questions per rule by hand and compare with `python scripts/demo.py --student <id>` | |
| 2 | 2026-11-23 | Perplexity | Claim: choosing questions by disagreement beats random questions | `python scripts/evaluate.py`, see `evidence/results.md` | Suggested check: run it yourself and compare the numbers | |
| 3 | 2026-11-23 | Perplexity | Sandbox for AI-written code (`mri/sandbox.py`) | Tests try harmful snippets | Suggested check: try to get a harmful snippet past it, add it to `tests/test_mri.py` | |
| 4 | 2026-11-23 | Claude | Licence check: MaE is MIT; MalruleLib forbids evaluating closed-source models, so none of its code or data is used | Read both LICENSE files in the cloned repositories | | |
| 5 | 2026-11-23 | Claude | Transcribed 40 MaE examples (fractions and integers) into `data/mae_examples.json` | Every example is listed next to its MaE id in `evidence/mae_results.md` | Suggested check: compare 10 rows with the original `data.json` from the MaE repository | |
| 6 | 2026-11-23 | Claude | 13 wrong rules for subtracting, multiplying and dividing fractions | Rules reproduce the MaE examples they were written from; reference code matches on every question | Suggested check: work 3 questions per rule by hand | |
| 7 | 2026-11-23 | Claude | Found a weakness in the starter design: a "prediction test" could be a question where the wrong rule gives the correct answer, which proves nothing. Changed the engine to prefer questions where the rule predicts a wrong answer, and to count only those | Demo transcripts before and after; 40 tests pass | Suggested check: read one demo transcript and confirm every counted prediction differs from the correct answer | |
| 8 | 2026-11-23 | Claude | Wrote held-out set 3 (10 unseen rules) after freezing the design; replaced one rule that was identical to a library rule before any result was seen | Commit order: freeze 377934c, set 3 1d4d7f8, then results | Suggested check: confirm the commit order in `git log` | |
| 9 | 2026-11-23 | Claude | Claude client for the live AI rule-writer (`ClaudeProposer`) | Test: fails safely with no key | Suggested check: run `python scripts/evaluate_ai.py --writer claude --seeds 5` with your key; read 5 admitted and 5 rejected rules by hand | |

## Later AI help

Add a row each time AI writes or changes something: date, tool, what it made, how you checked it, what you found, what you decided.
