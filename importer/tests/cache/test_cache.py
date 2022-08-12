import pytest

from importer import cache


@pytest.fixture(autouse=True)
def clear_object_cache():
    """
    Clears the object cache data for each test in this suite

    Object cache will persist between tests so this is required for some tests in the suite to prepare a clean cache for
    subsequent tests. This fixture is only local to this set of tests and is not called for any other tests
    """
    object_cache = cache.ObjectCacheFacade()
    object_cache.clear()
    yield


def test_put_stores_value():
    object_cache = cache.ObjectCacheFacade()
    object_cache.put("test", 123)
    assert object_cache.get("test") == 123


def test_put_stores_value_when_value_exists():
    object_cache = cache.ObjectCacheFacade()
    object_cache.put("test", 123)
    object_cache.put("test", 456)
    assert object_cache.get("test") == 456


def test_pop_when_no_values_available_returns_none():
    object_cache = cache.ObjectCacheFacade()
    assert object_cache.pop("test") is None


def test_pop_removes_and_returns_value_whne_present():
    object_cache = cache.ObjectCacheFacade()
    object_cache.put("test", 123)
    assert object_cache.pop("test") == 123


def test_pop_returns_none_if_not_present():
    object_cache = cache.ObjectCacheFacade()
    assert object_cache.pop("test") is None


def test_keys_return_keys_correctly_when_populated():
    object_cache = cache.ObjectCacheFacade()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()


def test_keys_return_keys_correctly_when_empty():
    object_cache = cache.ObjectCacheFacade()
    assert object_cache.keys() == {}.keys()


def test_dump_return_correctly():
    object_cache = cache.ObjectCacheFacade()
    assert object_cache.dump() is None


def test_clear_returns_correctly():
    object_cache = cache.ObjectCacheFacade()
    object_cache.put("test", 123)
    assert object_cache.keys() == {"test": ""}.keys()
    object_cache.clear()
    assert object_cache.keys() == {}.keys()
