"""Run a whole tutoring session from first question to final result."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .engine import Question, Session, Status
from .problems import Problem, kind
from .proposer import Admission, ProposerUnavailable, propose_and_admit
from .sandbox import UnsafeRule, compile_rule

WRONG_ANSWERS_FOR_AI = 4  # wrong answers to collect before asking the AI for a rule
MAX_EXPLORE_QUESTIONS = 6  # extra questions allowed to collect them
EXTRA_QUESTIONS_FOR_AI_RULE = 5  # room to test an AI-written rule with fresh predictions
REVISION_QUESTIONS = 3  # new answers collected before the AI may revise a rule that failed admission
# Questions reserved for the rival check (mri/rivals.py): close variations of an admitted
# AI rule that fit the answers equally well must be ruled out before the rule is named.
RIVAL_QUESTIONS = 4
# After a rule was admitted and then CONTRADICTED by the student, the contradicting answers
# are already new evidence: questions stop as soon as this many NEW wrong answers are in hand
# (one is needed as the fresh hidden answer), up to REVISION_QUESTIONS.
REVISION_QUESTIONS_AFTER_CONTRADICTION = 1
FAILED_ON_ANSWERS = ("Rejected: predicted only", "Rejected: explains only")


def max_revisions() -> int:
    return int(os.environ.get("MRI_MAX_REVISIONS", "1"))


def revise_after_contradiction() -> bool:
    return os.environ.get("MRI_REVISE_CONTRADICTED", "1") == "1"


@dataclass
class Transcript:
    steps: list[tuple[Question, object]] = field(default_factory=list)  # (question, answer)
    notes: list[str] = field(default_factory=list)
    ai_attempted: bool = False
    ai_unavailable: bool = False
    revisions: int = 0
    admitted_at: int = 0  # number of answers recorded when the AI rule was admitted
    admission: Admission | None = None
    status: Status | None = None

    @property
    def questions_asked(self) -> int:
        return len(self.steps)


def try_ai_rule(session: Session, ask, gate: bool = True, seed: int = 0,
                **revision) -> tuple[Admission | None, str]:
    """Ask the AI for a rule and check it. Returns (admission or None, note for the tutor).

    If the AI service is down, returns (None, note): the session carries on without it.
    """
    try:
        result = propose_and_admit(ask, session.domain, session.observations, session.correct,
                                   session.pool, session.rules, gate=gate, seed=seed, **revision)
    except ProposerUnavailable as exc:
        return None, f"AI rule-writer unavailable. {exc} Continuing with known rules only."
    if result.admitted:
        session.add_rule(result.rule)
        # room for the fresh predictions plus one check per shape of question not tested yet
        untested = len(session.untested_shapes())
        session.max_questions = len(session.observations) + EXTRA_QUESTIONS_FOR_AI_RULE + untested \
            + RIVAL_QUESTIONS
    return result, result.reason


def _revise(session: Session, ask, gate: bool, log: "Transcript", put, failed: Admission,
            since: int | None) -> bool:
    """One revision. `since` is set when an ADMITTED rule was later contradicted: the new
    questions then target the kinds where the student contradicted it. Otherwise they
    target the kinds of the hidden answers it failed. Returns True if a rule was admitted."""
    rule = next((r for r in session.rules if r.source == "ai" and r.code == failed.code), None)
    if since is not None and rule is not None:
        missed = [o for o in session.observations[since:] if rule.predict(o.problem) != o.answer]
        kinds = {kind(o.problem) for o in missed} or {kind(o.problem) for o in failed.hidden_obs}
    else:
        kinds = {kind(o.problem) for o in failed.hidden_obs}
    before = len(session.observations) if since is None else since
    start = len(session.observations)
    try:
        failed_rule = rule or compile_rule(failed.code, session.domain, "failed_ai_rule")
    except UnsafeRule:
        failed_rule = None
    correct = session.correct

    def new_wrong() -> int:
        return sum(1 for o in session.observations[start:] if correct.predict(o.problem) != o.answer)

    # Up to REVISION_QUESTIONS new questions where the rule failed, aimed at its bold claims.
    # After a contradiction, stop as soon as one new wrong answer is in hand (it becomes the
    # fresh hidden answer); after a failed admission, collect all of them (more data).
    for _ in range(REVISION_QUESTIONS):
        if since is not None and new_wrong() >= REVISION_QUESTIONS_AFTER_CONTRADICTION:
            break
        question = session.explore_in_kinds(kinds, failed_rule) or session.explore_question()
        if question is None:
            break
        put(question)
    fresh = session.observations[before:]
    log.revisions += 1
    session.max_questions = max(session.max_questions, len(session.observations))
    log.admission, note = try_ai_rule(session, ask, gate, keep_hidden=list(failed.hidden_obs), fresh=fresh,
                                      previous_code=failed.code, rule_id=f"ai_rule_{log.revisions + 1}")
    log.ai_unavailable = log.admission is None
    log.notes.append("Revision: " + note)
    if log.admission and log.admission.admitted:
        log.admitted_at = start
        return True
    return False


def run_session(session: Session, student, ask=None, given: list[Problem] | None = None,
                gate: bool = True) -> Transcript:
    """Ask questions until the tool reaches a result.

    student : anything with .answer(problem)
    ask     : optional AI rule-writer (prompt -> reply). Used once, only if no known rule fits.
              An admitted AI rule is treated like any other candidate: it still has to
              predict fresh answers before it can become a diagnosis.
    given   : optional worksheet answered before the tool chooses its own questions.
    """
    log = Transcript()

    def put(question: Question) -> None:
        answer = student.answer(question.problem)
        session.record(question.problem, answer, question)
        log.steps.append((question, answer))

    for problem in given or []:
        session.record(problem, student.answer(problem))
    while True:
        question = session.next_question()
        if question is not None:
            put(question)
            continue
        stuck = session.status().state in ("abstain", "inconclusive")
        if not (stuck and ask is not None):
            break
        if log.ai_attempted:
            # An admitted AI rule was later contradicted by the student's answers (or could
            # not be confirmed). Revise once, against a stricter still-hidden check.
            adm = log.admission
            if not (adm and adm.admitted and log.revisions < max_revisions() and revise_after_contradiction()):
                break
            if not _revise(session, ask, gate, log, put, adm, since=log.admitted_at):
                break
            continue
        log.ai_attempted = True
        explored = 0
        while session.wrong_answers() < WRONG_ANSWERS_FOR_AI and explored < MAX_EXPLORE_QUESTIONS:
            question = session.explore_question(budget_left=MAX_EXPLORE_QUESTIONS - explored,
                                                target=WRONG_ANSWERS_FOR_AI)
            if question is None:
                break
            put(question)
            explored += 1
        log.admission, note = try_ai_rule(session, ask, gate)
        log.ai_unavailable = log.admission is None
        log.notes.append(note)
        # Revision: the rule failed the student's answers. Collect new answers where it
        # failed, then let the AI try once more against a stricter, still-hidden check.
        while (log.admission is not None and not log.admission.admitted
               and log.admission.reason.startswith(FAILED_ON_ANSWERS) and log.revisions < max_revisions()):
            _revise(session, ask, gate, log, put, log.admission, since=None)
        if not (log.admission and log.admission.admitted):
            break
        log.admitted_at = len(session.observations)
    log.status = session.status()
    return log
