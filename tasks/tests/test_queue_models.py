import threading
from functools import wraps

import pytest
from django.db import OperationalError
from django.db.models import CASCADE
from django.db.models import ForeignKey
from django.db.models import QuerySet
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


@pytest.mark.django_db(transaction=True)
class TestQueueRaceConditions:
    """Tests that concurrent requests to reorder queue items don't result in
    duplicate or non-consecutive positions."""

    NUM_THREADS: int = 2
    """The number of threads each test uses."""

    THREAD_TIMEOUT: int = 15
    """The duration in seconds to wait for a thread to complete before timing
    out."""

    NUM_QUEUE_ITEMS: int = 5
    """The number of queue items to create for each test."""

    @pytest.fixture(autouse=True)
    def setup(self, queue):
        """Initialises a barrier to synchronise threads and creates queue items
        anew for each test."""

        self.unexpected_exceptions: list[Exception] = []

        self.barrier: threading.Barrier = threading.Barrier(
            parties=self.NUM_THREADS,
            timeout=self.THREAD_TIMEOUT,
        )

        self.queue: TestQueue = queue
        self.queue_items: QuerySet[TestQueueItem] = TestQueueItemFactory.create_batch(
            self.NUM_QUEUE_ITEMS,
            queue=queue,
        )

    def assert_no_unexpected_exceptions(self):
        """Asserts that no threads raised an unexpected exception."""
        assert (
            not self.unexpected_exceptions
        ), f"Unexpected exception(s) raised: {self.unexpected_exceptions}"

    def assert_expected_positions(self):
        """Asserts that queue item positions remain both unique and in
        consecutive sequence."""
        positions = list(
            TestQueueItem.objects.filter(
                queue=self.queue,
            )
            .order_by("position")
            .values_list("position", flat=True),
        )

        assert len(set(positions)) == len(positions), "Duplicate positions found!"

        assert positions == list(
            range(min(positions), max(positions) + 1),
        ), "Non-consecutive positions found!"

    def synchronised(func):
        """
        Decorator that ensures all threads wait until they can call their target
        function in a synchronised fashion.

        Any unexpected exceptions raised during the execution of the decorated
        function are stored for the individual test to re-raise.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                self.barrier.wait()
                func(self, *args, **kwargs)
            except OperationalError:
                # A conflicting lock is already acquired
                pass
            except Exception as error:
                self.unexpected_exceptions.append(error)

        return wrapper

    @synchronised
    def synchronised_call(
        self,
        method_name: str,
        queue_item: TestQueueItem,
    ):
        """
        Thread-synchronised wrapper for the following `QueueItem` instance
        methods:

        - delete
        - promote
        - demote
        - promote_to_first
        - demote_to_last
        """
        getattr(queue_item, method_name)()

    @synchronised
    def synchronised_create_queue_item(self):
        """Thread-synchronised wrapper to create a new queue item instance."""
        TestQueueItemFactory.create(queue=self.queue)

    def execute_threads(self, threads: list[threading.Thread]):
        """Starts a list of threads and waits for them to complete or
        timeout."""
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=self.THREAD_TIMEOUT)
            if thread.is_alive():
                raise RuntimeError(f"Thread {thread.name} timed out.")

    def test_demote_and_promote_queue_items(self):
        """Demotes and promotes the same queue item."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "demote",
                "queue_item": self.queue_items[2],
            },
            name="DemoteItemThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote",
                "queue_item": self.queue_items[2],
            },
            name="PromoteItemThread2",
        )

        self.execute_threads([thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()

    def test_delete_and_create_queue_items(self):
        """Deletes the first item while creating a new one."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "delete",
                "queue_item": self.queue_items[0],
            },
            name="DeleteItemThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_create_queue_item,
            name="CreateItemThread2",
        )

        self.execute_threads([thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()

    def test_promote_and_promote_to_first_queue_items(self):
        """Promotes to first the last-placed item while promoting the one before
        it."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote_to_first",
                "queue_item": self.queue_items[4],
            },
            name="PromoteItemToFirstThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote",
                "queue_item": self.queue_items[3],
            },
            name="PromoteItemThread2",
        )

        self.execute_threads([thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()
