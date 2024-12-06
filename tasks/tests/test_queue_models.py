import pytest
from django.db.models import CASCADE
from django.db.models import ForeignKey
from factory import SubFactory
from factory.django import DjangoModelFactory

from tasks.models import QueueItem
from tasks.models import RequiredFieldError
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


@pytest.fixture()
def queue() -> TestQueue:
    """Return an instance of TestQueue that contains no TestQueueItems."""
    queue = TestQueueFactory.create()

    assert not queue.get_items().exists()

    return queue


@pytest.fixture()
def single_item_queue(queue) -> TestQueue:
    """Return an instance of TestQueue containing a single TestQueueItem."""
    TestQueueItemFactory.create(queue=queue)

    assert queue.get_items().count() == 1

    return queue


@pytest.fixture()
def three_item_queue(queue) -> TestQueue:
    """Return an instance of TestQueue containing three TestQueueItem
    instances."""
    TestQueueItemFactory.create(queue=queue)
    TestQueueItemFactory.create(queue=queue)
    TestQueueItemFactory.create(queue=queue)

    assert queue.get_items().count() == 3

    return queue


def test_queueitem_metaclass_validation_missing_queue_field():
    """Tests that a concrete sublass of `QueueItem` must provide a queue field
    on the model."""
    with pytest.raises(RequiredFieldError) as error:

        class TestQueueItemSubclass(QueueItem):
            class Meta:
                abstract = False

        TestQueueItemSubclass()

    assert (
        "must have a 'queue' ForeignKey field. The name of the field must match the value given to the 'queue_field' attribute on the model."
        in str(error.value)
    )


def test_queueitem_metaclass_validation_mismatched_queue_field():
    """Tests that the `QueueItem.queue_field` attribute on a concrete subclass
    must match its queue ForeignKey field."""
    with pytest.raises(RequiredFieldError) as error:

        class TestQueueItemSubclass(QueueItem):
            class Meta:
                abstract = False

            queue_field = "test_queue"
            queue = ForeignKey(TestQueue, on_delete=CASCADE)

        TestQueueItemSubclass()

    assert (
        "The name of the field must match the value given to the 'queue_field' attribute on the model."
        in str(error.value)
    )


def test_queueitem_metaclass_validation_invalid_model():
    """Tests that a concrete subclass of `QueueItem` must have a ForeignKey
    field to a subclass of `Queue`."""
    with pytest.raises(RequiredFieldError) as error:

        class TestQueueItemSubclass(QueueItem):
            class Meta:
                abstract = False

            queue_field = "test_queue"
            test_queue = ForeignKey(QueueItem, on_delete=CASCADE)

        TestQueueItemSubclass()

    assert "must be a ForeignKey field to a subclass of 'Queue' model" in str(
        error.value,
    )


def test_empty_queue(queue):
    assert queue.max_position == 0
    assert queue.get_first() == None
    assert queue.get_item(1) == None
    assert queue.get_last() == None


def test_non_empty_queue(queue):
    first_item = TestQueueItemFactory.create(queue=queue)
    second_item = TestQueueItemFactory.create(queue=queue)
    third_item = TestQueueItemFactory.create(queue=queue)

    assert first_item.position == 1
    assert second_item.position == 2
    assert third_item.position == 3
    assert {first_item, second_item, third_item} == set(queue.get_items())
    assert queue.max_position == 3
    assert queue.get_items().count() == 3
    assert queue.get_first() == first_item
    assert queue.get_last() == third_item
    assert queue.get_item(2) == second_item


def test_item_delete(three_item_queue):
    three_item_queue.get_first().delete()

    assert three_item_queue.get_items().count() == 2

    three_item_queue.get_item(1).delete()
    three_item_queue.get_last().delete()

    assert three_item_queue.get_items().count() == 0


def test_item_promote(three_item_queue):
    item = three_item_queue.get_last()

    assert item.position == 3

    item = item.promote()
    item = item.promote()

    assert item.position == 1

    item = item.promote()

    assert item.position == 1


def test_item_demote(three_item_queue):
    item = three_item_queue.get_first()

    assert item.position == 1

    item = item.demote()
    item = item.demote()

    assert item.position == 3

    item = item.demote()

    assert item.position == 3


def test_item_demote_to_last(three_item_queue):
    item = three_item_queue.get_first()

    assert item.position == 1

    item = item.demote_to_last()

    assert item.position == 3

    item = item.demote_to_last()

    assert item.position == 3


def test_item_promote_to_first(three_item_queue):
    item = three_item_queue.get_last()

    assert item.position == 3

    item = item.promote_to_first()

    assert item.position == 1

    item = item.promote_to_first()

    assert item.position == 1
