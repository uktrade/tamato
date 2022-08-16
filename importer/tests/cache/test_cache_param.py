import pytest

from importer.cache.cache import *
from importer.cache import base
from importer.cache import cache
from importer.cache import memory
from importer.cache import pickle
from importer.cache import redis


def does_not_raise():
    yield


# TODO  note : Redis cache defaults to django dummy cache - need to discuss getting redis on the CI server
# and actually testing redis interaction
test_data = [
    cache.ObjectCacheFacade,
    memory.MemoryCacheEngine,
    pickle.PickleCacheEngine,
    # redis.RedisCacheEngine,
]

@pytest.fixture(autouse=True)
def clear_object_cache():
    """
    Clears the object cache data for each test in this suite.

    Object cache will persist between tests so this is required for some tests
    in the suite to prepare a clean cache for subsequent tests. This fixture is
    only local to this set of tests and is not called for any other tests
    """
    object_cache = ObjectCacheFacade()
    object_cache.clear()

    object_cache = pickle.PickleCacheEngine()
    object_cache.clear()
    object_cache.dump()

    yield


@pytest.mark.parametrize("target", test_data)
def test_put_stores_value(target):
    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.get("test") == 123


@pytest.mark.parametrize("target", test_data)
def test_put_stores_value_when_value_exists(target):
    object_cache = target()
    object_cache.put("test", 123)
    object_cache.put("test", 456)
    assert object_cache.get("test") == 456


@pytest.mark.parametrize("target", test_data)
def test_pop_when_no_values_available_returns_none(target):
    object_cache = target()
    assert object_cache.pop("test") is None


@pytest.mark.parametrize("target", test_data)
def test_pop_removes_and_returns_value_whne_present(target):
    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.pop("test") == 123


@pytest.mark.parametrize("target", test_data)
def test_pop_returns_none_if_not_present(target):
    object_cache = target()
    assert object_cache.pop("test") is None


@pytest.mark.parametrize("target", test_data)
def test_keys_return_keys_correctly_when_populated(target):
    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()


@pytest.mark.parametrize("target", test_data)
def test_keys_return_keys_correctly_when_empty(target):
    object_cache = target()
    assert object_cache.keys() == {}.keys()


@pytest.mark.parametrize("target", test_data)
def test_dump_return_correctly(target):
    object_cache = target()
    assert object_cache.dump() is None


@pytest.mark.parametrize("target", test_data)
def test_clear_returns_correctly(target):
    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()
    object_cache.clear()
    assert object_cache.keys() == {}.keys()
