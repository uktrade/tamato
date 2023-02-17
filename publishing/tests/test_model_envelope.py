from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import freezegun
import pytest
from freezegun import freeze_time

from common.tests import factories
from publishing.models import Envelope
from publishing.models import EnvelopeCurrentlyProccessing
from publishing.models import EnvelopeInvalidQueuePosition
from publishing.models import EnvelopeNoTransactions
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def _create_workbasket_with_tracked_models():
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.QUEUED,
    )
    with factories.ApprovedTransactionFactory.create(workbasket=workbasket):
        factories.FootnoteTypeFactory()
        factories.AdditionalCodeFactory()
    return workbasket


def _create_envelope(packaged_workbasket, envelope_storage, **kwargs):
    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        envelope = factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket, **kwargs
        )
        mock_save.assert_called_once()

    return envelope


def _create_successful_process_envelope(
    packaged_workbasket, envelope_storage, **kwargs
):
    envelope = _create_envelope(packaged_workbasket, envelope_storage, **kwargs)

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
    return envelope


def test_create_envelope(envelope_storage, settings):
    """Test multiple Envelope instances creates the correct."""
    workbasket = _create_workbasket_with_tracked_models()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_successful_process_envelope(
        packaged_workbasket,
        envelope_storage,
    )

    workbasket2 = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket2,
        )

    envelope2 = _create_envelope(packaged_workbasket2, envelope_storage)

    assert int(envelope.envelope_id[2:]) == 1
    assert int(envelope2.envelope_id[2:]) == 2
    assert int(envelope.envelope_id) < int(envelope2.envelope_id)


def test_create_currently_processing():
    """Test that an Envelope cannot be created when a packaged workbasket is
    currently processing."""

    workbasket = _create_workbasket_with_tracked_models()
    packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
        workbasket=workbasket,
    )
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

    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
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


def test_queryset_deleted(envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_envelope(
        packaged_workbasket,
        envelope_storage,
        deleted=True,
    )

    deleted_envelopes = Envelope.objects.deleted()

    assert deleted_envelopes.last() == envelope


def test_queryset_deleted_no_xml_file(envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_envelope(
        packaged_workbasket,
        envelope_storage,
        xml_file=None,
    )
    envelope.xml_file = ""
    envelope.save()
    deleted_envelopes = Envelope.objects.deleted()

    assert envelope in deleted_envelopes


def test_queryset_nondeleted(envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_successful_process_envelope(
        packaged_workbasket,
        envelope_storage,
    )

    non_deleted_envelopes = Envelope.objects.non_deleted()

    assert non_deleted_envelopes.last() == envelope


def test_queryset_nondeleted_condition(envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_successful_process_envelope(
        packaged_workbasket,
        envelope_storage,
        deleted=True,
    )

    workbasket2 = _create_workbasket_with_tracked_models()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket2,
        )
    envelope2 = _create_successful_process_envelope(
        packaged_workbasket2,
        envelope_storage,
        xml_file=None,
    )
    envelope2.xml_file = None
    envelope2.save()

    non_deleted_envelopes = Envelope.objects.non_deleted()

    assert envelope not in non_deleted_envelopes
    assert envelope2 not in non_deleted_envelopes


def test_queryset_for_year(approved_transaction, envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )

    with freeze_time("2022-01-01"):
        envelope = _create_successful_process_envelope(
            packaged_workbasket,
            envelope_storage,
        )

    workbasket2 = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket2,
        )
    with freeze_time("2023-01-01"):
        envelope2 = _create_envelope(
            packaged_workbasket2,
            envelope_storage,
        )
    current_year_envelopes = Envelope.objects.for_year()
    previous_year_envelopes = Envelope.objects.for_year(2022)

    assert envelope not in current_year_envelopes
    assert envelope in previous_year_envelopes
    assert envelope2 in current_year_envelopes
    assert envelope2 not in previous_year_envelopes


def test_queryset_processing_states(envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_envelope(
        packaged_workbasket,
        envelope_storage,
    )
    packaged_workbasket.envelope = envelope
    packaged_workbasket.save()

    unprocessed_result = Envelope.objects.unprocessed()
    assert envelope in unprocessed_result

    packaged_workbasket.begin_processing()

    currently_processing_result = Envelope.objects.currently_processing()
    assert envelope in currently_processing_result

    packaged_workbasket.processing_failed()

    failed_processing_result = Envelope.objects.failed_processing()
    assert envelope in failed_processing_result

    workbasket2 = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket2 = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket2,
        )
    envelope2 = _create_successful_process_envelope(
        packaged_workbasket2,
        envelope_storage,
    )

    success_processing_result = Envelope.objects.successfully_processed()
    assert envelope2 in success_processing_result


def test_delete_envelope(approved_transaction, envelope_storage):
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )
    envelope = _create_envelope(
        packaged_workbasket,
        envelope_storage,
    )

    envelope.delete_envelope()
    envelope.save()
    assert envelope.deleted == True
    assert envelope.xml_file.name is None


@freezegun.freeze_time("2023-01-01")
def test_next_envelope_id(envelope_storage):
    """Verify that envelope ID is made up of two digits of the year and a 4
    digit counter starting from 0001."""
    workbasket = _create_workbasket_with_tracked_models()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
            workbasket=workbasket,
        )

    _create_successful_process_envelope(packaged_workbasket, envelope_storage)
    assert Envelope.next_envelope_id() == "230002"
