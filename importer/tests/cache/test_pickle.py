from importer.cache import pickle
import os


def test_init_no_cache_file():
    cwd = os.getcwd()
    cache_file = f'{cwd}/{pickle.PickleCacheEngine.CACHE_FILE}'
    if os.path.exists(cache_file):
        os.remove(cache_file)

    pickle_cache = pickle.PickleCacheEngine()
    assert isinstance(pickle_cache, pickle.PickleCacheEngine)


def test_init_with_cache_file():
    cwd = os.getcwd()
    cache_file = f'{cwd}/{pickle.PickleCacheEngine.CACHE_FILE}'
    if os.path.exists(cache_file):
        os.remove(cache_file)

    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.put("test", 123)
    pickle_cache.dump()

    assert os.path.exists(cache_file)

    pickle_cache_with_pickle_file_present = pickle.PickleCacheEngine()

    assert isinstance(pickle_cache, pickle.PickleCacheEngine)
    assert isinstance(pickle_cache_with_pickle_file_present, pickle.PickleCacheEngine)


def test_put_stores_value():
    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.put("test", 123)
    assert pickle_cache.get("test") == 123


def test_pop_removes_value():
    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.put("test", 123)
    assert pickle_cache.pop("test") == 123
    assert pickle_cache.pop("test") is None


def test_keys_return_keys_correctly():
    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.put("test", 123)
    assert pickle_cache.keys() == {'test': ''}.keys()


def test_dump_return_correctly():
    pickle_cache = pickle.PickleCacheEngine()
    assert pickle_cache.dump() is None


def test_clear_returns_correctly():
    pickle_cache = pickle.PickleCacheEngine()
    pickle_cache.put("test", 123)
    assert pickle_cache.keys() == {'test': ''}.keys()
    pickle_cache.clear()
    assert pickle_cache.keys() == {}.keys()
