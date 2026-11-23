# Go/no-go results
Seed 20261123, 200 simulated students per rule.

## E1. Identification: adaptive vs random follow-up questions
Opening worksheet: 3 random questions for the operation. Follow-ups: chosen by the engine (adaptive) or random. Limit 5 follow-ups.

| Hypothesis | Adaptive accuracy | Adaptive mean questions | Random accuracy | Random mean questions |
|---|---|---|---|---|
| OK | 100% | 0.72 | 80% | 1.48 |
| R01 | 100% | 1.33 | 50% | 3.04 |
| R02 | 100% | 1.48 | 47% | 3.22 |
| R03 | 100% | 0.61 | 88% | 1.52 |
| R04 | 100% | 2.10 | 15% | 4.66 |
| R05 | 100% | 2.08 | 11% | 4.83 |
| R06 | 100% | 0.57 | 79% | 2.13 |
| R07 | 100% | 0.66 | 72% | 2.29 |
| R08 | 100% | 1.19 | 73% | 2.75 |
| R09 | 100% | 0.35 | 94% | 0.92 |
| R10 | 100% | 0.29 | 96% | 0.94 |
| R11 | 100% | 0.00 | 100% | 0.01 |
| **All** | **100%** | **0.95** | **67%** | **2.32** |

## E2. Correct answer trap
Three opening questions are all traps (the wrong rule gives the right answer).

Exposed means the correct method no longer explains the student's answers.

| Rule | Op | Trap share of questions | Answer checking marks student correct | Exposed by 1 chosen question | Exposed within 2 | Mean questions | Confirmed after stress checks |
|---|---|---|---|---|---|---|---|
| R02 | + | 18% (140/784) | 100% | 100% | 100% | 1.00 | 100% |
| R02 | - | 22% (79/368) | 100% | 31% | 100% | 1.69 | 100% |
| R04 | - | 60% (2743/4558) | 100% | 28% | 100% | 1.72 | 100% |
| R08 | / | 20% (93/462) | 100% | 100% | 100% | 1.00 | 100% |
| R09 | / | 6% (48/784) | 100% | 100% | 100% | 1.00 | 100% |

## E3. Unknown reasoning (rule removed from the bank), with and without stress coverage
| Held-out rule | Says unknown (with) | Wrong label (with) | Says unknown (without) | Wrong label (without) |
|---|---|---|---|---|
| R01 | 100% | 0% | 59% | 41% |
| R02 | 100% | 0% | 49% | 51% |
| R03 | 100% | 0% | 78% | 22% |
| R04 | 100% | 0% | 78% | 22% |
| R05 | 100% | 0% | 87% | 13% |
| R06 | 100% | 0% | 34% | 66% |
| R07 | 100% | 0% | 100% | 0% |
| R08 | 100% | 0% | 86% | 14% |
| R09 | 100% | 0% | 100% | 0% |
| R10 | 100% | 0% | 100% | 0% |
| R11 | 100% | 0% | 100% | 0% |
| **All** | **100%** | **0%** | **79%** | **21%** |

## E4. Careless slips
Slip rate 15%, tolerance 1, 5 opening questions: accuracy 79% over 1100 students.

## E5. External answer key (MaE, transcribed fraction items)
Examples reproduced exactly by a wrong rule: 27/32.

| MaE | Ex | Problem | Student | Correct | Explained by |
|---|---|---|---|---|---|
| MaE07 | 1 | simplify 4/8 | 2/8 | 1/2 | nothing (unknown) |
| MaE07 | 2 | simplify 6/8 | 3/8 | 3/4 | R11 |
| MaE07 | 3 | simplify 4/6 | 1/6 | 2/3 | nothing (unknown) |
| MaE07 | 4 | simplify 7/7 | 1/7 | 1 | R11 |
| MaE08 | 1 | 4/5 + 2/3 | 6/8 | 1 7/15 | R01 |
| MaE08 | 2 | 1/4 + 2/3 | 3/7 | 11/12 | R01 |
| MaE08 | 3 | 5/12 + 3/8 | 8/20 | 19/24 | R01 |
| MaE08 | 4 | 8 - 3/5 | 5/3 | 7 2/5 | nothing (unknown) |
| MaE09 | 1 | 1/2 + 1/4 | 2/4 | 3/4 | R02 |
| MaE09 | 2 | 2/5 + 1/2 | 3/10 | 9/10 | R02, R03 |
| MaE09 | 3 | 3/5 + 1/3 | 4/15 | 14/15 | R02, R03 |
| MaE09 | 4 | 3/4 + 1/2 | 4/4 | 1 1/4 | R02 |
| MaE10 | 1 | 7 - 1/3 | 2 | 6 2/3 | nothing (unknown) |
| MaE10 | 2 | 8 1/3 - 2/3 | 4 1/2 | 7 2/3 | nothing (unknown) |
| MaE10 | 3 | 6 - 1 1/4 | 5 1/4 | 4 3/4 | R04 |
| MaE10 | 4 | 1 - 1/3 | 1 1/3 | 2/3 | R04 |
| MaE11 | 1 | 6 2/3 - 3 1/6 | 3 1/3 | 3 1/2 | R05 |
| MaE11 | 2 | 4 5/8 - 1 3/4 | 3 2/4 | 2 7/8 | R05 |
| MaE11 | 3 | 5 3/8 - 2 2/3 | 3 1/5 | 2 17/24 | R05 |
| MaE11 | 4 | 7 2/5 - 4 7/10 | 3 5/5 | 2 7/10 | R05 |
| MaE13 | 1 | 2/3 × 3 | 6/9 | 2 | R06 |
| MaE13 | 2 | 1/4 × 6 | 6/24 | 1 1/2 | R06 |
| MaE13 | 3 | 4/5 × 2 | 8/10 | 1 3/5 | R06 |
| MaE13 | 4 | 3/8 × 4 | 12/32 | 1 1/2 | R06 |
| MaE14 | 1 | 4/6 ÷ 2/2 | 2/3 | 2/3 | OK, R08 |
| MaE14 | 2 | 6/8 ÷ 2/8 | 3/1 | 3 | OK, R08 |
| MaE14 | 3 | 6/10 ÷ 2/4 | 3/2 | 1 1/5 | R08 |
| MaE14 | 4 | 7/5 ÷ 3/2 | 2/2 | 14/15 | R08 |
| MaE15 | 1 | 2/3 ÷ 3/8 | 9/16 | 1 7/9 | R09 |
| MaE15 | 2 | 2/5 ÷ 1/3 | 5/6 | 1 1/5 | R09 |
| MaE15 | 3 | 3/4 ÷ 1/5 | 4/15 | 3 3/4 | R09 |
| MaE15 | 4 | 5/8 ÷ 2/3 | 16/15 | 15/16 | R09 |

Leave-one-out: diagnose from the other examples of the same misconception, predict the held-out answer: 20/32 correct overall. The engine committed on 21 and was right on 20 of them; it said unknown on 11.

| MaE | Held out | Status | Diagnosis | Predicted (value) | Actual | Result |
|---|---|---|---|---|---|---|
| MaE07 | 1 | unknown | - | - | 2/8 | - |
| MaE07 | 2 | unknown | - | - | 3/8 | - |
| MaE07 | 3 | unknown | - | - | 1/6 | - |
| MaE07 | 4 | unknown | - | - | 1/7 | - |
| MaE08 | 1 | unknown | - | - | 6/8 | - |
| MaE08 | 2 | unknown | - | - | 3/7 | - |
| MaE08 | 3 | unknown | - | - | 8/20 | - |
| MaE08 | 4 | confirmed | R01 | 7 2/5 | 5/3 | miss |
| MaE09 | 1 | confirmed | R02 | 1/2 | 2/4 | match |
| MaE09 | 2 | confirmed | R02 | 3/10 | 3/10 | match |
| MaE09 | 3 | confirmed | R02 | 4/15 | 4/15 | match |
| MaE09 | 4 | confirmed | R02 | 1 | 4/4 | match |
| MaE10 | 1 | unknown | - | - | 2 | - |
| MaE10 | 2 | unknown | - | - | 4 1/2 | - |
| MaE10 | 3 | unknown | - | - | 5 1/4 | - |
| MaE10 | 4 | unknown | - | - | 1 1/3 | - |
| MaE11 | 1 | confirmed | R05 | 3 1/3 | 3 1/3 | match |
| MaE11 | 2 | confirmed | R05 | 3 1/2 | 3 2/4 | match |
| MaE11 | 3 | confirmed | R05 | 3 1/5 | 3 1/5 | match |
| MaE11 | 4 | confirmed | R05 | 4 | 3 5/5 | match |
| MaE13 | 1 | confirmed | R06 | 2/3 | 6/9 | match |
| MaE13 | 2 | confirmed | R06 | 1/4 | 6/24 | match |
| MaE13 | 3 | confirmed | R06 | 4/5 | 8/10 | match |
| MaE13 | 4 | confirmed | R06 | 3/8 | 12/32 | match |
| MaE14 | 1 | confirmed | R08 | 2/3 | 2/3 | match |
| MaE14 | 2 | confirmed | R08 | 3 | 3/1 | match |
| MaE14 | 3 | confirmed | R08 | 1 1/2 | 3/2 | match |
| MaE14 | 4 | confirmed | R08 | 1 | 2/2 | match |
| MaE15 | 1 | confirmed | R09 | 9/16 | 9/16 | match |
| MaE15 | 2 | confirmed | R09 | 5/6 | 5/6 | match |
| MaE15 | 3 | confirmed | R09 | 4/15 | 4/15 | match |
| MaE15 | 4 | confirmed | R09 | 1 1/15 | 16/15 | match |
