from importer.cache import cache


def test_put_stores_value():
    object_cache = cache.ObjectCacheFacade()

    object_cache.put("test", 123)

    assert object_cache.get("test") == 123


def test_pop_removes_value():
    object_cache = cache.ObjectCacheFacade()

    object_cache.put("test", 123)

    assert object_cache.pop("test") == 123
    assert object_cache.pop("test") is None
