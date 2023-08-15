import pytest

from notifications.models import Notification
from publishing.models import ApiPublishingState
from publishing.models import CrownDependenciesEnvelope

pytestmark = pytest.mark.django_db


def test_create_crown_dependencies_envelope(
    packaged_workbasket_factory,
    crown_dependencies_envelope_factory,
    settings,
):
    """Test TAP api Envelope instance is created on successful envelope
    processing."""

    # unit testing envelope not notification integration
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    packaged_work_basket = packaged_workbasket_factory()

    crown_dependencies_envelope_factory(
        packaged_workbasket=packaged_work_basket,
    )

    packaged_work_basket.refresh_from_db()
    assert (
        packaged_work_basket.crown_dependencies_envelope.publishing_state
        == ApiPublishingState.CURRENTLY_PUBLISHING
    )


def test_notify_processing_succeeded(
    mocked_publishing_models_send_emails_delay,
    packaged_workbasket_factory,
    successful_envelope_factory,
    crown_dependencies_envelope_factory,
):
    pwb = packaged_workbasket_factory()

    crown_dependencies_envelope_factory(packaged_workbasket=pwb)

    cd_envelope = CrownDependenciesEnvelope.objects.all().first()

    cd_envelope.notify_publishing_success()

    personalisation = {
        "envelope_id": pwb.envelope.envelope_id,
    }
    notification = Notification.objects.last()
    mocked_publishing_models_send_emails_delay.assert_called_with(
        notification_id=notification.id,
    )


def test_notify_processing_failed(
    mocked_publishing_models_send_emails_delay,
    packaged_workbasket_factory,
    successful_envelope_factory,
    crown_dependencies_envelope_factory,
):
    pwb = packaged_workbasket_factory()

    crown_dependencies_envelope_factory(packaged_workbasket=pwb)

    cd_envelope = CrownDependenciesEnvelope.objects.all().first()

    cd_envelope.notify_publishing_failed()

    personalisation = {
        "envelope_id": pwb.envelope.envelope_id,
    }

    notification = Notification.objects.last()
    mocked_publishing_models_send_emails_delay.assert_called_with(
        notification_id=notification.id,
    )
