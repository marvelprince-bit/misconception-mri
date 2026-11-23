# Development log

This log records every AI contribution to the project, how it was checked, and what was kept, changed or rejected. It supports rubric item A4 and description question 3.

**AI tool used for development:** Claude (Anthropic), working in a cloud workspace with code execution.

**How to use this log:** the "AI contribution" and "Automated check" columns are filled in as work happens. The "Human check" column must be filled in by Emmanuel Ikeme after personally reviewing the item: what he looked at, what he found, and his decision. Leave it blank until that review has actually happened.

| # | Date (CST) | AI contribution | Automated check and result | Human check (Emmanuel): what was reviewed, what was found | Decision: keep, change, reject |
|---|---|---|---|---|---|
| 1 | 2026-11-23 | Checked data licenses. Found MaE is MIT licensed. Found MalruleLib's license forbids evaluating closed-source models. | Read both LICENSE files in the cloned repositories. | | |
| 2 | 2026-11-23 | Transcribed 32 MaE fraction examples (MaE07 to MaE15, excluding MaE06 and MaE12) into `data/mae_fractions.json`. | Every transcription is reproduced in `eval/results.md` next to the original misconception id. | | |
| 3 | 2026-11-23 | Wrote 11 executable wrong rules (`mri/rules.py`): 8 from MaE misconception descriptions, 3 added as competing hypotheses. | Rules reproduce 27 of 32 MaE examples exactly. Unit tests check four misconceptions against all their MaE examples. | | |
| 4 | 2026-11-23 | Wrote the diagnosis engine: keep methods that reproduce every answer, then ask the question that splits the survivors most (entropy). | Simulated students: 100% identification vs 74% with random follow-up questions. | | |
| 5 | 2026-11-23 | First version confirmed diagnoses too early. When a wrong rule was missing from the bank, 19% of students got a confident wrong label. | Found by experiment E3 (rule removed from bank). | | |
| 6 | 2026-11-23 | Added stress coverage: no diagnosis is confirmed until the student has met each hard case for the operation (for example regrouping). | Wrong labels fell from 19% to 10%. | | |
| 7 | 2026-11-23 | Stress questions were chosen as "simplest", which picked uninformative ones (1/2 minus 1/3 gives 0 under two different rules). Changed to choose the question that best separates every method in the bank. Added a missing stress case (two mixed numbers with unlike denominators). | Wrong labels fell from 10% to 6%. | | |
| 8 | 2026-11-23 | Added confirmation by prediction: a wrong rule is only confirmed after it predicts a distinctive wrong answer before the student gives it. Idea relayed by Emmanuel from an outside review ("a rule counts only if it predicts an answer it never saw"). | Wrong labels fell from 6% to 0%; unknown reasoning is reported as unknown 100% of the time. | | |
| 9 | 2026-11-23 | Removed questions with negative answers from the subtraction pool, and stopped repeating a prediction with the same answer. | Demo storylines re-run by hand in the terminal. | | |
| 10 | 2026-11-23 | Wrote unit tests (`tests/test_engine.py`). | 10 of 10 pass. | | |
