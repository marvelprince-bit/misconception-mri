# Misconception MRI

**Finds the wrong rule behind a student's maths answers, even when the answers are right, and proves it by predicting the student's next answers before they are given.**

---

## 1. Who is your project for, and why would they use it?

**For maths teachers and tutors of students aged about 9 to 14**, working on negative numbers and fractions. They use it when a student keeps making mistakes, or when a student's scores look fine but something feels off.

**The need.** Many maths errors are not random slips. They are wrong rules, applied consistently:

- Brown and Burton's BUGGY research (1978) showed that many errors are coherent procedures, such as writing 1/2 + 1/3 = 2/5 ([summary in MalruleLib, 2026](https://arxiv.org/pdf/2601.03217)).
- In a study of 227 at-risk fourth graders, 81% of fraction-ordering problems were answered wrongly, and 65% of the errors came from applying whole-number logic to fractions ([Malone and Fuchs, 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5018237)).
- Among 1,036 grade 4 students, errors were consistent across trials, which points to systematic strategies ([Di Lonardo Burr et al., 2022](https://eprints.whiterose.ac.uk/206211/1/Di%20Lonardo%20Burr%20et%20al.%202022%20BJEP.pdf)).
- Students hold several misconceptions at once and they change over time, so help has to respond to the specific error ([Di Lonardo Burr et al., 2026](https://eprints.whiterose.ac.uk/id/eprint/244198)).
- In the 2024 Nation's Report Card, nearly 40% of US 8th graders were below NAEP Basic in maths ([NAGB, 2025](https://www.nagb.gov/news-and-events/news-releases/2025/nations-report-card-decline-in-reading-progress-in-math.html)).

**The hidden part, the "correct answer trap".** Some wrong rules give the right answer on the easy questions that make up a typical worksheet. In this project, **16 of the 24 wrong rules score 5 out of 5** on an ordinary 5-question worksheet. A grade cannot see them. Recent research found AI tutors under-detect exactly these cases ([Imran and Bulathwela, 2026](https://arxiv.org/html/2605.23925)).

**A realistic use.** A student scores 5/5 on "7 − 6, 5 − 4, 8 − 5 ...". The teacher runs a scan. The tool picks questions where candidate rules disagree (−6 + (−8)), sees the student write 14, then writes down before asking that the student will answer 5 to −9 + 4. The student writes 5. After 5 questions it reports: *"Works out the right size but drops the negative sign"*, shows the evidence side by side, and gives three practice questions on which this rule fails.

**Compared with what teachers do now** (all comparison numbers are from this project's evaluations, `evidence/results.md`):

| Approach | What it finds |
|---|---|
| Marking a worksheet right or wrong | Misses 16 of 24 wrong rules completely: every answer is right |
| Asking more questions at random | Right rule found 92.5% of the time, 7.31 questions on average |
| **Misconception MRI** (questions chosen where rules disagree) | **Right rule 100% of the time, 5.53 questions on average**; for the 16 hidden rules, exposed in 100% of cases with 3 to 5 extra questions |
| Teacher's own error analysis | Needs the teacher to already suspect the right rule, and has no built-in test of the guess; the tool tests every guess by prediction |

**Workable for real users.** It runs on any laptop with Python and opens in a browser. Known rules need no internet and no account. Only when no known rule fits does it call Claude; that needs an Anthropic API key, and without one the tool still works with known rules and says the AI step was skipped. Only the maths questions and answers are sent to Claude, never names.

---

## 2. What did your team build or improve during the hackathon?

This is a new project, built entirely during the event: every commit in the repository is dated 23 to 25 November 2026. On day one, a starter engine was set up (13 wrong rules and a first diagnosis loop, DEVLOG rows 1 to 2); everything else was built on top of it during the event:

- **24 executable wrong rules across 5 topics** (negative numbers; adding, subtracting, multiplying and dividing fractions and mixed numbers), each a Python function that answers every question, matched to published misconceptions (MaE dataset).
- **The diagnosis engine:** questions chosen where rules disagree, predictions written before answers, careful re-tests ("one miss is not proof"), no all-clear until every kind of question is tested, and "no diagnosis" when it cannot tell.
- **The AI rule-writer with five safeguards** (question 3).
- **A web interface** with three ready cases and a "Be the student" mode.
- **An evaluation suite:** 93 automated tests, an external answer key (MaE), four sets of rules held back from development, stand-in AIs that cheat or fail, ten live Claude runs, and an exact replay of live runs without an API key.

---

## 3. How did your team use AI?

### AI in the finished project

**What it does.** When no known rule explains a student's answers, the tool asks **Claude Sonnet 5.5** to write the student's wrong rule as a short Python function. The tool does not trust the code. It tests it against the student.

**Why Claude Sonnet 5.5.** The job needs short, exact code that follows strict format rules, and a reply within seconds while a student waits. Sonnet is Anthropic's mid-size model, chosen for code quality at lower cost and latency than the largest model. Evidence from our own runs: on the final design, **every rule Claude wrote that passed admission matched the student's real rule on all questions** (live runs 9 and 10). We also built for Gemini, but its API was blocked in our development environment, so we have no head-to-head comparison; we say so rather than claim one.

**Design choices, each tied to a problem it solves:**

| Design choice | Problem it solves | Evidence it works |
|---|---|---|
| The rule must be **runnable code**, not a description | A label cannot be tested; code can predict answers | Admitted rules are checked against all 4,558 subtraction questions, not a sample |
| **Hidden answers:** some wrong answers are never shown to Claude; its rule must predict them | An AI could memorise the answers it is shown | A stand-in AI that memorises answers was admitted **0 times in 480 sessions** (and 0 of 240 on never-seen rules); with this check switched off, it was admitted 94% of the time |
| **Sandbox:** one function, plain arithmetic only, no imports, loops or file access | AI-written code runs on the teacher's machine | Unsafe code is rejected before it runs (`tests/`) |
| **Rival and coverage checks:** the tool makes small edits of Claude's code and must rule them all out; every branch of the code must be tried on a real answer | In live runs 3 and 8, Claude wrote rules that fitted every answer shown but differed in cases never asked | Both traced in the raw logs and fixed; Claude's own near-miss rules are **never named wrong** in simulation |
| **Revision and repair:** if Claude's rule fails, it gets one revision, and the tool tries small edits of it, each re-tested on new questions | Claude is often one condition away from the right rule | Live run 6 (22/24) became runs 9 and 10 (24/24) |

**How we checked the AI's work.** Every simulated student follows a known rule, so each diagnosis is checked against that rule on every possible question.

| Live Claude runs (24 misconceptions each, the tool's list missing the student's rule) | Right | Wrong | No diagnosis |
|---|---|---|---|
| Runs 1 to 8, while the safeguards were developed | 20 to 24 | 0 or 1 | 0 to 4 |
| **Run 9, final design, a new student** | **24** | **0** | **0** |
| **Run 10, final design, student 0** | **24** | **0** | **0** |

Every run is listed in `evidence/live/README.md`, including the two runs that produced a wrong diagnosis. The 24 cases are our development benchmark, so we also report:

- **Rules held back from development (set 4, 12 rules, 2,400 sessions, run once):** 0 wrong rules named; 1 session gave a false all-clear (0.04%).
- **External answer key (MaE dataset, 40 published examples):** predicted the student's exact answer on all 23 examples it committed to; declined on 12.

**When you can rely on it, and when not.** A named diagnosis has predicted the student's answers before seeing them, on new questions, so it can be trusted for students who apply one rule consistently. It cannot be relied on for students who mix several rules or make many careless slips: then it usually says "no diagnosis" (at 10% slips the right rule is still found 93.1% of the time). It has not been tested with real students.

---

## 4. How can people access and use the project, and what results does it achieve?

**Access:** [github.com/marvelprince-bit/misconception-mri](https://github.com/marvelprince-bit/misconception-mri)

```
pip install -r requirements.txt
python app.py        # open http://127.0.0.1:5000
```

Choose **Watch a scan** (pick a topic and the rule a simulated student secretly follows) or **Be the student** (answer yourself, mistakes included). Set `ANTHROPIC_API_KEY` for live Claude; without it, the AI case is replayed exactly from a saved live run.

**Test cases: what should happen and what happened**

| Case | Should happen | Happened |
|---|---|---|
| Ordinary 1: student drops the negative sign, 5/5 on the worksheet | Expose the hidden rule and name it | Named correctly after 5 questions, 3 predictions matched |
| Ordinary 2: a person types "add tops, add bottoms" answers | Name that rule | Named correctly after 5 questions |
| Repeat: the same 24 live Claude cases replayed from the saved log | Same results, no API calls | 24/24 again, all 27 saved replies used exactly |
| Demanding: subtraction rule the tool has never seen | Claude writes it, the tool tests it, names it only if it passes | Claude's first rule passed admission, then failed a prediction; its revision failed a hidden answer; the tool repaired it with one small edit; the repaired rule predicted new answers before they were given; named correctly |
| Failure 1: a cheating AI that memorises answers | Refuse the rule | Rejected twice; "No diagnosis"; earlier answers kept |
| Failure 2: someone types "three quarters" | Explain and keep the session | "'three quarters' is not a number. Type a number such as -8 or 3/5."; the question stays open, earlier answers kept |
| Failure 3: the AI service cannot be reached | Continue safely | "AI rule-writer unavailable ... Continuing with known rules only."; ends with "No diagnosis", never a guess |

**Results overall** (simulated students; tables in `evidence/`):

- Student's rule on the list: **100% right, 5.53 questions on average**; never a wrong rule, even with 10% careless slips.
- Student's rule not on the list, no AI: **100% "no diagnosis"**, 0% wrong.
- With AI, final design: **24/24 right, 0 wrong, in two live Claude runs**, about 16 questions per student.

---

## 5. What are the current limitations, and what happens when something goes wrong?

**Limitations**

- **No real students yet.** All results come from simulated students who follow one rule exactly, and from published examples. Real students mix rules and slip more.
- **Five topics.** Negative numbers and four fraction operations; simplifying fractions is not covered.
- **The live benchmark is small.** 24/24 on 24 cases is consistent with a true rate of about 86% or more, and these 24 cases were used to develop the safeguards. Independent figures come from held-out rules and new students.
- **One known look-alike remains.** One held-out rule ("adds tops and bottoms only when the bottoms differ") is named as its look-alike 65.5% of the time.
- **AI cases take longer:** about 16 questions on average, up to about 30 when the tool has to repair Claude's rule.
- **Cost and access:** the AI step needs an API key and an internet connection.

**What happens when something goes wrong**

| Problem | What the tool does |
|---|---|
| Answers do not fit any rule well enough | Says "No diagnosis" and explains why, instead of guessing |
| Claude's rule fails a hidden answer | Rejects it, collects new answers, allows one revision, tries small repairs, then declines if none passes |
| Claude returns unsafe or malformed code | The sandbox refuses it; one repair request for format errors only |
| Claude cannot be reached | Continues with known rules and says the AI step was unavailable |
| A careless slip | One miss is re-tested before it counts; AI-written rules get no slip allowance |
| An unreadable typed answer | Explains the format and keeps the question open |
