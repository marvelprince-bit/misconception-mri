# Misconception MRI

**A student can score 100% on a worksheet and still be using a wrong rule. Misconception MRI finds the rule, proves it by predicting the student's next wrong answer before they give it, and says "no diagnosis" when the evidence is not there.**

Built for the Global AI Builder's Challenge (Devpost, November 21 to 28, 2026).

Topics: adding and subtracting negative numbers; adding, subtracting (including mixed numbers), multiplying and dividing fractions.

**Status, 23 Nov 2026:** engine, AI rule-writer (tested with stand-ins; first live Gemini test run by Emmanuel), demo, 67 unit tests and four evaluations work. Not yet done: a run with a live AI model, a user interface, and any use by real students. Every number below comes from simulated students or from the published MaE examples.

## The problem

Some wrong procedures produce the right answer on the easy questions that make up a first worksheet. On a 5-question ordinary worksheet, **16 of the 24 wrong rules in this tool scored 5/5 every time** (all 7 negative-number rules, 3 of 6 fraction-addition rules, all 4 subtraction rules, 2 of 3 multiplication rules). Answer checking cannot see them.

Research calls this the *correct answer trap*: AI tutors under-detect misconceptions when the student reaches a correct answer through flawed reasoning, and at realistic prevalence even a strong model raises about four false alarms per real detection (Imran and Bulathwela, 2026, arXiv:2605.23925). The trap is also visible in the MaE dataset itself: its note on misconception MaE14, example 2, reads "The learner got a correct answer, however he did not apply the correct algorithm."

## How it works

1. **Wrong rules are code.** Each known misconception is a small function that gives the answer a student holding it would give (`mri/rules.py`: 24 wrong rules plus the correct method for each topic).
2. **Questions chosen by disagreement.** The next question is the one where the remaining candidate rules disagree most about the answer.
3. **One miss is not proof.** A single answer that breaks a rule may be a careless slip, so the tool asks a look-alike question. Two misses on the same shape of question strike the rule out.
4. **Predictions before answers.** Before naming a wrong rule, the tool writes down the student's answer in advance on two new questions, chosen so that the rule predicts a *wrong* answer. A prediction that equals the correct answer does not count, because it cannot tell the wrong rule from correct reasoning.
5. **No all-clear without coverage.** "No misconception" is given only after every kind of question has been answered correctly.
6. **It can decline.** If no rule explains the answers, the result is "no diagnosis".
7. **AI writes a new rule when the list runs out** (`mri/proposer.py`, `mri/pipeline.py`). The model sees some of the student's wrong answers and writes a rule as code. That code
   - runs only if it passes a whitelist (`mri/sandbox.py`: one function, plain arithmetic, no imports, loops or attribute access, so it always finishes),
   - must reproduce every answer it was shown,
   - must also predict wrong answers that were hidden from it,
   - and then must pass the same prediction tests as any other rule.

   - and, before it can be named as the diagnosis, must match the student on **every shape of question not yet tested** (a kind of question, split by which number is larger in size), using the most contested question of each shape. This was added after a live Claude run: Claude wrote a rule that copied the student's "sign of the first number" rule on addition but did subtraction normally. It fit all 10 answers it was shown and a hidden one, because the student's subtraction answers happened to look correct, yet it is wrong on (−3) − (−5). The engine named it. With the shape check, a stand-in writer reproducing that failure is never named for that rule (0 of 40 sessions, previously 34 of 40); correct AI rules are still confirmed at the same rate, at a cost of about 4.6 extra questions on this path only.

   **Efficiency and second chances on this path** (`evidence/efficiency_report.md`, generated from `efficiency_before.json` and `efficiency_final.json`). A live Claude run on that student was safe (no diagnosis) but took 20 questions. Tracing it showed the AI had only seen wrong answers from one shape of question, and the hidden answers came from that same shape. Changes, all on the AI path only (every session that does not call the AI is byte-for-byte unchanged):
   - before calling the AI, collect wrong answers from varied shapes, closest and most contested first, keeping enough questions in reserve for rules that only show up in one shape;
   - when the wrong answers span three or more kinds, hide a whole kind from the AI so the check tests generalisation;
   - check an AI rule's riskiest shapes first and skip shapes where every known method agrees;
   - **one revision**: if the AI's rule fails the hidden answers, or is admitted and later contradicted by the student, a few new answers are collected where it failed and the AI may write one revised rule. Every answer ever hidden stays hidden and one new one is added, so the revision faces a stricter check; the prompt says only that the earlier rule failed, never which answers. (Switch off with `MRI_MAX_REVISIONS=0` or `MRI_REVISE_CONTRADICTED=0`.)

   | Stand-in writer (20 students per hidden rule) | Right | Wrong | No diagnosis | Mean questions |
   |---|---|---|---|---|
   | Writes the correct rule, before -> after | 90.6% -> 91.9% | 8.1% -> 8.1% | 1.2% -> 0.0% | 13.88 -> 12.64 |
   | Copies only the shapes it saw wrong, before -> after | 30.7% -> 42.9% | 9.3% -> 9.3% | 60.0% -> 47.9% | 16.57 -> 17.27 |

   The remaining "wrong" are all known look-alike rules named before the AI is called. Revision helps where the AI can extend a pattern (two misconceptions went from 16/20 and 7/20 right to 20/20); for a writer that never generalises it only costs questions, e.g. 18.2 questions on average for that student (14.5 with revision switched off). Whether the revision pays off with a real model is being tested live.

   **First live run, Claude Sonnet 5.5, one student per misconception (24 sessions, before the revision step):** 20 right, 0 wrong, 4 no diagnosis, 11.8 questions on average. 21 rules were admitted; the one that was not the student's real rule (`int_sign_of_first`) was caught during verification. No reply needed the repair step. With 24 sessions the true right-rate could plausibly be anywhere from about 63% to 95%.

   If the code is rejected for format or safety reasons (for example `/` instead of `//`, or type hints), the model gets **one** repair attempt, told only the rejection message. A rule that fails the student's answers is never retried, and hidden answers never appear in any prompt. Every prompt, reply and verdict is saved to `evidence/ai_raw_<writer>.jsonl`.

## Evidence

All tables are in `evidence/`. Simulated students follow one rule exactly, with optional careless slips. Real students are messier, so these results show the method behaves as designed; they do not show it works with real children.

**1. Right answers, wrong rule** (`evidence/results.md`, section 4). For every wrong rule that scored 5/5 on an ordinary worksheet, the tool then exposed it in 100% of cases, using 3 to 5 extra questions.

**2. Choosing questions by disagreement beats random questions** (5,800 sessions each):

| Setting | Right rule | No diagnosis | Mean questions |
|---|---|---|---|
| Disagreement, no slips | 100.0% | 0.0% | 4.54 |
| Random, no slips | 93.8% | 6.2% | 6.48 |
| Disagreement, 10% slips | 94.5% | 5.2% | 5.46 |
| Random, 10% slips | 86.0% | 13.8% | 7.29 |

**3. A wrong rule the tool has never seen.** The only correct result is "no diagnosis".

| Test | No diagnosis (correct) | Wrong rule named | False all-clear |
|---|---|---|---|
| Each library rule removed in turn (4,800 sessions; safeguards were designed on these, so flattering) | 91.7% | 3.2% | 5.0% |
| Held-out set 2 (6 rules, run once, starter design) | 88.7% | 11.3% | 0.0% |
| **Held-out set 3 (10 rules, all five topics, written after the design was frozen, run once; 2,000 sessions)** | **99.0%** | **0.1%** | **0.9%** |

Set 3 was written by the same AI that designed the safeguards, so it may share blind spots; set 2 is the more conservative figure. The honest range for a rule the tool has never seen is about **1 to 11 misdiagnoses in 100**. Commit order proves set 3 came after the freeze: `377934c` (freeze), `1d4d7f8` (set 3), then the results.

**4. External answer key: MaE** (`evidence/mae_results.md`). 40 examples transcribed from the MaE dataset (fractions and negative numbers).
- 31 of 36 in-scope examples are reproduced exactly by a wrong rule in the library.
- Leave-one-out: shown the other examples of the same misconception, the engine committed to a diagnosis on 23 held-out examples and **predicted the student's exact answer on all 23**. It declined on 12, including all of MaE18, whose published label ("unsure of the correct sign") describes no stable rule.
- MaE examples were written by learning researchers from published sources; they are not raw student data.

**5. AI rule-writer, tested with stand-ins** (`evidence/ai_results_standins.md`, 480 sessions each; no live model yet):

| Stand-in writer | Hidden-answer check | Rules admitted | Admitted rules that were right |
|---|---|---|---|
| Perfect (writes the true rule) | on | 90.6% | 100% |
| Cheater (memorises the answers it was shown) | on | **0.0%** | n/a |
| Cheater | off | 90.6% | **0%** |
| Outage (service down) | on | 0.0% | n/a, session continues safely |
| Messy formatting (right idea), repair on | on | 91.7% | 100% |
| Messy formatting, repair off | on | 0.0% | n/a |

**6. Careless slips:** right rule found 94.5% of the time at 10% slips, 75.2% at 20%, 47.3% at 30%; the rest end as "no diagnosis", almost never a wrong diagnosis (0.1 to 0.2%).

## Limitations

- **Narrow misconceptions can hide behind an all-clear.** The all-clear tests one question of each kind. A wrong rule that only fires on a narrow sub-case can pass. When such a rule is missing from the list, false all-clears reach 17% in division and 11.5% in subtraction. Finer question kinds are the planned fix, to be followed by a new unseen-rule set.
- **Students with no stable rule.** In subtraction and multiplication the wrong rules fire only on narrow cases, so a student mixing them answers correctly most of the time; the tool then often gives an all-clear (24.5% overall across topics).
- One set-3 rule ("adds the whole number to the top") got a false all-clear 9% of the time, because a question like 2/5 × 2 gives the same answer either way.
- Simplifying fractions is not covered (answers are compared by value).
- The shape check is applied to AI-written rules only. Applying it to known rules too would stop known look-alikes from being named (2.5% of sessions where the student's rule is missing from the list) but cut correct diagnoses in normal sessions from 93.6% to 71.0% and nearly double the questions, so it is off by default (`diagnosis_needs_all_kinds="all"` turns it on).
- No live AI model has been run yet. No user interface yet. No real students.

## Prior work, and what is new

- **MalruleLib** (Chen, Liu and Sonkar, ACL 2026): 101 wrong rules written as code, and a measured drop in model accuracy from 66% to 40% on cross-template misconception prediction. [Paper](https://ar5iv.labs.arxiv.org/html/2601.03217). Its licence forbids evaluating closed-source models, so no code, rules or data from it are used here.
- **The correct answer trap** (Imran and Bulathwela, 2026): 343 cases in 20,964 Eedi responses, 71% of them in integer subtraction and equivalent fractions. [Paper](https://arxiv.org/html/2605.23925).
- **MaE** (Otero, Druga and Lan, 2024, MIT licence): 55 misconceptions, 220 examples; our external answer key. [Repository](https://github.com/nancyotero-projects/math-misconceptions).

What is different here: the tool never labels a misconception from one answer. It chooses questions to separate rules, tests its own diagnosis with wrong-answer predictions made in advance, lets an AI write new rules only when they predict answers the AI never saw, and declines when the evidence is not there.

## Quick start

Python 3.10 or newer. Nothing to install.

```bash
python -m unittest discover -s tests              # 67 tests
python scripts/demo.py --list                     # every rule the tool knows
python scripts/demo.py --student sub_smaller_from_larger
python scripts/demo.py --student div_across_drop_remainder
python scripts/demo.py --interactive --domain frac_sub   # you answer as the student
python scripts/evaluate.py                        # rebuilds evidence/results.md (about 7 minutes)
python scripts/evaluate_set3.py                   # the clean unseen-rule test (seconds)
python scripts/evaluate_mae.py                    # the MaE answer key
python scripts/evaluate_ai.py --writer cheat      # the admission check, no key needed
python scripts/evaluate_efficiency.py --compare before final   # AI-path efficiency report
```

Live AI rule-writer (either provider; never commit a key, see `.env.example`):

```bash
export ANTHROPIC_API_KEY=...   # or GEMINI_API_KEY=...
python scripts/evaluate_ai.py --writer gemini --seeds 2 --domain integers   # small, cheap first run
python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai claude
```

## AI disclosure

- **AI in the product:** a language model writes candidate wrong rules as code when no known rule fits. The code is sandboxed and must predict answers it never saw before it can be used.
- **AI in development:** Perplexity Computer (starter engine and AI pipeline) and Claude (MaE answer key, three new fraction topics, the merge, held-out set 3). Every AI contribution and its human check is recorded in [`DEVLOG.md`](DEVLOG.md).

## Credits and licence

- MaE dataset: Nancy Otero, Stefania Druga, Andrew Lan. MIT License.
- Misconception descriptions in MaE draw on Ashlock (2006), *Error Patterns in Computation*.
- This project: MIT. See [`LICENSE`](LICENSE).
