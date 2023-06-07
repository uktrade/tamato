from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import freezegun
import pytest
from django.conf import settings
from django_fsm import TransitionNotAllowed

from common.tests import factories
from publishing.models import CrownDependenciesPublishingOperationalStatus
from publishing.models import Envelope
from publishing.models import EnvelopeCurrentlyProccessing
from publishing.models import EnvelopeInvalidQueuePosition
from publishing.models import EnvelopeNoTransactions
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
    mocked_publishing_models_send_emails_delay,
):
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
    mocked_publishing_models_send_emails_delay.assert_called_once_with(
        template_id=settings.READY_FOR_CDS_TEMPLATE_ID,
        personalisation=personalisation,
        email_type="packaging",
    )


def test_notify_processing_succeeded(
    mocked_publishing_models_send_emails_delay,
    packaged_workbasket_factory,
    published_envelope_factory,
):
    packaged_wb = packaged_workbasket_factory(
        loading_report__comments="comment",
    )

    envelope = published_envelope_factory(packaged_workbasket=packaged_wb)

    packaged_wb.notify_processing_succeeded()

    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "transaction_count": packaged_wb.workbasket.transactions.count(),
        "loading_report_message": "Loading report: No loading report was provided.",
        "comments": "comment",
    }
    mocked_publishing_models_send_emails_delay.assert_called_once_with(
        template_id=settings.CDS_ACCEPTED_TEMPLATE_ID,
        personalisation=personalisation,
        email_type="packaging",
    )


def test_notify_processing_failed(
    mocked_publishing_models_send_emails_delay,
    packaged_workbasket_factory,
    published_envelope_factory,
):
    packaged_wb = packaged_workbasket_factory(
        loading_report__comments="comment",
    )

    envelope = published_envelope_factory(packaged_workbasket=packaged_wb)

    packaged_wb.notify_processing_failed()

    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "transaction_count": packaged_wb.workbasket.transactions.count(),
        "loading_report_message": "Loading report: No loading report was provided.",
        "comments": "comment",
    }

    mocked_publishing_models_send_emails_delay.assert_called_once_with(
        template_id=settings.CDS_REJECTED_TEMPLATE_ID,
        personalisation=personalisation,
        email_type="packaging",
    )


def test_success_processing_transition(
    packaged_workbasket_factory,
    published_envelope_factory,
    envelope_storage,
    mocked_publishing_models_send_emails_delay,
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


def test_upload_envelope_no_transactions():
    packaged_workbasket = factories.PackagedWorkBasketFactory()
    with pytest.raises(EnvelopeNoTransactions):
        factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
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
