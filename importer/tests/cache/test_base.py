import pytest

from importer.cache import base


def test_initializer():
    """
    Test that the initializer gives type error since it's an abstract class
    """
    err = 'Can\'t instantiate abstract class BaseEngine with abstract methods clear, dump, get, keys, pop, put'
    with pytest.raises(TypeError) as ex:
        base.BaseEngine()
        assert ex.value == err
