# AI-assisted development log

The rubric (A4) gives points only when a PERSON checked a specific piece of AI-made
work, says what the check found, and says what was decided. Reporting AI use alone
earns nothing. Fill in the "Human check" columns yourself, truthfully. Leave a row
out rather than invent a check.

## What AI produced

On 23 Nov 2026 the starter engine in this repo (`mri/`, `scripts/`, `tests/`) was
generated with an AI assistant (Perplexity Computer) from the team's project idea.
The AI also ran the simulated-student tests and changed its own design three times
in response to the results (see "Design history" in the README).

## Checks to do and record

| # | AI-made piece | How a person can check it | What the check found | Decision (keep / change / reject) | Evidence (screenshot, commit) |
|---|---|---|---|---|---|
| 1 | The 13 wrong rules in `mri/rules.py` | Work 3 questions per rule by hand and compare with `python scripts/demo.py --student <id>` | | | |
| 2 | The claim "disagreement needs fewer questions than random" | Run `python scripts/evaluate.py` yourself and compare with `evidence/results.md` | | | |
| 3 | The sandbox that runs AI-written code (`mri/sandbox.py`) | Try to get a harmful snippet past it; add your snippet to `tests/test_mri.py` | | | |
| 4 | Wording of each rule's label | Would a volunteer tutor understand it? Rewrite any that are unclear | | | |
| 5 | Live AI rule-writer (`scripts/evaluate_ai.py --writer gemini`) | Run it with your key. Read 5 admitted rules and 5 rejected rules by hand | | | |

## Later AI help

Add a row each time AI writes or changes something: date, tool, what it made, how you
checked it, what you found, what you decided.
