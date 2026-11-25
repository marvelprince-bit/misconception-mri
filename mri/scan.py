"""Run one real session and return every step as plain data, for the web interface.

Nothing here changes how the tool decides: it wraps Session.record to take a snapshot of
what the tool believes after each answer, and reads the AI exchanges from the same raw
log the evaluations use.
"""
from __future__ import annotations

import json
import os
import random
import tempfile
from pathlib import Path

from .engine import UNKNOWN, Session
from .pipeline import run_session
from .problems import TITLES, format_answer, parse_answer, worksheet_pool
from .rules import LIBRARY, get_rule, library
from .student import SimulatedStudent

ROOT = Path(__file__).resolve().parent.parent
REPLAY_LOG = ROOT / "evidence" / "live" / "claude_run10_seed0_raw.jsonl"
PURPOSE = {"diagnose": "question", "confirm": "prediction", "explore": "extra"}


def _count(x) -> int:
    return x if isinstance(x, int) else len(x or [])


def catalogue() -> dict:
    """Topics and the simulated students available in each."""
    out = {}
    for domain, rules in LIBRARY.items():
        out[domain] = {
            "title": TITLES.get(domain, domain),
            "students": [{"id": r.id, "label": r.label, "correct": r.is_correct} for r in rules],
        }
    return out


def _label(session: Session, rule_id: str) -> str:
    if rule_id == UNKNOWN:
        return "No rule on the list fits"
    rule = session.rule_by_id(rule_id)
    if rule is None:
        return rule_id
    if rule.id.startswith("ai_repair"):
        return "AI rule, repaired by the tool"
    return rule.label


def _ranking(session: Session, top: int = 4) -> list:
    return [{"label": _label(session, rid), "p": round(p, 4), "ai": rid.startswith("ai_")}
            for rid, p in session.ranking()[:top]]


class _ReplayAsk:
    def __init__(self, path: Path):
        self.book = {}
        for line in path.read_text().splitlines():
            entry = json.loads(line)
            self.book.setdefault(entry["prompt"], []).append(entry["reply"])

    def __call__(self, prompt: str) -> str:
        from .proposer import ProposerUnavailable
        replies = self.book.get(prompt)
        if not replies:
            raise ProposerUnavailable("this case is not in the saved live run")
        return replies.pop(0)


def ai_writers() -> dict:
    """AI rule-writers the interface can offer right now."""
    out = {"replay": "Claude, replayed from a saved live run (no key needed)",
           "cheat": "A cheating AI that memorises answers (safety demo)",
           "none": "No AI: known rules only"}
    if os.environ.get("ANTHROPIC_API_KEY"):
        out = {"claude": "Claude, live (uses your API key)", **out}
    return out


def _writer(name: str):
    from . import fakes
    if name == "replay":
        return _ReplayAsk(REPLAY_LOG)
    if name == "cheat":
        return fakes.cheat
    if name == "claude":
        from .proposer import ClaudeProposer
        return ClaudeProposer()
    return None


def scan(student_id: str, hide: bool = False, writer: str = "replay", seed: int = 7,
         worksheet: int = 5) -> dict:
    """One full session with a simulated student. With hide=True the student's rule is
    removed from the tool's list; the replayed Claude run used student 0 and no worksheet,
    so those settings are fixed in that case."""
    true_rule = get_rule(student_id)
    domain = true_rule.domain
    if hide and writer == "replay":
        seed, worksheet = 0, 0
    rules = [r for r in library(domain) if not (hide and r.id == true_rule.id)]
    session = Session(domain, rules=rules, seed=seed)
    student = SimulatedStudent(true_rule, 0.0, seed=seed)
    correct = session.correct

    sheet_rows, trap = [], None
    if worksheet and not hide:
        sheet = random.Random(seed).sample(worksheet_pool(domain), worksheet)
        for p in sheet:
            a = student.answer(p)
            session.record(p, a)
            sheet_rows.append({"q": p.text(), "answer": format_answer(a),
                               "correct": format_answer(correct.predict(p)), "ok": a == correct.predict(p)})
        report = session.trap_report()
        trap = {"possible": report["trap_possible"], "kinds_tested": report["kinds_tested"],
                "kinds_total": report["kinds_total"],
                "look_alikes": [r.label for r in report["hidden_rules"]]}

    steps, ai_calls = [], []
    original_record = session.record

    def record(problem, answer, question=None):
        original_record(problem, answer, question)
        if question is None:
            return
        steps.append({
            "kind": PURPOSE.get(question.purpose, question.purpose),
            "q": problem.text(), "why": question.why,
            "predicted": format_answer(question.predicted) if question.predicted is not None else None,
            "answer": format_answer(answer), "correct": format_answer(correct.predict(problem)),
            "ok": answer == correct.predict(problem),
            "matched": (answer == question.predicted) if question.predicted is not None else None,
            "ranking": _ranking(session),
        })

    session.record = record
    ask = _writer(writer) if hide or writer == "claude" else None
    if ask is not None:
        inner = ask

        def ask(prompt, inner=inner):  # noqa: F811  (note when the AI was called)
            ai_calls.append(len(steps))
            return inner(prompt)

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.jsonl"
        old = os.environ.get("MRI_RAW_LOG")
        os.environ["MRI_RAW_LOG"] = str(raw)
        try:
            log = run_session(session, student, ask=ask)
        finally:
            if old is None:
                os.environ.pop("MRI_RAW_LOG", None)
            else:
                os.environ["MRI_RAW_LOG"] = old
        exchanges = [json.loads(x) for x in raw.read_text().splitlines()] if raw.exists() else []

    ai = []
    for i, e in enumerate(exchanges):
        ai.append({"after_step": ai_calls[i] if i < len(ai_calls) else len(steps),
                   "revision": bool(e.get("revision")), "admitted": bool(e.get("admitted")),
                   "verdict": e.get("reason", ""), "code": e.get("extracted_code", ""),
                   "shown": _count(e.get("shown")), "hidden": _count(e.get("hidden"))})
    for note in log.notes:
        if note.startswith("Repair"):
            ai.append({"after_step": ai_calls[-1] if ai_calls else len(steps), "repair": True,
                       "verdict": note, "code": ""})

    st = log.status
    result = {"state": st.state, "message": st.message, "confirmed": st.confirmed,
              "kinds_tested": st.kinds_tested, "kinds_total": st.kinds_total,
              "rule": None, "evidence": [], "practice": []}
    if st.state == "diagnosed":
        rule = st.rule
        result["rule"] = {"label": _label(session, rule.id), "source": rule.source,
                          "code": rule.code if rule.source == "ai" else "",
                          "repaired": rule.id.startswith("ai_repair")}
        wrong = [o for o in session.observations if correct.predict(o.problem) != o.answer][:4]
        result["evidence"] = [{"q": o.problem.text(), "student": format_answer(o.answer),
                               "rule": format_answer(rule.predict(o.problem)),
                               "correct": format_answer(correct.predict(o.problem))} for o in wrong]
        result["practice"] = [{"q": p.text(), "rule": format_answer(rule.predict(p)),
                               "correct": format_answer(correct.predict(p))}
                              for p in session.fix_questions(rule, 3)]

    named = st.rule if st.state == "diagnosed" else None
    if named is not None:
        key_ok = all(named.predict(p) == true_rule.predict(p) for p in session.pool)
    else:
        key_ok = st.state == "no_misconception" and true_rule.is_correct
    return {
        "topic": TITLES.get(domain, domain), "student": true_rule.label, "student_id": true_rule.id,
        "hidden": hide, "writer": writer if ask is not None else "none", "seed": seed,
        "worksheet": sheet_rows, "trap": trap, "steps": steps, "ai": ai, "result": result,
        "answer_key": {"student_rule": true_rule.label, "verdict":
                       "right" if key_ok else ("declined" if named is None and st.state != "no_misconception" else "wrong")},
    }


# --------------------------------------------------------- you are the student
_LIVE: dict[str, Session] = {}


def start(domain: str, seed: int = 11) -> dict:
    session = Session(domain, seed=seed)
    sid = os.urandom(8).hex()
    _LIVE[sid] = session
    if len(_LIVE) > 200:
        _LIVE.pop(next(iter(_LIVE)))
    return {"sid": sid, "topic": TITLES.get(domain, domain), **_next(session)}


def answer(sid: str, text: str) -> dict:
    session = _LIVE.get(sid)
    if session is None:
        return {"error": "This session has expired. Start a new one."}
    pending = getattr(session, "_pending", None)
    if pending is None:
        return {"error": "There is no open question."}
    try:
        value = parse_answer(text)
    except ValueError as exc:
        return {"error": str(exc)}
    session._pending = None
    session.record(pending.problem, value, pending)
    step = {"kind": PURPOSE.get(pending.purpose, pending.purpose), "q": pending.problem.text(),
            "why": pending.why, "answer": format_answer(value),
            "predicted": format_answer(pending.predicted) if pending.predicted is not None else None,
            "matched": (value == pending.predicted) if pending.predicted is not None else None,
            "ok": value == session.correct.predict(pending.problem),
            "correct": format_answer(session.correct.predict(pending.problem)),
            "ranking": _ranking(session)}
    return {"step": step, **_next(session)}


def _next(session: Session) -> dict:
    question = session.next_question()
    if question is not None:
        session._pending = question
        return {"question": {"q": question.problem.text(), "kind": PURPOSE.get(question.purpose, question.purpose),
                             "why": question.why,
                             "predicted": format_answer(question.predicted) if question.predicted is not None else None}}
    st = session.status()
    out = {"state": st.state, "message": st.message,
           "rule": st.rule.label if st.state == "diagnosed" else None, "practice": []}
    if st.state == "diagnosed":
        out["practice"] = [{"q": p.text(), "rule": format_answer(st.rule.predict(p)),
                            "correct": format_answer(session.correct.predict(p))}
                           for p in session.fix_questions(st.rule, 3)]
    return {"result": out}
