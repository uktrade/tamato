import pytest

from common.tests import factories
from common.tests.models import TestModel1
from common.validators import UpdateType
from footnotes.models import Footnote, FootnoteType
from importer import nursery
from importer.utils import DispatchedObjectType


def test_nursery_gets_handler_with_tag(object_nursery, handler_class):
    assert object_nursery.get_handler(handler_class.tag) is handler_class


def test_nursery_throws_error_on_no_handler(object_nursery):
    with pytest.raises(nursery.HandlerDoesNotExistError):
        object_nursery.get_handler("non-existent-tag")


@pytest.mark.django_db
def test_nursery_clears_cache(
        handler_class,
        object_nursery,
        date_ranges,
        unapproved_transaction,
):
    handler = handler_class(
        {
            "data": {
                "sid": 1,
                "name": "clears_cache",
                "update_type": UpdateType.CREATE,
                "valid_between": {
                    "lower": date_ranges.normal.lower,
                    "upper": date_ranges.normal.upper,
                },
            },
            "tag": handler_class.tag,
            "transaction_id": unapproved_transaction.pk,
        },
        object_nursery,
    )
    object_nursery._cache_handler(handler)

    assert TestModel1.objects.count() == 0
    assert object_nursery.cache.get(handler.key)

    object_nursery.clear_cache()

    assert object_nursery.cache.get(handler.key) is None
    assert TestModel1.objects.count() == 1
    assert TestModel1.objects.get().name == "clears_cache"
    assert TestModel1.objects.get().sid == 1


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


@pytest.mark.django_db
def test_nursery_gets_object_from_cache(settings, object_nursery):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    instance = factories.FootnoteFactory.create()
    object_nursery.cache_object(instance)

    identifying_fields = instance.get_identifying_fields()

    cached_instance = object_nursery.get_obj_from_cache(
        Footnote,
        identifying_fields.keys(),
        identifying_fields,
    )
    assert cached_instance == (instance.pk, instance.__class__.__name__)


@pytest.mark.django_db
def test_submit_commits_to_database(settings, object_nursery, handler_footnote_type_test_data, handler_footnote_type_description_test_data):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    expected_footnote_count = len(FootnoteType.objects.all()) + 1

    # create dispatch object
    footnote_type_dis_obj = handler_footnote_type_test_data
    footnote_type_description_dis_obj = handler_footnote_type_description_test_data


    # submit to nursery
    object_nursery.submit(footnote_type_description_dis_obj)
    object_nursery.submit(footnote_type_dis_obj)

    assert len(FootnoteType.objects.all()) == expected_footnote_count
