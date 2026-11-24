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

| 10 | 2026-11-23 | Claude | Emmanuel's first live Gemini run (3 calls: 2 rejected as malformed, 1 failed verification) was reviewed with an outside AI review. Kept: stricter prompt with a valid example, robust code extraction, one repair attempt for format or safety errors only, raw reply logging. Rejected: loosening admission for student slips, because the live test's students make no slips. | 52 tests pass; messy-format stand-in admitted 91.7% with repair, 0% without; cheater still 0% | Suggested check: rerun the live test, open `evidence/ai_raw_gemini.jsonl` and read why each reply was accepted or rejected | |

| 11 | 2026-11-23 | Claude | Emmanuel's live Claude run found an AI rule (sign of the first number, addition only) that passed admission and was diagnosed although it is wrong on (-3) - (-5). Reproduced with a stand-in writer (34 of 40 false diagnoses), traced to coarse kinds: subtraction had been "tested" on questions where the student's wrong rule looked correct. Fix: AI-written rules must match the student on every untested shape before being named. Kept from the outside review: test across operations, choose contested questions. Not adopted: more confirmations of the same kind (would not have helped), and the check for known rules too (measured: correct diagnoses 93.6% to 71.0%). | False diagnoses for that rule 34/40 to 0/40; good AI rules still 90.6% right, 1.2% unresolved; 58 tests pass | Suggested check: rerun the live Claude test on integers and confirm int_sign_of_first now ends with no diagnosis or the full rule | |

| 12 | 2026-11-23 | Claude | Emmanuel's next live Claude run on int_sign_of_first was safe but took 20 questions. Traced question by question with a stand-in that reproduces it: the AI saw wrong answers from one shape only, and the hidden answers came from the same shape; verification then spent questions on shapes this student never gets wrong. Changed exploration (varied, budget-aware), admission (hide a whole kind when wrong answers span 3+ kinds) and AI-rule verification (riskiest shapes first, uncontested shapes skipped). Rejected after measuring: hiding a kind when only 2 kinds are wrong (lowered correct results). Baseline recorded and committed before any change (`evidence/efficiency_before.json`). | Same right, wrong and no-diagnosis counts for every hidden rule; questions for this case 18.2 to 14.5; non-AI sessions byte-for-byte unchanged (fingerprint of 580 sessions); 63 tests pass | Suggested check: rerun `python scripts/evaluate_ai.py --writer claude --seeds 2 --domain integers` and compare the question count for int_sign_of_first with the earlier 20 | |

| 13 | 2026-11-23 | Claude | Emmanuel's live Claude run on all 24 misconceptions (1 student each): 20 right, 0 wrong, 4 no diagnosis, 11.8 questions. An outside review proposed revising failed hypotheses, better questions, and final verification. Kept: one revision after a rule fails the hidden answers or is later contradicted, with all hidden answers kept hidden plus one new. Not needed: final verification (already required) and disagreement-based questions (already the core). Not promised: 24/24 right with 0 unresolved, because forcing a diagnosis when the AI's rule is wrong would risk a wrong one, and tuning on the same 24 sessions would overfit the evidence. | Partial writer right 30.7% to 42.9%, wrong unchanged; cheater still never admitted; efficiency test rewritten openly (with revision off it still averages under 16 questions for int_sign_of_first); 67 tests pass | Suggested check: rerun the live Claude test and compare with the 20/0/4 result above | |

## Later AI help

Add a row each time AI writes or changes something: date, tool, what it made, how you checked it, what you found, what you decided.
