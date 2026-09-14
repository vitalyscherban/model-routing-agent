from router import classifier
from router.config import DEFAULT
from router.tasks import build_tasks

_EXPECTED_TIER = {"trivial": "cheap", "moderate": "mid", "hard": "strong"}


def test_trivial_and_moderate_are_never_misclassified(tasks):
    """These two boundaries have zero tolerance in this corpus.

    If this regresses, something changed in the signal lists or the weights,
    not in the corpus -- the corpus is seeded and asserted stable separately.
    """
    for t in tasks:
        if t.category in ("trivial", "moderate"):
            tier, _ = classifier.pick_tier(t.text, DEFAULT.thresholds)
            assert tier.name == _EXPECTED_TIER[t.category], (t.category, t.text)


def test_hard_misclassification_rate_is_bounded(tasks):
    """Documents a real, known classifier weakness rather than hiding it.

    A minority of hard tasks contain only one hard-signal phrase (the
    memory-leak template) and score just under the strong threshold, landing
    on mid instead. This is caught here with an explicit upper bound so a
    regression that makes it *worse* fails CI, while the existing, understood
    gap does not.

    Correctness is not at risk: `test_pipeline.py` verifies escalation
    recovers every one of these misrouted tasks at the cost of one extra
    request per escalation.
    """
    hard = [t for t in tasks if t.category == "hard"]
    misrouted = sum(
        1 for t in hard
        if classifier.pick_tier(t.text, DEFAULT.thresholds)[0].name != "strong"
    )
    rate = misrouted / len(hard)
    assert 0 < rate <= 0.20, f"hard misclassification rate drifted to {rate:.2%}"


def test_all_misrouted_hard_tasks_go_to_mid_not_cheap(tasks):
    """An under-scored hard task should still land in the middle, never at
    the bottom -- landing at cheap would mean escalation needs two rungs
    instead of one, which the default ladder does not allow.
    """
    for t in tasks:
        if t.category != "hard":
            continue
        tier, _ = classifier.pick_tier(t.text, DEFAULT.thresholds)
        assert tier.name in ("mid", "strong")


def test_score_is_bounded_zero_to_one():
    tasks = build_tasks()
    for t in tasks:
        _, s = classifier.pick_tier(t.text, DEFAULT.thresholds)
        assert 0.0 <= s <= 1.0


def test_more_hard_signals_scores_at_least_as_high():
    one_signal = "There is a race condition somewhere in here."
    two_signals = "There is a race condition and a memory leak somewhere in here."
    _, s1 = classifier.pick_tier(one_signal, DEFAULT.thresholds)
    _, s2 = classifier.pick_tier(two_signals, DEFAULT.thresholds)
    assert s2 >= s1
