import pytest

from common.tests import factories
from publishing.models import ApiPublishingState
from publishing.models import PackagedWorkBasket
from publishing.models.tap_api_envelope import ApiEnvelopeAlreadyExists
from publishing.models.tap_api_envelope import ApiEnvelopeInvalidWorkBasketStatus

pytestmark = pytest.mark.django_db


def test_create_tap_api_envelope(
    successful_envelope_factory,
    settings,
):
    """Test TAP api Envelope instance is created on successful envelope
    processing."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    #    factories.TapApiEnvelopeFactory()
    successful_envelope_factory()

    packaged_work_basket = PackagedWorkBasket.objects.completed_processing().first()
    assert packaged_work_basket.tap_api_envelope
    assert (
        packaged_work_basket.tap_api_envelope.publishing_state
        == ApiPublishingState.AWAITING_PUBLISHING
    )


def test_create_tap_api_envelope_invalid_status(packaged_workbasket_factory):
    """"""
    with pytest.raises(ApiEnvelopeInvalidWorkBasketStatus):
        factories.TapApiEnvelopeFactory(
            packaged_work_basket=packaged_workbasket_factory(),
        )


def test_create_tap_api_envelope_already_exists(successful_envelope_factory, settings):
    """"""
    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    envelope = successful_envelope_factory()
    packaged_workbasket = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )

    with pytest.raises(ApiEnvelopeAlreadyExists):
        factories.TapApiEnvelopeFactory(packaged_work_basket=packaged_workbasket)


# def test_create_tap_api_envelope_invalid_envelope_sequence(published_envelope_factory):
#     """Test that create tap envelope will not create out of sequence."""
#     # create 2 published envelopes, trigger envelope with unexpected one
#     with pytest.raises(ApiEnvelopeUnexpectedEnvelopeSequence):
#         factories.TapApiEnvelopeFactory(packaged_work_basket=packaged_workbasket)
