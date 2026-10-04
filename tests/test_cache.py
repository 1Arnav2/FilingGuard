from filingguard.llm.cache import DiskCache, cache_key


def test_key_ignores_dict_order():
    assert cache_key({"a": 1, "b": 2}) == cache_key({"b": 2, "a": 1})


def test_key_changes_with_any_field():
    base = {"model": "m", "prompt": "p", "params": {}}
    assert cache_key(base) != cache_key({**base, "model": "m2"})
    assert cache_key(base) != cache_key({**base, "prompt": "p2"})
    assert cache_key(base) != cache_key({**base, "params": {"temperature": 0}})


def test_miss_returns_none(tmp_path):
    assert DiskCache(tmp_path).get(cache_key({"x": 1})) is None


def test_put_then_get_round_trips(tmp_path):
    cache = DiskCache(tmp_path)
    key = cache_key({"x": 1})
    cache.put(key, {"text": "héllo"})
    assert cache.get(key) == {"text": "héllo"}
    assert not list(tmp_path.rglob("*.tmp"))
