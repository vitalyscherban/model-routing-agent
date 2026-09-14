from router.model import OfflineModel
from router.tasks import Task
from router.tiers import CHEAP, MID, STRONG

_model = OfflineModel()


def _task(category: str, id_: str = "x1") -> Task:
    return Task(id=id_, text=f"a {category} task about the checkout_service", category=category)


def test_a_tier_always_solves_tasks_within_its_declared_capability():
    for category, tier in (("trivial", CHEAP), ("moderate", MID), ("hard", STRONG)):
        answer = _model.ask(_task(category), tier)
        assert answer.correct


def test_strong_tier_solves_everything():
    for category in ("trivial", "moderate", "hard"):
        assert _model.ask(_task(category), STRONG).correct


def test_cheap_tier_does_not_always_solve_hard_tasks():
    outcomes = {_model.ask(_task("hard", id_=f"h{i}"), CHEAP).correct for i in range(20)}
    assert False in outcomes, "expected at least one failure across 20 distinct hard tasks"


def test_answers_are_deterministic():
    task = _task("hard", id_="h-repeat")
    a = _model.ask(task, MID)
    b = _model.ask(task, MID)
    assert a.correct == b.correct
    assert a.output_tokens == b.output_tokens


def test_stronger_tiers_produce_more_thorough_longer_answers():
    task = _task("hard", id_="h-thorough")
    cheap = _model.ask(task, CHEAP)
    strong = _model.ask(task, STRONG)
    assert strong.output_tokens > cheap.output_tokens


def test_token_counts_are_positive_and_reflect_task_text_length():
    short = _model.ask(Task(id="s", text="fix typo", category="trivial"), CHEAP)
    long_task = Task(
        id="l",
        text="fix typo " + ("with a lot of extra surrounding context " * 20),
        category="trivial",
    )
    long_answer = _model.ask(long_task, CHEAP)
    assert long_answer.input_tokens > short.input_tokens
