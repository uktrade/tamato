import pytest

from importer.cache import base


def test_put_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.put("test", 123)


def test_get_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.get("test")


def test_pop_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.pop("test")


def test_keys_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.keys()


def test_dump_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.dump()


def test_clear_raises_not_implemented_error():
    base_cache = base.BaseEngine()
    with pytest.raises(NotImplementedError):
        base_cache.clear()
