import pytest
from factory import SubFactory
from factory.django import DjangoModelFactory

from tasks.tests.test_queue.models import TestQueue
from tasks.tests.test_queue.models import TestQueueItem

pytestmark = pytest.mark.django_db


class TestQueueFactory(DjangoModelFactory):
    """Factory for TestQueue."""

    class Meta:
        abstract = False
        model = TestQueue


class TestQueueItemFactory(DjangoModelFactory):
    """Factory for TestQueueItem."""

    class Meta:
        model = TestQueueItem
        abstract = False

    queue = SubFactory(TestQueueFactory)


def test_create_empty_queue():
    queue = TestQueueFactory.create()
    assert not queue.get_items()


def test_non_empty_queue():
    queue = TestQueueFactory.create()
    first_item = TestQueueItemFactory(queue=queue)
    second_item = TestQueueItemFactory(queue=queue)
    third_item = TestQueueItemFactory(queue=queue)

    assert first_item.position == 1
    assert second_item.position == 2
    assert third_item.position == 3
