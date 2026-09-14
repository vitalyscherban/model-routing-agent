from router.cache import Cache, normalize


def test_normalize_strips_known_filler_prefixes():
    assert normalize("Quick one: what is X?") == normalize("what is X?")
    assert normalize("Hey, what is X?") == normalize("what is X?")
    assert normalize("Following up -- what is X?") == normalize("what is X?")


def test_normalize_is_case_and_whitespace_insensitive():
    assert normalize("  What   IS   X?  ") == normalize("what is x?")


def test_normalize_does_not_touch_unprefixed_text():
    assert normalize("what is X?") == "what is x?"


def test_cache_miss_then_hit():
    cache = Cache()
    assert cache.get("what is X?") is None
    cache.put("what is X?", "the answer")
    assert cache.get("Quick one: what is X?") == "the answer"
    assert cache.hits == 1
    assert cache.misses == 1


def test_hit_rate_is_zero_with_no_lookups():
    assert Cache().hit_rate == 0.0


def test_hit_rate_reflects_mixed_traffic():
    cache = Cache()
    cache.put("a", "answer-a")
    cache.get("a")       # hit
    cache.get("a")       # hit
    cache.get("unseen")  # miss
    assert cache.hit_rate == 2 / 3
