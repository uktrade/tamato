import threading
from functools import wraps
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import freezegun
import pytest
from django.db import OperationalError
from django_fsm import TransitionNotAllowed

from common.tests import factories
from publishing.models import CrownDependenciesPublishingOperationalStatus
from publishing.models import Envelope
from publishing.models import EnvelopeCurrentlyProccessing
from publishing.models import EnvelopeInvalidQueuePosition
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import PackagedWorkBasketDuplication
from publishing.models import PackagedWorkBasketInvalidCheckStatus
from publishing.models import ProcessingState
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_create():
    """Test multiple PackagedWorkBasket instances creation is managed
    correctly."""

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        first_packaged_work_basket = factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        second_packaged_work_basket = factories.PackagedWorkBasketFactory()

    assert first_packaged_work_basket.position > 0
    assert second_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_create_duplicate_awaiting_instances():
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""

    packaged_work_basket = factories.PackagedWorkBasketFactory()
    with pytest.raises(PackagedWorkBasketDuplication):
        factories.PackagedWorkBasketFactory(workbasket=packaged_work_basket.workbasket)


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""

    editing_workbasket = factories.WorkBasketFactory(
        status=WorkflowStatus.EDITING,
    )
    with pytest.raises(PackagedWorkBasketInvalidCheckStatus):
        factories.PackagedWorkBasketFactory(workbasket=editing_workbasket)


def test_notify_ready_for_processing(
    packaged_workbasket_factory,
    published_envelope_factory,
    mocked_send_emails_apply_async,
    settings,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = True

    packaged_wb = packaged_workbasket_factory()
    envelope = published_envelope_factory(packaged_workbasket=packaged_wb)
    packaged_wb.notify_ready_for_processing()
    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "description": packaged_wb.description,
        "download_url": settings.BASE_SERVICE_URL + "/publishing/envelope-queue/",
        "theme": packaged_wb.theme,
        "eif": "Immediately",
        "embargo": str(packaged_wb.embargo),
        "jira_url": packaged_wb.jira_url,
    }
    mocked_send_emails_apply_async.assert_called_once()


def test_notify_processing_succeeded(
    mocked_send_emails_apply_async,
    packaged_workbasket_factory,
    published_envelope_factory,
    settings,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = True

    packaged_wb = packaged_workbasket_factory()
    loading_report = factories.LoadingReportFactory.create(
        packaged_workbasket=packaged_wb,
    )

    envelope = published_envelope_factory(packaged_workbasket=packaged_wb)

    packaged_wb.notify_processing_succeeded()

    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "transaction_count": packaged_wb.workbasket.transactions.count(),
        "loading_report_message": f"Loading report(s): {loading_report.file_name}",
        "comments": packaged_wb.loadingreports.first().comments,
    }
    mocked_send_emails_apply_async.assert_called_once()


def test_notify_processing_failed(
    mocked_send_emails_apply_async,
    packaged_workbasket_factory,
    published_envelope_factory,
    settings,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = True
    packaged_wb = packaged_workbasket_factory()
    loading_report1 = factories.LoadingReportFactory.create(
        packaged_workbasket=packaged_wb,
    )
    loading_report2 = factories.LoadingReportFactory.create(
        packaged_workbasket=packaged_wb,
    )

    envelope = published_envelope_factory(packaged_workbasket=packaged_wb)

    packaged_wb.notify_processing_failed()

    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "transaction_count": packaged_wb.workbasket.transactions.count(),
        "loading_report_message": f"Loading report(s): {loading_report1.file_name}, {loading_report2.file_name}",
        "comments": packaged_wb.loadingreports.first().comments,
    }

    mocked_send_emails_apply_async.assert_called_once()


def test_success_processing_transition(
    packaged_workbasket_factory,
    published_envelope_factory,
    envelope_storage,
    mocked_send_emails_apply_async,
    settings,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    packaged_workbasket = packaged_workbasket_factory()

    envelope = published_envelope_factory(
        packaged_workbasket=packaged_workbasket,
    )

    packaged_work_basket = PackagedWorkBasket.objects.get(position=1)
    assert packaged_work_basket.position == 1
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING

    packaged_work_basket.begin_processing()
    assert packaged_work_basket.processing_started_at
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )

    packaged_work_basket.processing_succeeded()
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED
    )


def test_begin_processing_transition_invalid_position():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().last()
    assert packaged_work_basket.position == PackagedWorkBasket.objects.max_position()
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    with pytest.raises(TransitionNotAllowed):
        packaged_work_basket.begin_processing()


def test_begin_processing_transition_invalid_start_state():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    # Begin processing the first instance in the queue.
    packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().first()
    assert packaged_work_basket.position == 1
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    packaged_work_basket.begin_processing()
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )

    # Try to start processing what is now the first instance in the queue,
    # which should fail - only one instance may be processed at any time.
    next_packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().first()
    assert (
        next_packaged_work_basket.position == PackagedWorkBasket.objects.max_position()
    )
    assert (
        next_packaged_work_basket.processing_state
        == ProcessingState.AWAITING_PROCESSING
    )
    with pytest.raises(TransitionNotAllowed):
        next_packaged_work_basket.begin_processing()


def test_abandon_transition():
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    assert packaged_work_basket.position > 0
    packaged_work_basket.abandon()
    assert packaged_work_basket.processing_state == ProcessingState.ABANDONED
    assert packaged_work_basket.position == 0


def test_abandon_transition_from_invalid_state():
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    packaged_work_basket.begin_processing()
    assert packaged_work_basket.processing_state == ProcessingState.CURRENTLY_PROCESSING
    assert packaged_work_basket.position == 0
    with pytest.raises(TransitionNotAllowed):
        packaged_work_basket.abandon()


def test_remove_from_queue():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_1 = factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_2 = factories.PackagedWorkBasketFactory()

    assert packaged_work_basket_1.position == 1
    assert packaged_work_basket_2.position == 2

    packaged_work_basket_1.remove_from_queue()
    packaged_work_basket_2.refresh_from_db()

    assert packaged_work_basket_1.position == 0
    assert packaged_work_basket_2.position == 1


def test_promote_to_top_position():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    packaged_work_basket = PackagedWorkBasket.objects.last()
    assert packaged_work_basket.position == PackagedWorkBasket.objects.max_position()

    packaged_work_basket.promote_to_top_position()
    assert packaged_work_basket.position == 1
    assert PackagedWorkBasket.objects.filter(position=1).count() == 1


def test_promote_position():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    initially_first = PackagedWorkBasket.objects.get(position=1)
    initially_second = PackagedWorkBasket.objects.get(position=2)
    initially_second.promote_position()
    initially_first.refresh_from_db()
    assert initially_first.position == 2
    assert initially_second.position == 1


def test_demote_position():
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    initially_first = PackagedWorkBasket.objects.get(position=1)
    initially_second = PackagedWorkBasket.objects.get(position=2)
    initially_first.demote_position()
    initially_second.refresh_from_db()
    assert initially_first.position == 2
    assert initially_second.position == 1


def test_cannot_promote_or_demote_removed_packaged_workbasket():
    """Tests that packaged workbasket positions remain unchanged after
    attempting to reposition a packaged workbasket that has since been removed
    from the queue."""
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        factories.PackagedWorkBasketFactory()

    queued_pwb = PackagedWorkBasket.objects.get(position=1)
    removed_pwb = PackagedWorkBasket.objects.get(position=2)
    removed_pwb.abandon()

    removed_pwb = removed_pwb.promote_to_top_position()
    assert removed_pwb.position == 0
    queued_pwb.refresh_from_db()
    assert queued_pwb.position == 1

    removed_pwb = removed_pwb.demote_position()
    assert removed_pwb.position == 0
    queued_pwb.refresh_from_db()
    assert queued_pwb.position == 1


def test_pause_and_unpause_queue(unpause_queue):
    assert not OperationalStatus.is_queue_paused()
    OperationalStatus.pause_queue(user=None)
    assert OperationalStatus.is_queue_paused()
    OperationalStatus.unpause_queue(user=None)
    assert not OperationalStatus.is_queue_paused()


@pytest.mark.skip(
    reason="TODO correctly implement file save & duplicate create_envelope_task_id_key",
)
def test_create_envelope(envelope_storage, settings):
    """Test multiple Envelope instances creates the correct."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    packaged_workbasket = factories.QueuedPackagedWorkBasketFactory()
    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        envelope = factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
        )
        mock_save.assert_called_once()

    packaged_workbasket.envelope = envelope
    packaged_workbasket.save()
    packaged_workbasket.begin_processing()
    assert packaged_workbasket.position == 0
    assert (
        packaged_workbasket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )
    packaged_workbasket.processing_succeeded()
    assert packaged_workbasket.position == 0
    assert (
        packaged_workbasket.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED
    )

    packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory()

    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        envelope2 = factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket2,
        )
        mock_save.assert_called_once()

    assert int(envelope.envelope_id[2:]) == 1
    assert int(envelope2.envelope_id[2:]) == 2
    assert int(envelope.envelope_id) < int(envelope2.envelope_id)


def test_create_currently_processing():
    """Test that an Envelope cannot be created when a packaged workbasket is
    currently processing."""

    packaged_workbasket = factories.QueuedPackagedWorkBasketFactory()
    packaged_workbasket.begin_processing()
    assert packaged_workbasket.position == 0
    assert (
        packaged_workbasket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )
    with pytest.raises(EnvelopeCurrentlyProccessing):
        factories.PublishedEnvelopeFactory()


def test_create_invalid_queue_position():
    """Test that an Envelope cannot be created when the packaged workbasket is
    not at the front of the queue."""

    packaged_workbasket = factories.QueuedPackagedWorkBasketFactory()
    packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory()

    assert packaged_workbasket.position < packaged_workbasket2.position

    with pytest.raises(EnvelopeInvalidQueuePosition):
        factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket2,
        )


@pytest.mark.skip(
    reason="TODO correctly implement file save",
)
@freezegun.freeze_time("2023-01-01")
def test_next_envelope_id(envelope_storage):
    """Verify that envelope ID is made up of two digits of the year and a 4
    digit counter starting from 0001."""
    packaged_workbasket = factories.QueuedPackagedWorkBasketFactory()
    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ):
        envelope = factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
        )
    packaged_workbasket.envelope = envelope
    packaged_workbasket.save()
    packaged_workbasket.begin_processing()
    packaged_workbasket.processing_succeeded()
    assert Envelope.next_envelope_id() == "230002"


@pytest.mark.django_db(transaction=True)
class TestPackagingQueueRaceConditions:
    """Tests that concurrent requests to reorder packaged workbaskets don't
    result in duplicate or non-consecutive positions."""

    NUM_THREADS: int = 2
    """The number of threads each test uses."""

    THREAD_TIMEOUT: int = 5
    """The duration in seconds to wait for a thread to complete before timing
    out."""

    NUM_PACKAGED_WORKBASKETS: int = 5
    """The number of packaged workbaskets to create for each test."""

    @pytest.fixture(autouse=True)
    def setup(self, settings):
        """Initialises a barrier to synchronise threads and creates packaged
        workbaskets anew for each test."""
        settings.ENABLE_PACKAGING_NOTIFICATIONS = False

        self.unexpected_exceptions = []

        self.barrier = threading.Barrier(
            parties=self.NUM_THREADS,
            timeout=self.THREAD_TIMEOUT,
        )

        for _ in range(self.NUM_PACKAGED_WORKBASKETS):
            self._create_packaged_workbasket()

        self.packaged_workbaskets = PackagedWorkBasket.objects.filter(
            processing_state__in=ProcessingState.queued_states(),
        )

    def _create_packaged_workbasket(self):
        """Creates a new packaged workbasket with a unique
        create_envelope_task_id."""
        with patch(
            "publishing.tasks.create_xml_envelope_file.apply_async",
            return_value=MagicMock(id=factory.Faker("uuid4")),
        ):
            factories.QueuedPackagedWorkBasketFactory()

    def assert_no_unexpected_exceptions(self):
        """Asserts that no threads raised an unexpected exception."""
        assert (
            not self.unexpected_exceptions
        ), f"Unexpected exception(s) raised: {self.unexpected_exceptions}"

    def assert_expected_positions(self):
        """Asserts that positions in the packaging queue are both unique and in
        consecutive sequence."""
        positions = list(
            PackagedWorkBasket.objects.filter(
                processing_state__in=ProcessingState.queued_states(),
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
            except (TransitionNotAllowed, OperationalError):
                pass
            except Exception as error:
                self.unexpected_exceptions.append(error)

        return wrapper

    @synchronised
    def synchronised_call(
        self,
        method_name: str,
        packaged_workbasket: PackagedWorkBasket,
    ):
        """
        Thread-synchronised wrapper for the following `PackagedWorkBasket`

        instance methods:
        - begin_processing
        - abandon
        - promote_to_top_position
        - promote
        - demote
        """
        getattr(packaged_workbasket, method_name)()

    @synchronised
    def synchronised_create_packaged_workbasket(self):
        """Thread-synchronised wrapper method to create a new
        `PackagedWorkbasket` instance."""
        self._create_packaged_workbasket()

    def execute_threads(self, threads: list[threading.Thread]):
        """Starts a list of threads and waits for them to complete or
        timeout."""
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=self.THREAD_TIMEOUT)
            if thread.is_alive():
                raise RuntimeError(f"Thread {thread.name} timed out.")

    def test_process_and_promote_to_top_packaged_workbaskets(self):
        """Begins processing the top-most packaged workbasket while promoting to
        the top the packaged workbasket in last place."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "begin_processing",
                "packaged_workbasket": self.packaged_workbaskets[0],
            },
            name="BeginProcessingThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote_to_top_position",
                "packaged_workbasket": self.packaged_workbaskets[4],
            },
            name="PromoteToTopThread2",
        )

        self.execute_threads(threads=[thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()

    def test_promote_and_promote_to_top_packaged_workbaskets(self):
        """Promotes to the top the last-placed packaged workbasket while
        promoting the one above it."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote_to_top_position",
                "packaged_workbasket": self.packaged_workbaskets[4],
            },
            name="PromoteToTopThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "begin_processing",
                "packaged_workbasket": self.packaged_workbaskets[3],
            },
            name="BeginProcessingThread2",
        )

        self.execute_threads(threads=[thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()

    def test_demote_and_promote_packaged_workbaskets(self):
        """Demotes and promotes the same packaged workbasket."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "demote_position",
                "packaged_workbasket": self.packaged_workbaskets[2],
            },
            name="DemotePositionThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "promote_position",
                "packaged_workbasket": self.packaged_workbaskets[2],
            },
            name="PromotePositionThread2",
        )

        self.execute_threads(threads=[thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()

    def test_abandon_and_create_packaged_workbaskets(self):
        """Abandons the last-placed packaged workbasket while creating a new
        one."""
        thread1 = threading.Thread(
            target=self.synchronised_call,
            kwargs={
                "method_name": "abandon",
                "packaged_workbasket": self.packaged_workbaskets[4],
            },
            name="AbandonThread1",
        )
        thread2 = threading.Thread(
            target=self.synchronised_create_packaged_workbasket,
            name="CreateThread2",
        )

        self.execute_threads(threads=[thread1, thread2])
        self.assert_no_unexpected_exceptions()
        self.assert_expected_positions()


def test_crown_dependencies_publishing_pause_and_unpause(unpause_publishing):
    """Test that Crown Dependencies publishing operational status can be paused
    and unpaused."""
    assert not CrownDependenciesPublishingOperationalStatus.is_publishing_paused()

    paused = CrownDependenciesPublishingOperationalStatus.pause_publishing(user=None)
    assert (
        paused == CrownDependenciesPublishingOperationalStatus.objects.current_status()
    )
    assert CrownDependenciesPublishingOperationalStatus.is_publishing_paused()

    unpaused = CrownDependenciesPublishingOperationalStatus.unpause_publishing(
        user=None,
    )
    assert (
        unpaused
        == CrownDependenciesPublishingOperationalStatus.objects.current_status()
    )
    assert not CrownDependenciesPublishingOperationalStatus.is_publishing_paused()
