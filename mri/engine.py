"""The diagnosis engine.

How it works, in plain words:

1. Keep a list of candidate rules (the correct method, known wrong rules, and any
   AI-written rule that passed the admission check).
2. After every answer, score how well each rule explains ALL the answers so far.
   One extra candidate, "unknown", stands for "no single rule explains this"
   (careless slips, guessing, or a rule the tool has never seen).
3. Pick the next question where the remaining rules disagree most, so one answer
   rules out as many candidates as possible.
4. A rule may miss an answer once (a careless slip). The tool then re-tests with a
   look-alike question. A second miss on the same shape of question is not a slip:
   that rule is struck out.
5. Before a wrong-rule diagnosis is final, the tool writes down predictions for
   new kinds of question. The diagnosis stands only if the student's answers match.
6. Before saying "no misconception", the tool tests every kind of question once.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache

from .problems import Problem, format_answer, full_pool, kind, shape
from .rules import Rule, library

UNKNOWN = "unknown"


@lru_cache(maxsize=None)
def _full_pool(domain: str) -> tuple:
    return tuple(full_pool(domain))


def _split(rules: tuple, problem: Problem) -> tuple:
    """How one question divides the rules: rules with the same answer share a group."""
    first_seen: dict = {}
    return tuple(first_seen.setdefault(r.predict(problem), k) for k, r in enumerate(rules))


@lru_cache(maxsize=64)
def _build_buckets(rules: tuple, pool: tuple) -> dict:
    """Group pool questions by (how they split the rules, kind of question)."""
    buckets: dict[tuple, list[int]] = {}
    for i, problem in enumerate(pool):
        buckets.setdefault((_split(rules, problem), kind(problem)), []).append(i)
    return buckets


@dataclass
class Observation:
    problem: Problem
    answer: Fraction
    purpose: str = "given"  # "given" | "diagnose" | "confirm"
    predicted: Fraction | None = None  # written down BEFORE a confirm question is asked
    predicted_rule: str | None = None
    question_why: str = ""


@dataclass
class Question:
    problem: Problem
    purpose: str  # "diagnose" | "confirm" | "explore"
    score: float = 0.0  # disagreement in bits (diagnose questions)
    predicted: Fraction | None = None
    predicted_rule: str | None = None
    why: str = ""


@dataclass
class Status:
    state: str  # "undecided" | "diagnosed" | "no_misconception" | "abstain" | "inconclusive"
    rule: Rule | None
    confidence: float
    confirmed: bool
    message: str
    ranking: list[tuple[str, float]] = field(default_factory=list)
    kinds_tested: int = 0
    kinds_total: int = 0

    @property
    def final(self) -> bool:
        return self.state != "undecided"


class Session:
    def __init__(
        self,
        domain: str,
        rules: list[Rule] | None = None,
        pool: list[Problem] | None = None,
        policy: str = "disagreement",  # or "random" (the comparison baseline)
        seed: int | None = None,
        slip: float = 0.10,  # chance a student who knows a rule still slips
        wrong_answer_prob: float = 0.05,  # chance a slip lands on one particular wrong answer
        unknown_lik: float = 0.15,  # how well "unknown" explains any single answer
        unknown_prior: float = 0.05,
        correct_prior: float = 0.50,  # most students who answer correctly do know the method
        confidence: float = 0.95,
        min_questions: int = 3,
        min_to_abstain: int = 5,  # do not give up on a student after only a few answers
        max_questions: int = 15,
        confirmations: int = 2,  # successful predictions needed before a wrong-rule diagnosis
        # How confirmation questions are chosen. "novel" is the default. The other two
        # are earlier, weaker designs kept so the comparison in evidence/ can be re-run.
        confirm_mode: str = "novel",  # "novel" | "novel_prefer_solo" | "solo"
        clear_needs_all_kinds: bool = True,  # test every kind before saying "no misconception"
        # Before NAMING a wrong rule, must the student also have been checked on every kind
        # of question? "ai": only for AI-written rules (default), "all": every rule, "none".
        # An AI-written rule may copy the student only where it saw wrong answers; a kind
        # where the student's rule happened to look correct can then hide the difference.
        diagnosis_needs_all_kinds: str = "risk",
        check_rivals: bool = True,
    ):
        if policy not in ("disagreement", "random"):
            raise ValueError("policy must be 'disagreement' or 'random'")
        if diagnosis_needs_all_kinds not in ("ai", "all", "none", "kinds", "risk"):
            raise ValueError("diagnosis_needs_all_kinds must be 'ai', 'risk', 'kinds', 'all' or 'none'")
        if confirm_mode not in ("novel", "novel_prefer_solo", "solo"):
            raise ValueError("confirm_mode must be 'novel', 'novel_prefer_solo' or 'solo'")
        self.domain = domain
        self.rules: list[Rule] = list(rules) if rules is not None else library(domain)
        self.pool = tuple(pool) if pool is not None else _full_pool(domain)
        self.policy = policy
        self.rng = random.Random(seed)
        self.slip = slip
        self.wrong_answer_prob = wrong_answer_prob
        self.unknown_lik = unknown_lik
        self.unknown_prior = unknown_prior
        self.correct_prior = correct_prior
        self.confidence = confidence
        self.min_questions = min_questions
        self.min_to_abstain = min_to_abstain
        self.max_questions = max_questions
        self.check_rivals = check_rivals
        self.confirmations = confirmations
        self.confirm_mode = confirm_mode
        self.clear_needs_all_kinds = clear_needs_all_kinds
        self.diagnosis_needs_all_kinds = diagnosis_needs_all_kinds
        self.observations: list[Observation] = []
        self.all_kinds = sorted({kind(p) for p in self.pool})
        self._rebuild()

    # ------------------------------------------------------------- set-up
    def _rebuild(self) -> None:
        self._buckets = _build_buckets(tuple(self.rules), self.pool)
        self._splits: dict[tuple, list[int]] = {}
        for (split, _), indices in self._buckets.items():
            self._splits.setdefault(split, []).extend(indices)

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)
        self._rebuild()

    @property
    def correct(self) -> Rule | None:
        return next((r for r in self.rules if r.is_correct), None)

    def rule_by_id(self, rule_id: str) -> Rule | None:
        return next((r for r in self.rules if r.id == rule_id), None)

    # ------------------------------------------------------------ evidence
    def record(self, problem: Problem, answer: Fraction, question: Question | None = None) -> None:
        if question is not None:
            obs = Observation(problem, answer, question.purpose, question.predicted, question.predicted_rule,
                              question.why)
        else:
            obs = Observation(problem, answer)
        self.observations.append(obs)

    def _priors(self) -> dict[str, float]:
        mass = 1.0 - self.unknown_prior
        wrong = [r for r in self.rules if not r.is_correct]
        has_correct = len(wrong) < len(self.rules)
        priors = {}
        for r in self.rules:
            if not has_correct:
                priors[r.id] = mass / len(self.rules)
            elif r.is_correct:
                priors[r.id] = mass * (self.correct_prior if wrong else 1.0)
            else:
                priors[r.id] = mass * (1.0 - self.correct_prior) / len(wrong)
        priors[UNKNOWN] = self.unknown_prior
        return priors

    def posterior(self) -> dict[str, float]:
        """How likely each candidate is, given every answer so far. Sums to 1."""
        log_hit = math.log(1.0 - self.slip)
        log_miss = math.log(self.slip * self.wrong_answer_prob)
        logs = {k: math.log(v) for k, v in self._priors().items() if v > 0}
        for obs in self.observations:
            for r in self.rules:
                if r.id in logs:
                    logs[r.id] += log_hit if r.predict(obs.problem) == obs.answer else log_miss
            logs[UNKNOWN] += math.log(self.unknown_lik)
        top = max(logs.values())
        weights = {k: math.exp(v - top) for k, v in logs.items()}
        if self.confirm_mode != "solo":
            for r in self.rules:
                if self.misses(r)[1]:
                    weights[r.id] = 0.0  # struck out: missed twice on the same shape of question
                elif r.source == "ai" and any(r.predict(o.problem) != o.answer for o in self.observations):
                    # AI-written rules get no slip allowance: the AI wrote the rule to fit, so
                    # a miss means the rule is wrong (or the student slipped; either way the
                    # safe result is no diagnosis, or a revision). Live run 23 Nov: a re-test
                    # on coincidental numbers let a wrong AI rule through.
                    weights[r.id] = 0.0
        total = sum(weights.values())
        return {k: w / total for k, w in weights.items()}

    def misses(self, rule: Rule) -> tuple[set[str], bool]:
        """(shapes with a miss not yet re-tested, struck out?) for one rule.

        One miss on a shape is treated as a possible slip until a look-alike question
        is answered the way the rule predicts. Two misses on one shape strike the rule out.
        """
        count: dict[str, int] = {}
        pending: set[str] = set()
        for o in self.observations:
            sh = shape(o.problem)
            if rule.predict(o.problem) == o.answer:
                pending.discard(sh)
            else:
                count[sh] = count.get(sh, 0) + 1
                pending.add(sh)
        return pending, any(c >= 2 for c in count.values())

    def ranking(self) -> list[tuple[str, float]]:
        return sorted(self.posterior().items(), key=lambda kv: -kv[1])

    def kinds_tested(self) -> set[str]:
        return {kind(o.problem) for o in self.observations}

    # ----------------------------------------------------- question choice
    def _asked(self) -> set[Problem]:
        return {o.problem for o in self.observations}

    def _pick_from(self, indices: list[int], asked: set[Problem]) -> Problem | None:
        fresh = [i for i in indices if self.pool[i] not in asked]
        return self.pool[self.rng.choice(fresh)] if fresh else None

    def disagreement(self, split: tuple, post: dict[str, float]) -> float:
        """Entropy (in bits) of the answers the rules predict, weighted by belief."""
        groups: dict[int, float] = {}
        for k, g in enumerate(split):
            groups[g] = groups.get(g, 0.0) + post[self.rules[k].id]
        total = sum(groups.values())
        if total <= 0:
            return 0.0
        return -sum((m / total) * math.log2(m / total) for m in groups.values() if m > 0)

    def _diagnostic_question(self, post: dict[str, float]) -> Question | None:
        asked = self._asked()
        if self.policy == "random":
            problem = self._pick_from(list(range(len(self.pool))), asked)
            return Question(problem, "diagnose", why="chosen at random (baseline)") if problem else None
        scored = [(self.disagreement(s, post), self.rng.random(), s) for s in self._splits]
        for score, _, split in sorted(scored, key=lambda t: (-t[0], t[1])):
            problem = self._pick_from(self._splits[split], asked)
            if problem:
                groups = len(set(split))
                return Question(problem, "diagnose", score=score,
                                why=f"the candidate rules give {groups} different answers here")
        return None

    def _retest_question(self, rule: Rule, pending: set[str]) -> Question | None:
        """A look-alike of a question this rule got wrong: was that miss a careless slip?"""
        asked = self._asked()
        fresh = [p for p in self.pool
                 if shape(p) in pending and p not in asked and rule.predict(p) is not None]
        if not fresh:
            return None
        # Most coincidence-free look-alike: a re-test where the numbers line up by accident
        # (equal tops, say) would also fit a look-alike rule the tool does not know.
        top = max(self.genericity(p) for p in fresh)
        problem = self.rng.choice([p for p in fresh if self.genericity(p) == top])
        return Question(problem, "confirm", predicted=rule.predict(problem), predicted_rule=rule.id,
                        why="re-test: an earlier answer of this shape did not fit the rule")

    def _confirm_question(self, rule: Rule) -> Question | None:
        """A fresh question that puts the leading rule to a real test.

        The tool writes down what the rule predicts, then asks. It picks a kind of
        question not asked yet, at random. A rule that only fits the kinds already
        seen proves little, and spreading the tests evenly across kinds is what
        catches a student whose real rule only looks like this one some of the time.

        Two earlier designs are kept for comparison:
          "solo"              -> the question where fewest other rules share the answer
          "novel_prefer_solo" -> a new kind, but still preferring unique answers
        Both steer the test toward the same few kinds, which hides look-alike rules.
        """
        asked = self._asked()
        k = self.rules.index(rule)
        correct = self.correct
        c = self.rules.index(correct) if correct is not None else None
        seen = self.kinds_tested()
        options = []
        for (split, qkind), indices in self._buckets.items():
            shared = sum(1 for j, g in enumerate(split) if g == split[k] and j != k)
            fresh = [i for i in indices
                     if self.pool[i] not in asked and rule.predict(self.pool[i]) is not None]
            if not fresh:
                continue
            novel = qkind not in seen
            why = "a kind of question not tested yet" if novel else "another test of the leading rule"
            if self.confirm_mode == "solo":
                if len(self.rules) > 1 and shared == len(self.rules) - 1:
                    continue
                key, why = (shared,), "few other rules give this answer"
            elif self.confirm_mode == "novel_prefer_solo":
                if len(self.rules) > 1 and shared == len(self.rules) - 1:
                    continue
                key = (not novel, not (c is None or split[k] != split[c]), shared)
            else:
                # Prefer questions where this rule and the correct method disagree: a
                # prediction that equals the correct answer cannot tell them apart.
                distinct = c is None or rule.is_correct or split[k] != split[c]
                key = (not distinct, not novel, qkind)
                if distinct and not rule.is_correct:
                    why += "; the rule predicts a wrong answer here"
            options.append((key, fresh, why))
        if not options:
            return None
        best = min(o[0] for o in options)
        if self.confirm_mode == "novel":
            # choose the kind at random first, then a question of that kind
            kinds = sorted({o[0][2] for o in options if o[0][:2] == best[:2]})
            chosen = self.rng.choice(kinds)
            fresh = [i for o in options if o[0] == (best[0], best[1], chosen) for i in o[1]]
            why = next(o[2] for o in options if o[0] == (best[0], best[1], chosen))
        else:
            tied = [o for o in options if o[0] == best]
            _, fresh, why = self.rng.choice(tied)
        # Within the chosen kind, the question most free of numerical coincidences: a
        # look-alike rule the tool does not know (equal tops, say) can only be told apart
        # where the numbers do not line up by accident.
        top = max(self.genericity(self.pool[i]) for i in fresh)
        problem = self.pool[self.rng.choice([i for i in fresh if self.genericity(self.pool[i]) == top])]
        return Question(problem, "confirm", predicted=rule.predict(problem),
                        predicted_rule=rule.id, why=why)

    def _coverage_question(self, rule: Rule) -> Question | None:
        """A question from a kind that has not been tested yet."""
        asked = self._asked()
        seen = self.kinds_tested()
        k = self.rules.index(rule)
        options = []
        for (split, qkind), indices in self._buckets.items():
            if qkind in seen:
                continue
            fresh = [i for i in indices if self.pool[i] not in asked]
            if fresh:
                shared = sum(1 for j, g in enumerate(split) if g == split[k] and j != k)
                options.append((shared, self.rng.random(), fresh))
        if not options:
            return None
        _, _, fresh = min(options, key=lambda o: (o[0], o[1]))
        problem = self.pool[self.rng.choice(fresh)]
        return Question(problem, "confirm", predicted=rule.predict(problem), predicted_rule=rule.id,
                        why="a kind of question not tested yet")

    def _contested_shapes(self) -> set[str]:
        """Shapes with at least one question where the known methods (including any
        AI-written rule) do not all give the same answer."""
        key = tuple(self.rules)
        if getattr(self, "_contested_cache", (None,))[0] != key:
            live = {shape(p) for p in self.pool if self.contestedness(p) > 1}
            self._contested_cache = (key, live)
        return self._contested_cache[1]

    def untested_shapes(self) -> set[str]:
        """Shapes not tested yet (the ones an AI-written rule is checked on)."""
        seen = {shape(o.problem) for o in self.observations}
        return {shape(p) for p in self.pool} - seen

    def _shape_coverage_question(self, rule: Rule) -> Question | None:
        """For an AI-written rule: a question of a shape not tested yet, riskiest first.

        Risk order: (1) shapes where the rule claims the CORRECT answer, because a rule
        copied only from the student's wrong answers is most likely to be wrong there;
        (2) the most contested question; (3) shapes close to ones the student got wrong.
        """
        asked = self._asked()
        seen = {shape(o.problem) for o in self.observations}
        wrong = self._wrong_shape_counts()
        correct = self.correct
        best, best_key = [], None
        for p in self.pool:
            if p in asked:
                continue
            sh = shape(p)
            if sh in seen:
                continue
            # Every untested shape, even where all KNOWN methods agree: the student's rule is
            # unknown, so agreement among known methods says nothing about it. (Skipping
            # those shapes let a live Claude rule through on 23 Nov: it applied the student's
            # subtraction method only when regrouping was needed.)
            claims_correct = correct is not None and rule.predict(p) == correct.predict(p)
            key = (claims_correct, self.contestedness(p), self._closeness(sh, wrong))
            if best_key is None or key > best_key:
                best, best_key = [p], key
            elif key == best_key:
                best.append(p)
        if not best:
            return None
        problem = self.rng.choice(best)
        return Question(problem, "confirm", predicted=rule.predict(problem), predicted_rule=rule.id,
                        why=f"checking an AI-written rule on a shape not tested yet ({shape(problem)})")

    def _risk_question(self, rule: Rule) -> Question | None:
        """The riskiest untested question for a known rule, from shapes not tested yet (for
        integers a shape also records which number is larger, so whether the answer
        crosses zero). Order: where the student's error pattern (if any) would show but the
        rule does not predict it; the shape nearest to ones answered wrong (a look-alike
        most often parts company right next to the evidence, e.g. the same question with
        the order swapped); where the rule claims the correct answer; most contested;
        freest of numerical coincidences."""
        asked = self._asked()
        seen = {shape(o.problem) for o in self.observations}
        correct = self.correct
        patterns = self._error_patterns()
        wrong = self._wrong_shape_counts()
        # Lexicographic choice, done in stages so the costly 'how contested' count is only
        # worked out for questions still tied on the cheap criteria (same result as one
        # big sort key, in pool order).
        stages = [
            lambda p: self._pattern_breaks(p, rule, patterns),
            lambda p: self._closeness(shape(p), wrong),
            lambda p: correct is not None and rule.predict(p) == correct.predict(p),
            self.contestedness,
            self.genericity,
        ]
        best = [p for p in self.pool if p not in asked and shape(p) not in seen]
        best_key = []
        for score in stages:
            if not best:
                break
            scored = [(score(p), p) for p in best]
            top = max(v for v, _ in scored)
            best = [p for v, p in scored if v == top]
            best_key.append(top)
        if not best or (best_key[0] == 0 and best_key[3] < 2):
            return None
        problem = self.rng.choice(best)
        return Question(problem, "confirm", predicted=rule.predict(problem), predicted_rule=rule.id,
                        why=f"risk check: the untested shape most likely to expose a look-alike rule ({shape(problem)})")

    # Simple ways a wrong answer can relate to the right one. If EVERY wrong answer seen
    # so far follows one of them, the student may apply it more widely than the leading
    # rule says; the risk check then goes where that would show.
    ERROR_PATTERNS = {"made positive": abs, "sign flipped": lambda x: -x}

    def _error_patterns(self) -> list:
        correct = self.correct
        if correct is None:
            return []
        wrong = [(correct.predict(o.problem), o.answer) for o in self.observations
                 if o.answer is not None and o.answer != correct.predict(o.problem)]
        if len(wrong) < 2:
            return []
        out = []
        for f in self.ERROR_PATTERNS.values():
            try:
                if all(f(c) == a for c, a in wrong):
                    out.append(f)
            except TypeError:
                pass
        return out

    def _pattern_breaks(self, problem: Problem, rule: Rule, patterns: list) -> int:
        """How many fitted error patterns would give an answer here that the leading
        rule does not predict."""
        correct = self.correct
        if not patterns or correct is None:
            return 0
        c, r = correct.predict(problem), rule.predict(problem)
        n = 0
        for f in patterns:
            try:
                n += f(c) != r
            except TypeError:
                pass
        return n

    def _live_rivals(self, rule: Rule) -> list:
        """Variations of an AI rule that fit the student's answers at least as well as the
        rule itself, and still differ from it on some question not asked yet."""
        from .rivals import answer, rivals
        cache = getattr(self, "_rival_cache", {})
        self._rival_cache = cache
        if rule.code not in cache:
            cache[rule.code] = rivals(rule)
        own_misses = sum(1 for o in self.observations if rule.predict(o.problem) != o.answer)
        asked = self._asked()
        alive = []
        for r in cache[rule.code]:
            misses = sum(1 for o in self.observations if answer(r, o.problem) != o.answer)
            if misses > own_misses:
                continue
            alive.append(r)
        if not alive:
            return []
        # Keep only rivals that differ from the rule somewhere it could still be tested.
        differ = []
        for r in alive:
            for p in self.pool:
                if p in asked:
                    continue
                mine = rule.predict(p)
                if mine is not None and answer(r, p) not in (None, mine):
                    differ.append(r)
                    break
        return differ

    def _rival_question(self, rule: Rule, alive: list) -> Question | None:
        """The unasked question on which the AI rule disagrees with the most surviving
        rivals (ties: freest of coincidences)."""
        from .rivals import answer
        asked = self._asked()
        best, best_key = [], None
        for p in self.pool:
            if p in asked:
                continue
            mine = rule.predict(p)
            if mine is None:
                continue
            split = sum(1 for r in alive if answer(r, p) not in (None, mine))
            if split == 0:
                continue
            key = (split, self.genericity(p))
            if best_key is None or key > best_key:
                best, best_key = [p], key
            elif key == best_key:
                best.append(p)
        if not best:
            return None
        problem = self.rng.choice(best)
        return Question(problem, "confirm", predicted=rule.predict(problem), predicted_rule=rule.id,
                        why=f"rival check: {best_key[0]} close variation(s) of the AI rule answer differently here")

    def _needs_every_kind(self, rule: Rule) -> bool:
        mode = self.diagnosis_needs_all_kinds
        return not rule.is_correct and (mode == "all" or (mode in ("ai", "kinds", "risk") and rule.source == "ai"))

    def _confirm_hits(self, rule: Rule) -> int:
        """Predictions made before the answer that came true. For a wrong rule, only
        predictions that differ from the correct answer count: matching the correct
        answer does not tell the wrong rule apart from correct reasoning."""
        correct = self.correct
        return sum(
            1 for o in self.observations
            if o.purpose == "confirm" and o.predicted_rule == rule.id and o.answer == o.predicted
            and (rule.is_correct or correct is None or correct.predict(o.problem) != o.predicted)
        )

    def _decide(self) -> tuple[Status, Question | None]:
        post = self.posterior()
        ranking = sorted(post.items(), key=lambda kv: -kv[1])
        top_id, top_p = ranking[0]
        n = len(self.observations)
        sure = top_p >= self.confidence
        enough = n >= self.min_questions
        cover = dict(kinds_tested=len(self.kinds_tested()), kinds_total=len(self.all_kinds))

        def status(state, rule, confirmed, message):
            return Status(state, rule, top_p, confirmed, message, ranking, **cover)

        if sure and n >= self.min_to_abstain and top_id == UNKNOWN:
            return status("abstain", None, False,
                          "No single rule explains these answers. This looks like careless slips, "
                          "guessing, or a rule the tool does not know. No diagnosis is given."), None

        if sure and top_id != UNKNOWN:
            rule = self.rule_by_id(top_id)
            pending = self.misses(rule)[0] if self.confirm_mode != "solo" else set()
            question = self._retest_question(rule, pending) if pending else None
            if question is not None:
                confirmed = False
            elif rule.is_correct and self.clear_needs_all_kinds:
                question = self._coverage_question(rule)
                confirmed = question is None
            elif self.diagnosis_needs_all_kinds == "risk" and not rule.is_correct and rule.source != "ai" \
                    and self._confirm_hits(rule) >= self.confirmations \
                    and not any(o.question_why.startswith("risk check") for o in self.observations
                                if o.predicted_rule == rule.id) \
                    and self._risk_question(rule) is not None:
                # Known rule, confirmed by predictions: ONE extra question, the riskiest one
                # (an untested kind where the rule claims the correct answer and other methods
                # disagree), so a look-alike of a rule missing from the list is caught.
                question = self._risk_question(rule)
                confirmed = False
            elif self.diagnosis_needs_all_kinds == "kinds" and not rule.is_correct and rule.source != "ai" \
                    and self._coverage_question(rule) is not None \
                    and self._confirm_hits(rule) >= self.confirmations:
                # Known rule, already confirmed by predictions: also check each untested KIND
                # once (the most contested question), so a look-alike of a rule missing from
                # the list is not named on the strength of one kind of question.
                question = self._coverage_question(rule)
                confirmed = False
            elif self._needs_every_kind(rule):
                # AI-written rule: check every untested shape FIRST, riskiest first, so a
                # rule that only copied part of the student's procedure fails early. Kinds
                # alone are too coarse: a kind can be "tested" by a question where the
                # student's wrong rule happened to give the right answer. Then the usual
                # predictions, if the shape checks did not already supply them.
                question = self._shape_coverage_question(rule)
                confirmed = False
                if question is None:
                    confirmed = self._confirm_hits(rule) >= self.confirmations
                    question = None if confirmed else self._confirm_question(rule)
                if question is None and rule.source == "ai" and self.check_rivals:
                    # Last check before naming: no small variation of the rule may fit
                    # the student's answers equally well (see mri/rivals.py).
                    alive = self._live_rivals(rule)
                    if alive:
                        question = self._rival_question(rule, alive)
                        confirmed = False
                        if question is None or n >= self.max_questions:
                            return status(
                                "abstain", None, False,
                                "An AI-written rule fits, but so does a close variation of it, and no "
                                "question left can tell them apart. No diagnosis is given."), None
            else:
                confirmed = self._confirm_hits(rule) >= self.confirmations
                question = None if confirmed else self._confirm_question(rule)
            if enough and question is None:
                if rule.is_correct:
                    message = (f"No known wrong rule found. Correct on {cover['kinds_tested']} of "
                               f"{cover['kinds_total']} kinds of question.")
                    return status("no_misconception", rule, confirmed, message), None
                note = (f"confirmed by {self._confirm_hits(rule)} prediction(s) made before the answer was seen"
                        if confirmed else "not fully confirmed: ran out of questions that could test it")
                return status("diagnosed", rule, confirmed, f"{rule.label} ({note})"), None
            if question is not None and n < self.max_questions:
                return status("undecided", rule, False, "Leading rule found. Testing it with a prediction."), question

        if n >= self.max_questions:
            return status("inconclusive", None, False,
                          f"Still unsure after {n} answers. No diagnosis is given."), None

        question = self._diagnostic_question(post)
        if question is None:
            return status("inconclusive", None, False,
                          "Ran out of questions that could separate the rules."), None
        return status("undecided", None, False, "More answers needed."), question

    def status(self) -> Status:
        return self._decide()[0]

    def next_question(self) -> Question | None:
        """The next question to ask, or None when the session is finished."""
        return self._decide()[1]

    def wrong_answers(self) -> int:
        correct = self.correct
        return sum(1 for o in self.observations if correct.predict(o.problem) != o.answer)

    @staticmethod
    @lru_cache(maxsize=None)
    def genericity(problem: Problem) -> int:
        """How free a question is of numerical coincidences: distinct numbers, and distinct
        gaps between them. Coincidences (equal tops, tops that differ by as much as the
        bottoms, bottoms whose ratio rounds to 1) make different procedures give the same
        answer, so an AI shown such answers cannot tell which procedure the student uses."""
        nums = [abs(x) for x in problem.args if isinstance(x, int) and x != 0]
        gaps = {abs(a - b) for i, a in enumerate(nums) for b in nums[i + 1:]}
        ratios = {a // b for a in nums for b in nums if b and a >= b and a != b}
        return len(set(nums)) + len(gaps) + len(ratios - {1})

    def contestedness(self, problem: Problem) -> int:
        """How many different answers the known rules (and the correct method) give here.
        High values are the questions where wrong procedures split apart."""
        return len(set(_split(tuple(self.rules), problem)))

    def _wrong_shape_counts(self) -> dict[str, int]:
        correct = self.correct
        counts: dict[str, int] = {}
        if correct is None:  # a rule list without the correct method: nothing counts as wrong
            return counts
        for o in self.observations:
            if correct.predict(o.problem) != o.answer:
                counts[shape(o.problem)] = counts.get(shape(o.problem), 0) + 1
        return counts

    @staticmethod
    def _closeness(sh: str, wrong_shapes) -> int:
        """Shared descriptive words with the nearest shape the student got wrong."""
        words = set(sh.replace(",", " ").split())
        return max((len(words & set(w.replace(",", " ").split())) for w in wrong_shapes), default=0)

    def explore_question(self, budget_left: int | None = None, target: int = 4) -> Question | None:
        """When no known rule fits: collect VARIED wrong answers for the AI rule-writer.

        Prefers, in order: a shape not asked yet, shapes close to ones the student got
        wrong, and the most contested question (where known procedures disagree most).
        A shape already answered wrong twice is skipped: more of the same teaches the AI
        nothing new and lets a rule copied from one shape look general.

        Budget-aware: if the questions left are only just enough to reach `target` wrong
        answers, it asks look-alikes of a shape the student already gets wrong instead,
        so a rule that only shows up in one shape still gets enough answers for the AI.
        """
        asked = self._asked()
        wrong = self._wrong_shape_counts()
        seen = {shape(o.problem) for o in self.observations}
        need = max(0, target - sum(wrong.values()))
        must_collect = budget_left is not None and wrong and need >= budget_left
        best, best_key = [], None
        for p in self.pool:
            if p in asked:
                continue
            sh = shape(p)
            if must_collect:
                if sh not in wrong:
                    continue
                key = (-wrong[sh], self.contestedness(p), self.genericity(p))  # least-asked wrong shape first
            else:
                if wrong.get(sh, 0) >= 2:
                    continue
                key = (sh not in seen, self._closeness(sh, wrong), self.contestedness(p), self.genericity(p))
            if best_key is None or key > best_key:
                best, best_key = [p], key
            elif key == best_key:
                best.append(p)
        if not best:
            return None
        return Question(self.rng.choice(best), "explore",
                        why="collecting varied answers to work out an unknown rule")

    def explore_in_kinds(self, kinds: set[str], failed: Rule | None = None) -> Question | None:
        """After an AI rule failed: a new question in the kinds where it failed (the kinds
        of the hidden answers, or where the student contradicted it). The hidden answers
        themselves are never asked again or shown.

        Preference: questions where the failed rule makes a BOLD claim (predicts a wrong
        answer, different from the correct one), so whatever the student answers tells the
        AI something new; then the most contested; then free of numerical coincidences."""
        asked = self._asked()
        seen = {shape(o.problem) for o in self.observations}
        correct = self.correct
        best, best_key = [], None
        for p in self.pool:
            if p in asked or kind(p) not in kinds:
                continue
            bold = False
            if failed is not None and correct is not None:
                pred = failed.predict(p)
                bold = pred is not None and pred != correct.predict(p)
            key = (bold, shape(p) not in seen, self.contestedness(p), self.genericity(p))
            if best_key is None or key > best_key:
                best, best_key = [p], key
            elif key == best_key:
                best.append(p)
        if not best:
            return None
        return Question(self.rng.choice(best), "explore",
                        why="more answers where the AI's first rule failed")

    # ---------------------------------------------------------- reporting
    def trap_report(self) -> dict:
        """Right answers, wrong rule: which wrong rules would give these same answers?"""
        correct = self.correct
        obs = self.observations
        all_correct = bool(obs) and correct is not None and all(
            correct.predict(o.problem) == o.answer for o in obs)
        hidden = [r for r in self.rules if not r.is_correct
                  and all(r.predict(o.problem) == o.answer for o in obs)]
        return {
            "answers": len(obs),
            "all_correct": all_correct,
            "trap_possible": all_correct and bool(hidden),
            "hidden_rules": hidden,
            "kinds_tested": len(self.kinds_tested()),
            "kinds_total": len(self.all_kinds),
        }

    def predictions_table(self, problem: Problem) -> list[tuple[Rule, str, float]]:
        """For one question: what each rule predicts, next to how likely the rule is."""
        post = self.posterior()
        rows = [(r, format_answer(r.predict(problem)), post[r.id]) for r in self.rules]
        return sorted(rows, key=lambda row: -row[2])

    def fix_questions(self, rule: Rule, n: int = 3) -> list[Problem]:
        """Practice questions where the diagnosed rule gives a wrong answer."""
        correct = self.correct
        if correct is None:
            return []
        asked = self._asked()
        differ = [p for p in self.pool if p not in asked and rule.predict(p) != correct.predict(p)]
        self.rng.shuffle(differ)
        return differ[:n]
