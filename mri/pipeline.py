"""Run a whole tutoring session from first question to final result."""
from __future__ import annotations

from dataclasses import dataclass, field

from .engine import Question, Session, Status
from .problems import Problem
from .proposer import Admission, ProposerUnavailable, propose_and_admit

WRONG_ANSWERS_FOR_AI = 4  # wrong answers to collect before asking the AI for a rule
MAX_EXPLORE_QUESTIONS = 6  # extra questions allowed to collect them
EXTRA_QUESTIONS_FOR_AI_RULE = 5  # room to test an AI-written rule with fresh predictions


@dataclass
class Transcript:
    steps: list[tuple[Question, object]] = field(default_factory=list)  # (question, answer)
    notes: list[str] = field(default_factory=list)
    ai_attempted: bool = False
    ai_unavailable: bool = False
    admission: Admission | None = None
    status: Status | None = None

    @property
    def questions_asked(self) -> int:
        return len(self.steps)


def try_ai_rule(session: Session, ask, gate: bool = True, seed: int = 0) -> tuple[Admission | None, str]:
    """Ask the AI for a rule and check it. Returns (admission or None, note for the tutor).

    If the AI service is down, returns (None, note): the session carries on without it.
    """
    try:
        result = propose_and_admit(ask, session.domain, session.observations, session.correct,
                                   session.pool, session.rules, gate=gate, seed=seed)
    except ProposerUnavailable as exc:
        return None, f"AI rule-writer unavailable. {exc} Continuing with known rules only."
    if result.admitted:
        session.add_rule(result.rule)
        # room for the fresh predictions plus one check per shape of question not tested yet
        untested = len(session.untested_shapes())
        session.max_questions = len(session.observations) + EXTRA_QUESTIONS_FOR_AI_RULE + untested
    return result, result.reason


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
        if not (stuck and ask is not None and not log.ai_attempted):
            break
        log.ai_attempted = True
        explored = 0
        while session.wrong_answers() < WRONG_ANSWERS_FOR_AI and explored < MAX_EXPLORE_QUESTIONS:
            question = session.explore_question()
            if question is None:
                break
            put(question)
            explored += 1
        log.admission, note = try_ai_rule(session, ask, gate)
        log.ai_unavailable = log.admission is None
        log.notes.append(note)
        if not (log.admission and log.admission.admitted):
            break
    log.status = session.status()
    return log
