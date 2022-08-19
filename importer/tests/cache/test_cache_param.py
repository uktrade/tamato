import pytest

from importer.cache import cache, redis, memory, pickle


@pytest.fixture(autouse=True)
def clear_cache():
    cache.ObjectCacheFacade().clear()
    memory.MemoryCacheEngine().clear()
    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.clear()
    pickle_cache.dump()


# TODO  note : Redis cache defaults to django dummy cache - need to discuss getting redis on the CI server
# and actually testing redis interaction
test_data = [
    cache.ObjectCacheFacade,
    memory.MemoryCacheEngine,
    pickle.PickleCacheEngine,
    # redis.RedisCacheEngine,
]


@pytest.mark.parametrize("target", test_data)
def test_put_stores_value(target):
    """For all parameterized cache engines, test that the put method stores a
    value in the respective cache."""
    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.get("test") == 123


@pytest.mark.parametrize("target", test_data)
def test_put_stores_value_when_value_exists(target):
    """For all parameterized cache engines, test that the multiple put calls to
    same key overwrites stored value in the respective caches."""
    object_cache = target()
    object_cache.put("test", 123)
    object_cache.put("test", 456)
    assert object_cache.get("test") == 456


@pytest.mark.parametrize("target", test_data)
def test_pop_when_no_values_available_returns_none(target):
    """
    For all parameterized cache engines, test that pop calls to non-existent
    key returns None and does not throw exception etc.
    """

    object_cache = target()
    assert object_cache.pop("test") is None


@pytest.mark.parametrize("target", test_data)
def test_pop_removes_and_returns_value_when_present(target):
    """For all parameterized cache engines, test that pop returns and removes
    value from cache."""

    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.pop("test") == 123
    assert object_cache.pop("test") is None


@pytest.mark.parametrize("target", test_data)
def test_pop_returns_none_if_not_present(target):
    """For all parameterized cache engines, test that pop returns None when
    value not present."""

    object_cache = target()
    assert object_cache.pop("test") is None


@pytest.mark.parametrize("target", test_data)
def test_keys_return_keys_correctly_when_populated(target):
    """For all parameterized cache engines, test that keys returns as expected
    when populated."""

    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()


@pytest.mark.parametrize("target", test_data)
def test_keys_return_keys_correctly_when_empty(target):
    """For all parameterized cache engines, test that keys returns as expected
    when empty."""
    object_cache = target()
    assert object_cache.keys() == {}.keys()


@pytest.mark.parametrize("target", test_data)
def test_dump_return_correctly(target):
    """
    For all parameterized cache engines, test that dump returns as expected.

    Only used for pickle to write to file - but
    exists in base class.
    """

    object_cache = target()
    assert object_cache.dump() is None


@pytest.mark.parametrize("target", test_data)
def test_clear_returns_correctly(target):
    """For all parameterized cache engines, test that clear does clear the
    cache, verified by checking keys."""

    object_cache = target()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()
    object_cache.clear()
    assert object_cache.keys() == {}.keys()
