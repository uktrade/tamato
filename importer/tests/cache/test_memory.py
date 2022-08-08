from importer.cache import memory


def test_put_stores_value():
    memory_cache = memory.MemoryCacheEngine()
    memory_cache.put("test", 123)
    assert memory_cache.get("test") == 123


def test_pop_removes_value():
    memory_cache = memory.MemoryCacheEngine()
    memory_cache.put("test", 123)
    assert memory_cache.pop("test") == 123
    assert memory_cache.pop("test") is None


def test_keys_return_keys_correctly():
    memory_cache = memory.MemoryCacheEngine()
    memory_cache.put("test", 123)
    assert memory_cache.keys() == {'test': ''}.keys()


def test_dump_return_correctly():
    memory_cache = memory.MemoryCacheEngine()
    assert memory_cache.dump() is None


def test_clear_returns_correctly():
    memory_cache = memory.MemoryCacheEngine()
    memory_cache.put("test", 123)
    assert memory_cache.keys() == {'test': ''}.keys()
    memory_cache.clear()
    assert memory_cache.keys() == {}.keys()
