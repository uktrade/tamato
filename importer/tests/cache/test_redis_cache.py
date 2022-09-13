import pytest
from django_fakeredis.fakeredis import FakeRedis

from importer.cache import redis


@FakeRedis("django.core.cache")
def test_put_stores_value():
    """For all parameterized cache engines, test that the put method stores a
    value in the respective cache."""
    object_cache = redis.RedisCacheEngine()
    object_cache.put("test", 123)
    assert object_cache.get("test") == 123


@FakeRedis("django.core.cache")
def test_put_stores_value_when_value_exists():
    """For all parameterized cache engines, test that the multiple put calls to
    same key overwrites stored value in the respective caches."""
    object_cache = redis.RedisCacheEngine()
    object_cache.put("test", 123)
    object_cache.put("test", 456)
    assert object_cache.get("test") == 456


@FakeRedis("django.core.cache")
def test_pop_when_no_values_available_returns_none():
    """For all parameterized cache engines, test that pop calls to non-existent
    key returns None and does not throw exception etc."""
    object_cache = redis.RedisCacheEngine()
    object_cache.clear()
    assert object_cache.pop("zoo") is None


@FakeRedis("django.core.cache")
def test_pop_removes_and_returns_value_when_present():
    """For all parameterized cache engines, test that pop returns and removes
    value from cache."""

    object_cache = redis.RedisCacheEngine()
    object_cache.put("test", 123)
    assert object_cache.pop("test") == 123
    assert object_cache.pop("test") is None


@FakeRedis("django.core.cache")
def test_pop_returns_none_if_not_present():
    """For all parameterized cache engines, test that pop returns None when
    value not present."""

    object_cache = redis.RedisCacheEngine()
    assert object_cache.pop("test") is None


@FakeRedis("django.core.cache")
@pytest.mark.skip(reason="no way of currently testing this without redis")
def test_keys_return_keys_correctly_when_populated():
    """For all parameterized cache engines, test that keys returns as expected
    when populated."""

    object_cache = redis.RedisCacheEngine()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()


@FakeRedis("django.core.cache")
@pytest.mark.skip(reason="no way of currently testing this without redis")
def test_keys_return_keys_correctly_when_empty():
    """For all parameterized cache engines, test that keys returns as expected
    when empty."""
    object_cache = redis.RedisCacheEngine()
    assert object_cache.keys() == {}.keys()


@FakeRedis("django.core.cache")
def test_dump_return_correctly():
    """
    For all parameterized cache engines, test that dump returns as expected.

    Only used for pickle to write to file - but
    exists in base class.
    """

    object_cache = redis.RedisCacheEngine()
    assert object_cache.dump() is None


@FakeRedis("django.core.cache")
@pytest.mark.skip(reason="no way of currently testing this without redis")
def test_clear_returns_correctly():
    """For all parameterized cache engines, test that clear does clear the
    cache, verified by checking keys."""

    object_cache = redis.RedisCacheEngine()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()
    object_cache.clear()
    assert object_cache.keys() == {}.keys()
