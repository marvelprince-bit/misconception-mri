# Misconception MRI

**A student can score 100% on a worksheet and still be using a wrong rule. Misconception MRI finds the rule, proves it by predicting the student's next wrong answer before they give it, and says "no diagnosis" when the evidence is not there.**

Built for the Global AI Builder's Challenge (Devpost, November 21 to 28, 2026).

Topics: adding and subtracting negative numbers; adding, subtracting (including mixed numbers), multiplying and dividing fractions.

**Status, 25 Nov 2026:** engine, AI rule-writer (ten live Claude runs; the final design scored 24/24 with 0 wrong in both of its runs), web interface, 93 unit tests and five evaluations work. Not yet done: any use by real students. Every number below comes from simulated students or from the published MaE examples. The Devpost description is in [`DEVPOST.md`](DEVPOST.md).

## The problem

Some wrong procedures produce the right answer on the easy questions that make up a first worksheet. On a 5-question ordinary worksheet, **16 of the 24 wrong rules in this tool scored 5/5 every time** (all 7 negative-number rules, 3 of 6 fraction-addition rules, all 4 subtraction rules, 2 of 3 multiplication rules). Answer checking cannot see them.

Research calls this the *correct answer trap*: AI tutors under-detect misconceptions when the student reaches a correct answer through flawed reasoning, and at realistic prevalence even a strong model raises about four false alarms per real detection (Imran and Bulathwela, 2026, arXiv:2605.23925). The trap is also visible in the MaE dataset itself: its note on misconception MaE14, example 2, reads "The learner got a correct answer, however he did not apply the correct algorithm."

## How it works

1. **Wrong rules are code.** Each known misconception is a small function that gives the answer a student holding it would give (`mri/rules.py`: 24 wrong rules plus the correct method for each topic).
2. **Questions chosen by disagreement.** The next question is the one where the remaining candidate rules disagree most about the answer.
3. **One miss is not proof.** A single answer that breaks a rule may be a careless slip, so the tool asks a look-alike question. Two misses on the same shape of question strike the rule out.
4. **Predictions before answers.** Before naming a wrong rule, the tool writes down the student's answer in advance on two new questions, chosen so that the rule predicts a *wrong* answer. A prediction that equals the correct answer does not count, because it cannot tell the wrong rule from correct reasoning.
5. **No all-clear without coverage.** "No misconception" is given only after every kind of question has been answered correctly. Kinds are fine-grained (for subtraction: two mixed numbers vs a mixed number minus a fraction, and how the bottoms relate; for division: whether tops and bottoms divide straight across).
6. **One risk check before naming a known wrong rule.** One more question, on the untested shape most likely to expose a look-alike: where the student's error pattern would show if it is wider than the rule says (every wrong answer the right answer made positive, say), else the shape nearest to the wrong answers (the same question with the order swapped), else where the rule claims the correct answer.
7. **Questions free of coincidences.** Confirmations and re-tests avoid numbers that line up by accident (equal tops, gaps equal to the bottoms' gap), because on those a different procedure gives the same answer.
8. **It can decline.** If no rule explains the answers, the result is "no diagnosis".
9. **AI writes a new rule when the list runs out** (`mri/proposer.py`, `mri/pipeline.py`). The model sees some of the student's wrong answers and writes a rule as code. That code
   - runs only if it passes a whitelist (`mri/sandbox.py`: one function, plain arithmetic, no imports, loops or attribute access, so it always finishes),
   - must reproduce every answer it was shown,
   - must also predict wrong answers that were hidden from it,
   - and then must pass the same prediction tests as any other rule,
   - may not miss a single answer afterwards (no "careless slip" allowance: the AI wrote it to fit),
   - must be checked on every shape of question not yet asked, even where all known methods agree,
   - and must survive a **rival check** (`mri/rivals.py`): the tool makes small sandboxed edits of the rule's code (a condition dropped or added, abs() added or dropped, a flipped comparison). If any edit also fits every answer, it asks the question that separates them; if a rival survives, no diagnosis.
   - **Decision coverage** (`mri/paths.py`): every outcome of every decision in the rule's code (each `if` true and false, which side of `max`/`min` wins, the sign inside `abs`, whether `a // b` is zero or leaves a remainder) must be tried on at least one of the student's answers before the rule is named.
   - **Repair:** if the AI's rule fails, the same small edits are tried as repaired rules. Any that fit every answer so far enter as new AI rules and must pass every check above on NEW questions before they can be named. (Switch off with `MRI_REPAIR=0`.)

   - and, before it can be named as the diagnosis, must match the student on **every shape of question not yet tested** (a kind of question, split by which number is larger in size), using the most contested question of each shape. This was added after a live Claude run: Claude wrote a rule that copied the student's "sign of the first number" rule on addition but did subtraction normally. It fit all 10 answers it was shown and a hidden one, because the student's subtraction answers happened to look correct, yet it is wrong on (−3) − (−5). The engine named it. With the shape check, a stand-in writer reproducing that failure is never named for that rule (0 of 40 sessions, previously 34 of 40); correct AI rules are still confirmed at the same rate, at a cost of about 4.6 extra questions on this path only.

   **Efficiency and second chances on this path** (`evidence/efficiency_report.md`, generated from `efficiency_before.json` and `efficiency_v3.json`). A live Claude run on that student was safe (no diagnosis) but took 20 questions. Tracing it showed the AI had only seen wrong answers from one shape of question, and the hidden answers came from that same shape. Changes on the AI path (when made, every session that does not call the AI was byte-for-byte unchanged; the later finer kinds, risk check and coincidence-free questions do change the known-rule path, and are measured separately below):
   - before calling the AI, collect wrong answers from varied shapes, closest and most contested first, keeping enough questions in reserve for rules that only show up in one shape;
   - when the wrong answers span three or more kinds, hide a whole kind from the AI so the check tests generalisation;
   - check an AI rule's riskiest shapes first and skip shapes where every known method agrees;
   - **one revision**: if the AI's rule fails the hidden answers, or is admitted and later contradicted by the student, a few new answers are collected where it failed and the AI may write one revised rule. Every answer ever hidden stays hidden and one new one is added, so the revision faces a stricter check; the prompt says only that the earlier rule failed, never which answers. (Switch off with `MRI_MAX_REVISIONS=0` or `MRI_REVISE_CONTRADICTED=0`.)

   | Stand-in writer (20 students per hidden rule, students 0 to 19) | Right | Wrong | No diagnosis | Mean questions |
   |---|---|---|---|---|
   | Writes the correct rule: before these changes -> now | 90.6% -> **100%** | 8.1% -> **0%** | 1.2% -> 0% | 13.88 -> 13.81 |
   | Copies only the shapes it saw wrong: before -> now | 30.7% -> 42.9% | 9.3% -> **0%** | 60.0% -> 57.1% | 16.57 -> 18.44 |
   | Copies only the shapes it saw wrong, **final design** (repair, coverage; students 100 to 109) | **100%** | **0%** | 0% | 28.07 |
   | Writes the correct rule, **final design** (students 100 to 109) | **100%** | **0%** | 0% | 15.94 |

   One number got worse and is kept visible: with the partial writer, incomplete AI rules pass the hidden-answer check more often (27.9% -> 48.6% of sessions), because the more varied questions leave fewer hidden answers in the shapes it copied. The shape check catches every one of them before it is named, so its final wrong rate is 0%. The hidden-answer check alone is not enough; the two checks work together.

   On students 100 to 119, never used during development: 100% right and 0% wrong for the correct-rule writer, 42.1% right and 0% wrong for the partial one. The earlier 8.1% "wrong" was not only known look-alikes: it also included false all-clears for narrow rules (division and subtraction), removed by the finer kinds.

   **Live development benchmark, Claude Sonnet 5.5, one student per misconception (24 sessions each).** These 24 cases are the benchmark the AI path was developed against: each run's failures were traced in the raw logs (`evidence/live/`) and fixed. Independence comes from new simulated students, held-out rules and outside evaluation, not from these 24 cases.

   | Run | Right | Wrong | No diagnosis | Mean questions |
   |---|---|---|---|---|
   | 1, before the revision step | 20 | 0 | 4 | 11.8 |
   | 2, with the revision step | 22 | 0 | 2 | 13.1 |
   | 3, coincidence-free questions | 23 | **1** | 0 | 13.9 |
   | 4, rival check, every shape, no slip allowance | 23 | 0 | 1 | 15.5 |
   | 5 (new student), repair step | 24 | 0 | 0 | 16.0 |
   | 6, repair step | 22 | 0 | 2 | 15.5 |
   | 7, missing-condition edits | 24 | 0 | 0 | 15.7 |
   | 8 (new student) | 23 | **1** | 0 | 16.0 |
   | **9 (new student), final design** | **24** | **0** | **0** | 16.1 |
   | **10, final design** | **24** | **0** | **0** | 15.6 |

   In runs 1 and 2 every admitted rule that was named matched the student's real rule on every question. The two unresolved cases in run 2 were traced in Claude's raw replies (`ai_raw_claude.jsonl`): both times Claude wrote the **simplest rule that fitted the answers it was shown**, and those answers were numerical coincidences. In division every example had bottoms whose ratio rounds down to 1, so "divide the tops only" fitted. In subtraction the fraction parts came out as whole numbers, so "subtract the wholes" fitted. The fix changes which questions are asked, not what is accepted: questions free of coincidences, and revision questions aimed where the failed rule makes a bold claim. A stand-in that replays Claude's own two decoy rules goes from 4/20 and 12/20 right to 20/20 and 20/20. Run 3's one wrong diagnosis: Claude's rule applied the student's subtraction method only when regrouping was needed, and the final check skipped the question shapes where all known methods agree, which is exactly where the two differ. Run 4 added the rival check, every-shape checking and no slip allowance: the case ended in no diagnosis instead. The repair step was then added: given Claude's run-3 rule, stand-ins reach the student's real rule in 20 of 20 sessions, never a wrong one. Run 8's wrong diagnosis came from a branch hidden inside `max(1, d1 // d2)` that no question had tried; the final design adds **decision coverage** (below). On the final design (commit f9f4510) both live runs, student 0 and a new student, gave 24 right and 0 wrong, and both replay exactly from their raw logs with no API key (`evidence/live/README.md`). Every live run is listed above, including the misses. With 24 sessions, 24/24 would still be consistent with a true rate of roughly 86% or more, so fresh students (`--seed-offset 100`) are part of the validation.

   If the code is rejected for format or safety reasons (for example `/` instead of `//`, or type hints), the model gets **one** repair attempt, told only the rejection message. A rule that fails the student's answers is never retried, and hidden answers never appear in any prompt. Every prompt, reply and verdict is saved to `evidence/ai_raw_<writer>.jsonl`.

## Evidence

All tables are in `evidence/`. Simulated students follow one rule exactly, with optional careless slips. Real students are messier, so these results show the method behaves as designed; they do not show it works with real children.

**1. Right answers, wrong rule** (`evidence/results.md`, section 4). For every wrong rule that scored 5/5 on an ordinary worksheet, the tool then exposed it in 100% of cases, using 3 to 5 extra questions.

**2. Choosing questions by disagreement beats random questions** (5,800 sessions each):

| Setting | Right rule | No diagnosis | Mean questions |
|---|---|---|---|
| Disagreement, no slips | 100.0% | 0.0% | 5.53 |
| Random, no slips | 92.5% | 7.5% | 7.31 |
| Disagreement, 10% slips | 93.1% | 6.7% | 6.47 |
| Random, 10% slips | 83.8% | 16.1% | 8.15 |

No setting ever names a wrong rule for a student whose rule is in the list.

**3. A wrong rule the tool has never seen.** The only correct result is "no diagnosis".

| Test | No diagnosis (correct) | Wrong rule named | False all-clear |
|---|---|---|---|
| Each library rule removed in turn (4,800 sessions; safeguards were designed on these, so flattering) | 100.0% | 0.0% | 0.0% |
| Held-out set 2 (6 rules, starter design era; no longer clean) | 89.1% | 10.9% | 0.0% |
| Held-out set 3 (10 rules, run once on the design of commit 377934c; no longer clean) | 99.0% | 0.1% | 0.9% |
| **Held-out set 4 (12 rules, all five topics, written after the final freeze `aacb5fd`, committed `1b40b45` before any run, run once; 2,400 sessions)** | **99.96%** | **0.0%** | **0.04% (1 session)** |

Sets 3 and 4 were written by the same AI that designed the safeguards, so they may share blind spots. Set 2 is the more conservative figure, and its one bad rule ("adds tops and bottoms only when the bottoms differ") is still named as its look-alike 65.5% of the time; it is not tuned against, because a fix would need yet another clean set. The honest range for a rule the tool has never seen is about **0 to 11 misdiagnoses in 100**. Five first-choice set-4 rules were replaced before any run because they were identical to existing rules or never fired; each replacement is noted in the code.

**4. External answer key: MaE** (`evidence/mae_results.md`). 40 examples transcribed from the MaE dataset (fractions and negative numbers).
- 31 of 36 in-scope examples are reproduced exactly by a wrong rule in the library.
- Leave-one-out: shown the other examples of the same misconception, the engine committed to a diagnosis on 23 held-out examples and **predicted the student's exact answer on all 23**. It declined on 12, including all of MaE18, whose published label ("unsure of the correct sign") describes no stable rule.
- MaE examples were written by learning researchers from published sources; they are not raw student data.

**5. AI rule-writer, tested with stand-ins** (`evidence/ai_results_standins.md`, 480 sessions each, students 0 to 19; students 100 to 119 give the same rates):

| Stand-in writer | Hidden-answer check | Rules admitted | Admitted rules that were right |
|---|---|---|---|
| Perfect (writes the true rule) | on | 100% | 100% |
| Simplest-fit (replays Claude's live decoys) | on | 100% | 100% |
| Cheater (memorises the answers it was shown) | on | **0.0%** | n/a |
| Cheater on set-4 rules (never seen) | on | **0.0%** | n/a |
| Cheater on set-4 rules | off | 94.2% | **0%** |
| Outage (service down) | on | 0.0% | n/a, session continues safely |
| Messy formatting (right idea), repair on | on | 100% | 100% |
| Messy formatting, repair off | on | 0.0% | n/a |

**6. Careless slips:** right rule found 93.1% of the time at 10% slips, 72.5% at 20%, 43.6% at 30%; the rest end as "no diagnosis", almost never a wrong diagnosis (0 to 0.1% wrong rule, 0.2% false all-clear).

## Limitations

- **Careless slips can still hide a look-alike.** With the student's rule missing from the list and 10% slips, 0.3% of sessions (fresh students 100 to 129) named a look-alike, where a slip masked the difference.
- **Students with no stable rule.** In subtraction and multiplication the wrong rules fire only on narrow cases, so a student mixing them answers correctly most of the time; the tool then often gives an all-clear (16.8% overall across topics, down from 24.5%; 1.6% name a wrong rule).
- **One held-out look-alike remains** (set 2, see above), and one set-4 session gave a false all-clear: "multiplies each top by its own bottom" agrees with the correct method whenever the tops are equal.
- **The live 24-session runs are small.** A perfect score on 24 sessions does not prove perfect accuracy; it is reported together with fresh simulated students.
- Simplifying fractions is not covered (answers are compared by value).
- No user interface yet. No real students.

## Prior work, and what is new

- **MalruleLib** (Chen, Liu and Sonkar, ACL 2026): 101 wrong rules written as code, and a measured drop in model accuracy from 66% to 40% on cross-template misconception prediction. [Paper](https://ar5iv.labs.arxiv.org/html/2601.03217). Its licence forbids evaluating closed-source models, so no code, rules or data from it are used here.
- **The correct answer trap** (Imran and Bulathwela, 2026): 343 cases in 20,964 Eedi responses, 71% of them in integer subtraction and equivalent fractions. [Paper](https://arxiv.org/html/2605.23925).
- **MaE** (Otero, Druga and Lan, 2024, MIT licence): 55 misconceptions, 220 examples; our external answer key. [Repository](https://github.com/nancyotero-projects/math-misconceptions).

What is different here: the tool never labels a misconception from one answer. It chooses questions to separate rules, tests its own diagnosis with wrong-answer predictions made in advance, lets an AI write new rules only when they predict answers the AI never saw, and declines when the evidence is not there.

## Web interface

```
pip install -r requirements.txt
python app.py        # open http://127.0.0.1:5000
```

**Watch a scan:** pick a topic and the rule a simulated student secretly follows, and watch the tool's questions one at a time. You see each prediction written before the student answers, how its beliefs narrow, and the diagnosis with the evidence and practice questions. Tick "Take this rule off the tool's list" to make it meet a rule it has never seen: Claude then writes the rule as code (live with `ANTHROPIC_API_KEY`, otherwise replayed exactly from saved live run 10). Three ready cases: the correct-answer trap, a rule the tool has never seen, and a cheating AI.

**Be the student:** answer the questions yourself, mistakes included, and see whether it finds your rule.

The interface runs the same engine as the tests (`mri/scan.py` only records what happens).

## Quick start

Python 3.10 or newer. Nothing to install.

```bash
python -m unittest discover -s tests              # 93 tests
python scripts/demo.py --list                     # every rule the tool knows
python scripts/demo.py --student sub_smaller_from_larger
python scripts/demo.py --student div_across_drop_remainder
python scripts/demo.py --interactive --domain frac_sub   # you answer as the student
python scripts/evaluate.py                        # rebuilds evidence/results.md (about 16 minutes)
python scripts/evaluate_set4.py                   # the clean unseen-rule test (run once; refuses to overwrite)
python scripts/evaluate_mae.py                    # the MaE answer key
python scripts/evaluate_ai.py --writer cheat      # the admission check, no key needed
python scripts/evaluate_efficiency.py --compare before final   # AI-path efficiency report
```

Live AI rule-writer (either provider; never commit a key, see `.env.example`):

```bash
export ANTHROPIC_API_KEY=...   # or GEMINI_API_KEY=...
python scripts/evaluate_ai.py --writer replay:evidence/live/claude_run10_seed0_raw.jsonl --seeds 1   # replay live run 10, no key needed
python scripts/evaluate_ai.py --writer claude --seeds 1                      # the 24 misconceptions, student 0
python scripts/evaluate_ai.py --writer claude --seeds 3 --seed-offset 100    # fresh students 100 to 102
python scripts/evaluate_ai.py --writer claude --seeds 1 --hidden-set 4       # 12 rules never seen in development
python scripts/demo.py --student int_leading_minus_covers_all --hide-rule --ai claude
```

## Credits and licence

- MaE dataset: Nancy Otero, Stefania Druga, Andrew Lan. MIT License.
- Misconception descriptions in MaE draw on Ashlock (2006), *Error Patterns in Computation*.
- This project: MIT. See [`LICENSE`](LICENSE).
