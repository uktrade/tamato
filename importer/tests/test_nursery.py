import pytest

from importer import nursery


def test_nursery_gets_handler_with_tag(object_nursery, handler_class):
    assert object_nursery.get_handler(handler_class.tag) is handler_class


def test_nursery_throws_error_on_no_handler(object_nursery):
    with pytest.raises(nursery.HandlerDoesNotExistError):
        object_nursery.get_handler("non-existent-tag")


def test_nursery_caches_object(object_nursery, handler_class):
    handler = handler_class(
        {
            "data": {"sid": 1},
            "tag": "some unique tag",
            "transaction_id": 1,
        },
        object_nursery,
    )
    object_nursery._cache_handler(handler)

    cached_handler = object_nursery.get_handler_from_cache(handler.key)

    assert handler.data == cached_handler.data
    assert handler.tag == cached_handler.tag
    assert handler.key == cached_handler.key
