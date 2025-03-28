from datetime import date
from unittest import mock

import freezegun
import pytest
from freezegun import freeze_time

from common.tests import factories
from publishing.models import Envelope
from publishing.models import EnvelopeCurrentlyProccessing
from publishing.models import EnvelopeInvalidQueuePosition
from publishing.models import PackagedWorkBasket
from publishing.models.envelope import ValidationState
from publishing.util import TaricDataAssertionError

pytestmark = pytest.mark.django_db


def test_create_envelope(
    successful_envelope_factory,
    published_envelope_factory,
    settings,
):
    """Test multiple Envelope instances creates the correct."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    envelope = successful_envelope_factory()
    envelope2 = published_envelope_factory()

    assert int(envelope.envelope_id[2:]) == 1
    assert int(envelope2.envelope_id[2:]) == 2
    assert int(envelope.envelope_id) < int(envelope2.envelope_id)


def test_create_currently_processing(packaged_workbasket_factory):
    """Test that an Envelope cannot be created when a packaged workbasket is
    currently processing."""

    packaged_workbasket = packaged_workbasket_factory()
    packaged_workbasket.begin_processing()
    assert packaged_workbasket.position == 0
    assert (
        packaged_workbasket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )
    with pytest.raises(EnvelopeCurrentlyProccessing):
        factories.PublishedEnvelopeFactory()


def test_create_invalid_queue_position(packaged_workbasket_factory):
    """Test that an Envelope cannot be created when the packaged workbasket is
    not at the front of the queue."""

    packaged_workbasket = packaged_workbasket_factory()
    packaged_workbasket2 = packaged_workbasket_factory()

    assert packaged_workbasket.position < packaged_workbasket2.position

    with pytest.raises(EnvelopeInvalidQueuePosition):
        factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket2,
        )


def test_upload_envelope_no_transactions():
    """Test that an Envelope cannot be created when there are no
    transactions."""
    packaged_workbasket = factories.PackagedWorkBasketFactory()
    envelope = factories.PublishedEnvelopeFactory(
        packaged_work_basket=packaged_workbasket,
    )
    assert (
        envelope.validation_state == ValidationState.FAILED_TARIC_DATA_ASSERTION_ERROR
    )


def test_queryset_deleted(successful_envelope_factory, settings):
    """Test Envelope queryset deleted returns expected envelopes."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = successful_envelope_factory(deleted=True)
    envelope2 = successful_envelope_factory()
    envelope2.xml_file = ""
    envelope2.save()
    envelope3 = successful_envelope_factory()
    deleted_envelopes = Envelope.objects.deleted()

    assert envelope in deleted_envelopes
    assert envelope2 in deleted_envelopes
    assert envelope3 not in deleted_envelopes


def test_queryset_nondeleted(successful_envelope_factory, settings):
    """Test Envelope queryset non_deleted returns expected envelopes."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = successful_envelope_factory()
    envelope2 = successful_envelope_factory(
        deleted=True,
    )
    envelope3 = successful_envelope_factory()
    envelope3.xml_file = ""
    envelope3.save()
    non_deleted_envelopes = Envelope.objects.non_deleted()

    assert envelope in non_deleted_envelopes
    assert envelope2 not in non_deleted_envelopes
    assert envelope3 not in non_deleted_envelopes


def test_queryset_for_year(successful_envelope_factory, settings):
    """Test Envelope queryset for_year returns expected envelopes."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    with freeze_time(f"{str(date.today().year - 1)}-01-01"):
        envelope = successful_envelope_factory()
    with freeze_time(f"{str(date.today().year)}-01-01"):
        envelope2 = successful_envelope_factory()
    current_year_envelopes = Envelope.objects.for_year()
    previous_year_envelopes = Envelope.objects.for_year(int(date.today().year) - 1)

    assert envelope not in current_year_envelopes
    assert envelope in previous_year_envelopes
    assert envelope2 in current_year_envelopes
    assert envelope2 not in previous_year_envelopes


def test_queryset_processing_states(
    packaged_workbasket_factory,
    published_envelope_factory,
    successful_envelope_factory,
    settings,
):
    """Test Envelope queryset processing_states returns expected envelopes."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    packaged_workbasket = packaged_workbasket_factory()
    envelope = published_envelope_factory(packaged_workbasket=packaged_workbasket)

    unprocessed_result = Envelope.objects.unprocessed()
    assert envelope in unprocessed_result

    packaged_workbasket.begin_processing()
    packaged_workbasket.save()

    currently_processing_result = Envelope.objects.currently_processing()
    assert envelope in currently_processing_result

    packaged_workbasket.processing_failed()
    packaged_workbasket.save()

    failed_processing_result = Envelope.objects.failed_processing()
    assert envelope in failed_processing_result

    packaged_workbasket2 = packaged_workbasket_factory()
    envelope2 = successful_envelope_factory(
        packaged_workbasket=packaged_workbasket2,
    )

    success_processing_result = Envelope.objects.successfully_processed()
    assert envelope2 in success_processing_result


def test_delete_envelope(envelope_storage, published_envelope_factory, settings):
    """Test Envelope deleted_envelope() returns expected results."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = published_envelope_factory()

    with mock.patch(
        "publishing.storages.EnvelopeStorage.delete",
        wraps=mock.MagicMock(side_effect=envelope_storage.delete),
    ) as mock_delete:
        envelope.delete_envelope()
        mock_delete.assert_called_once()
    assert envelope.deleted is True


@freezegun.freeze_time("2024-01-01")
def test_next_envelope_id(successful_envelope_factory, settings):
    """Verify that envelope ID is made up of two digits of the year and a 4
    digit counter starting from 0001."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    successful_envelope_factory()
    assert Envelope.next_envelope_id() == f"{str(date.today().year)[2:]}0002"


def test_upload_envelope_handles_validate_envelope(packaged_workbasket_factory):
    """Mock Error repsonse from validate envelope and test it is raised."""

    packaged_workbasket = packaged_workbasket_factory()

    with mock.patch(
        "publishing.models.envelope.validate_envelope",
        side_effect=TaricDataAssertionError(
            "Missing records in XML: 4, while 6 expected",
        ),
    ) as mock_validate:
        envelope = factories.PublishedEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
        )
        mock_validate.assert_called_once()
        assert (
            envelope.validation_state
            == ValidationState.FAILED_TARIC_DATA_ASSERTION_ERROR
        )


@freezegun.freeze_time("2025-01-01")
def test_next_envelope_id_new_seed_envelope_id(
    settings,
    successful_envelope_factory,
):
    # publish an envelope
    successful_envelope_factory()
    # change seed_id within current year
    settings.HMRC_PACKAGING_SEED_ENVELOPE_ID = "250045"
    # resume automated publishing
    env = successful_envelope_factory()
    assert env.envelope_id == "250046"
