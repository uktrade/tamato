# import freezegun
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import pytest
from freezegun import freeze_time

from common.tests import factories
from publishing.models import ApiPublishingState
from publishing.models import PackagedWorkBasket
from publishing.models.tap_api_envelope import ApiEnvelopeInvalidWorkBasketStatus
from publishing.models.tap_api_envelope import ApiEnvelopeUnexpectedEnvelopeSequence

pytestmark = pytest.mark.django_db


def test_create_tap_api_envelope(
    successful_envelope_factory,
    settings,
):
    """Test TAP api Envelope instance is created on successful envelope
    processing."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    with freeze_time("2022-01-01"):
        envelope = successful_envelope_factory()

    packaged_work_basket = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )
    assert packaged_work_basket.tap_api_envelope
    assert (
        packaged_work_basket.tap_api_envelope.publishing_state
        == ApiPublishingState.AWAITING_PUBLISHING
    )

    # Creates successfully on new year
    with freeze_time("2023-01-01"):
        envelope2 = successful_envelope_factory()

    packaged_work_basket = PackagedWorkBasket.objects.get(
        envelope=envelope2,
    )
    assert (
        packaged_work_basket.tap_api_envelope.publishing_state
        == ApiPublishingState.AWAITING_PUBLISHING
    )


def test_create_tap_api_envelope_invalid_status(packaged_workbasket_factory):
    """Test that create tap envelope will not create for incorrect status."""
    with pytest.raises(ApiEnvelopeInvalidWorkBasketStatus):
        factories.TapApiEnvelopeFactory(
            packaged_work_basket=packaged_workbasket_factory(),
        )


def test_create_tap_api_envelope_invalid_envelope_sequence(
    successful_envelope_factory,
    settings,
):
    """Test that create tap envelope will not create out of sequence."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    with freeze_time("2022-01-01"):
        envelope = successful_envelope_factory()
    packaged_workbasket = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )

    with pytest.raises(ApiEnvelopeUnexpectedEnvelopeSequence):
        factories.TapApiEnvelopeFactory(packaged_work_basket=packaged_workbasket)

    # check out of sequence still works over different years
    with freeze_time("2023-01-01"):
        successful_envelope_factory()

    with pytest.raises(ApiEnvelopeUnexpectedEnvelopeSequence):
        factories.TapApiEnvelopeFactory(packaged_work_basket=packaged_workbasket)


def test_invalid_envelope_sequence_published_to_tariffs_api(envelope_storage, settings):
    """
    Test that create tap envelope will not create out of sequence.

    When the previous envelope has field published_to_tariffs_api set
    """
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    wb = factories.PublishedWorkBasketFactory()
    with factories.ApprovedTransactionFactory.create(workbasket=wb):
        factories.FootnoteTypeFactory()
        factories.AdditionalCodeFactory()
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        pwb = factories.SuccessPackagedWorkBasketFactory(
            workbasket=wb,
        )
    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        envelope = factories.APIPublishedEnvelope(
            packaged_work_basket=pwb,
        )
    pwb.envelope = envelope
    pwb.save()

    with pytest.raises(ApiEnvelopeUnexpectedEnvelopeSequence):
        factories.TapApiEnvelopeFactory(packaged_work_basket=pwb)
