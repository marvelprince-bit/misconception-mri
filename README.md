# Misconception MRI

**A fraction tutor that finds the wrong rule behind a student's answers, even when the answers come out right, and proves its diagnosis by predicting the student's next answer.**

Built for the Global AI Builder's Challenge (Devpost, November 21 to 28, 2026).

## The problem

Many students do fractions with a consistent but wrong procedure. Some of these procedures produce the right answer on many problems, so answer checking never catches them. In our question pool, the "subtract the smaller from the larger, never regroup" rule gives the correct answer on 60% of fraction subtraction questions. A worksheet marked 100% can hide it.

Research on AI tutors calls this the *correct answer trap*: models under-detect misconceptions when the student reaches a correct answer through flawed reasoning (Imran and Bulathwela, 2026, arXiv:2605.23925).

## How it works

1. **Every method is executable.** The correct method and 11 known wrong rules are small programs that answer any fraction problem the way a student holding that method would (`mri/rules.py`).
2. **Keep what fits.** After each answer, only the methods that reproduce every one of the student's answers exactly stay in play.
3. **Ask the question that separates them.** When several methods still fit, the engine asks the question whose predicted answers split them most evenly (maximum entropy), so one answer removes as many as possible.
4. **Check the hard cases.** No diagnosis is confirmed until the student has met each stress case for the operation, such as a subtraction that needs regrouping.
5. **Confirm by prediction.** A wrong rule is only confirmed after it predicts a distinctive wrong answer *before* the student gives it.
6. **Say "unknown" honestly.** If no method fits, the engine says so and refers the student to a teacher instead of guessing.

## Evidence

Full tables: [`eval/results.md`](eval/results.md). Reproduce with `python -m eval.run_gonogo` (fixed seed).

| Test | Result |
|---|---|
| **Correct answer trap.** Three opening answers are all correct, but the student uses a wrong rule. | Answer checking marks 100% of these students correct. Misconception MRI exposes 100% of them within 2 chosen questions (1 question for addition and division). |
| **Identification.** Simulated students using each of 12 methods, 200 per method, 3 random opening questions. | 100% identified, 0.95 follow-up questions on average. Random follow-up questions: 67% identified, 2.32 questions. |
| **Unknown reasoning.** Each wrong rule is removed from the bank in turn; a student who holds it is tested. | 100% reported as unknown, 0% wrong labels. Without the two safeguards: 21% wrong labels. |
| **External answer key (MaE).** 32 fraction examples from 8 published misconceptions. | 27 of 32 reproduced exactly. Leave-one-out: when the engine commits, it predicts the held-out answer correctly 20 of 21 times; it says unknown on the other 11. |
| **Careless slips.** 15% random slips, one mismatch tolerated. | 79% identified. This is the weakest result (see Limitations). |

Simulated students are generated from the same rule bank, so the identification and trap results show the engine works as designed; the unknown-reasoning test and the MaE answer key are the checks against that circularity.

## What is new here, and what is not

**Prior work we build on:**
- Executable misconceptions ("malrules") are established: MalruleLib (Chen, Liu and Sonkar, ACL 2026) encodes 101 of them. We cite it as prior work. We do not use its code or data, because its license does not allow evaluating closed-source models.
- The correct answer trap is documented by Imran and Bulathwela (2026).
- Our answer key is the MaE dataset (Otero, Druga and Lan, 2024, MIT license).

**Our contributions:**
1. Choosing the next question by how strongly it separates the remaining executable explanations.
2. Exposing correct-answer traps with chosen questions instead of screening single answers.
3. Two safeguards, stress coverage and confirmation by prediction, that turned 21% confident wrong labels into 0% when the student's real rule was missing from the bank.

## Limitations

- Covers fraction arithmetic only (add, subtract, multiply, divide, simplify), with 11 wrong rules.
- Simulated students follow their rule perfectly. With 15% random slips, accuracy falls to about 79%.
- The MaE examples were written by learning researchers from published sources; they are not raw student data.
- 5 of 32 MaE examples are not reproduced by any rule; the engine reports them as unknown.
- No classroom testing has been done, so no claim is made about learning gains.

## Setup

```bash
python -m pip install pytest
python -m pytest -q          # unit tests
python -m eval.run_gonogo    # full evaluation, about 4 minutes
```

Python 3.10 or newer. The engine itself uses only the standard library.

## Credits

- MaE dataset: Nancy Otero, Stefania Druga, Andrew Lan. MIT License. https://github.com/nancyotero-projects/math-misconceptions
- Misconception descriptions in MaE draw on Ashlock (2006), *Error Patterns in Computation*.
- Development assistance: Claude (Anthropic). See [`DEVLOG.md`](DEVLOG.md) for every AI contribution and how it was checked.

## License

MIT. See [`LICENSE`](LICENSE).
