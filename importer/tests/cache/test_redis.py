import pytest

from importer.cache import redis


@pytest.mark.skip(reason="WIP")
def test_put_stores_value():
    redis_cache = redis.RedisCacheEngine()
    redis_cache.put("test", 123)
    assert redis_cache.get("test") == 123


@pytest.mark.skip(reason="WIP")
def test_pop_removes_value():
    redis_cache = redis.RedisCacheEngine()
    redis_cache.put("test", 123)
    assert redis_cache.pop("test") == 123
    assert redis_cache.pop("test") is None


@pytest.mark.skip(reason="WIP")
def test_keys_return_keys_correctly():
    redis_cache = redis.RedisCacheEngine()
    redis_cache.put("test", 123)
    assert redis_cache.keys() == {'test': ''}.keys()


def test_dump_return_correctly():
    redis_cache = redis.RedisCacheEngine()
    assert redis_cache.dump() is None


@pytest.mark.skip(reason="WIP")
def test_clear_returns_correctly():
    redis_cache = redis.RedisCacheEngine()
    redis_cache.put("test", 123)
    assert redis_cache.keys() == {'test': ''}.keys()
    redis_cache.clear()
    assert redis_cache.keys() == {}.keys()
