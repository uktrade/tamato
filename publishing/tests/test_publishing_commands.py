from io import StringIO

import pytest
from django.core.management import call_command

from publishing.models import CrownDependenciesEnvelope
from publishing.models import PackagedWorkBasket

pytestmark = pytest.mark.django_db


def test_publish_to_api_lists_unpublished_envelopes(
    successful_envelope_factory,
    settings,
):
    """Test that publish_to_api lists unpublished envelopes."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()
    successful_envelope_factory()
    packaged_work_baskets = PackagedWorkBasket.objects.get_unpublished_to_api()

    out = StringIO()
    call_command("publish_to_api", "--list", stdout=out)
    output = out.getvalue()

    for packaged_work_basket in packaged_work_baskets:
        assert str(packaged_work_basket.envelope) in output


def test_publish_to_api_lists_no_envelopes(
    settings,
):
    """Test that publish_to_api lists no envelopes when none exist."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    out = StringIO()
    call_command("publish_to_api", "--list", stdout=out)
    output = out.getvalue()

    assert not output


def test_publish_to_api_exits_no_unpublished_envelopes():
    """Test that publish_to_api exists when there are no unpublished
    envelopes."""
    assert CrownDependenciesEnvelope.objects.unpublished().count() == 0

    with pytest.raises(SystemExit):
        call_command("publish_to_api")


def test_publish_to_api_publishes_envelopes(successful_envelope_factory, settings):
    """Test that publish_to_api triggers the task to upload unpublished
    envelopes to the Tariff API."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 1

    call_command("publish_to_api")

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 0
