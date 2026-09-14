from router.tasks import CATEGORIES, build_tasks, stats


def test_corpus_is_deterministic():
    a = build_tasks()
    b = build_tasks()
    assert [t.text for t in a] == [t.text for t in b]
    assert [t.category for t in a] == [t.category for t in b]


def test_different_seed_gives_a_different_corpus():
    a = build_tasks(seed=1)
    b = build_tasks(seed=2)
    assert [t.text for t in a] != [t.text for t in b]


def test_every_category_is_represented(tasks):
    present = {t.category for t in tasks}
    assert present == set(CATEGORIES)


def test_trivial_tasks_are_the_largest_share(tasks):
    s = stats(tasks)
    counts = s["by_category"]
    assert counts["trivial"] > counts["moderate"] > counts["hard"]


def test_duplicates_reference_a_real_earlier_task(tasks):
    by_id = {t.id: t for t in tasks}
    for t in tasks:
        if t.duplicate_of is not None:
            assert t.duplicate_of in by_id
            original = by_id[t.duplicate_of]
            assert original.category == t.category
            assert original.text in t.text or original.text == t.text


def test_requested_duplicate_ratio_is_approximately_honored():
    tasks = build_tasks(count=400, duplicate_ratio=0.25)
    s = stats(tasks)
    ratio = s["duplicates"] / s["total"]
    assert 0.20 <= ratio <= 0.30


def test_count_zero_produces_no_tasks():
    tasks = build_tasks(count=0)
    assert tasks == []
