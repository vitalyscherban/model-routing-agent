import dataclasses

from router.config import DEFAULT
from router.pipeline import RoutingAgent
from router.tasks import build_tasks


def _naive_settings():
    return dataclasses.replace(
        DEFAULT, routing_enabled=False, caching_enabled=False, escalation_enabled=False
    )


def test_naive_baseline_sends_everything_to_strong_and_is_fully_correct(tasks):
    report = RoutingAgent(settings=_naive_settings()).run(tasks)
    assert report.requests_by_tier == {"cheap": 0, "mid": 0, "strong": report.requests}
    assert report.requests == len(tasks)
    assert report.correct == len(tasks)
    assert report.cache_hits == 0


def test_routed_run_is_far_cheaper_than_naive_at_no_accuracy_cost(tasks):
    naive = RoutingAgent(settings=_naive_settings()).run(tasks)
    routed = RoutingAgent().run(tasks)

    assert routed.cost < naive.cost * 0.5
    assert routed.accuracy >= naive.accuracy


def test_routing_sends_the_majority_of_traffic_to_cheap_or_mid(tasks):
    report = RoutingAgent().run(tasks)
    top_tier_share = report.requests_by_tier["strong"] / report.requests
    assert top_tier_share < 0.30


def test_escalation_recovers_misclassified_hard_tasks(tasks):
    """The classifier is known to under-score some hard tasks onto mid
    (see test_classifier.py). This asserts the pipeline's answer to that:
    escalation, not a better classifier, is what keeps accuracy at 100%.
    """
    with_escalation = RoutingAgent().run(tasks)
    without_escalation = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, escalation_enabled=False)
    ).run(tasks)

    assert with_escalation.accuracy == 1.0
    assert without_escalation.accuracy < with_escalation.accuracy
    assert without_escalation.incorrect > 0


def test_forcing_everything_to_cheap_breaks_correctness(tasks):
    """The floor-of-the-ladder failure mode, made explicit.

    Escalation is capped at one rung by default, so a hard task forced onto
    cheap needs two rungs (cheap -> mid -> strong) to reliably reach a tier
    that actually covers it. This is a deliberately realistic limitation: an
    escalation policy is not a substitute for a reasonable first guess.
    """
    forced_cheap = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, force_tier="cheap")
    ).run(tasks)
    naive = RoutingAgent(settings=_naive_settings()).run(tasks)

    assert forced_cheap.cost < naive.cost
    assert forced_cheap.accuracy < naive.accuracy
    assert forced_cheap.incorrect > 0


def test_caching_eliminates_requests_for_duplicate_tasks(tasks):
    from router.tasks import stats

    report = RoutingAgent().run(tasks)
    expected_hits = stats(tasks)["duplicates"]

    assert report.cache_hits == expected_hits
    # One request per non-cached task at minimum; escalations add more, they
    # never subtract, so this is a floor, not an exact count.
    assert report.requests >= report.total_tasks - report.cache_hits


def test_disabling_caching_costs_more_with_the_same_corpus(tasks):
    with_cache = RoutingAgent().run(tasks)
    without_cache = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, caching_enabled=False)
    ).run(tasks)

    assert without_cache.cache_hits == 0
    assert without_cache.total_tokens > with_cache.total_tokens
    assert without_cache.requests > with_cache.requests


def test_only_correct_answers_populate_the_cache():
    """A wrong cached answer would compound across every duplicate of that
    question. Force a guaranteed-wrong first answer (cheap tier, hard task)
    and confirm its duplicate is NOT served from cache.
    """
    from router.tasks import Task

    original = Task(id="h0", text="Diagnose this intermittent race condition "
                                   "and its root cause in the retry queue.",
                     category="hard")
    duplicate = Task(id="h0-dup", text="Quick one: " + original.text,
                      category="hard", duplicate_of="h0")

    settings = dataclasses.replace(DEFAULT, force_tier="cheap", escalation_enabled=False)
    report = RoutingAgent(settings=settings).run([original, duplicate])

    assert report.cache_hits == 0
    assert report.requests == 2


def test_run_is_deterministic(tasks):
    a = RoutingAgent().run(tasks)
    b = RoutingAgent().run(tasks)
    assert a == b


def test_empty_input_does_not_crash():
    report = RoutingAgent().run([])
    assert report.total_tasks == 0
    assert report.accuracy == 0.0
    assert report.cost == 0.0
