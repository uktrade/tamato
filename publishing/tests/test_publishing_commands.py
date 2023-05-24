from io import StringIO

import pytest
from django.core.management import call_command

from common.tests import factories
from publishing.models import PackagedWorkBasket
from publishing.models import TAPApiEnvelope

pytestmark = pytest.mark.django_db


def test_publish_to_api_lists_unpublished_envelopes(
    successful_envelope_factory,
    settings,
):
    """Test that publish_to_api lists unpublished envelopes."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()
    successful_envelope_factory()
    envelopes = TAPApiEnvelope.objects.unpublished()

    out = StringIO()
    call_command("publish_to_api", "--list", stdout=out)
    output = out.getvalue()

    for envelope in envelopes:
        assert str(envelope) in output


def test_publish_to_api_exits_no_unpublished_envelopes():
    """Test that publish_to_api exists when there are no unpublished
    envelopes."""
    assert TAPApiEnvelope.objects.unpublished().count() == 0

    with pytest.raises(SystemExit):
        call_command("publish_to_api")


def test_publish_to_api_publishes_envelopes(successful_envelope_factory, settings):
    """Test that publish_to_api triggers the task to upload unpublished
    envelopes to the Tariff API."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    assert TAPApiEnvelope.objects.unpublished().count() == 1

    call_command("publish_to_api")

    assert TAPApiEnvelope.objects.unpublished().count() == 0


def test_create_api_envelope_lists_packaged_workbaskets():
    """Test that create_api_envelope lists successfully-processed, packaged
    workbaskets that do not have a published envelope and API envelope."""

    packaged_workbaskets = factories.SuccessPackagedWorkBasketFactory.create_batch(3)

    out = StringIO()
    call_command("create_api_envelope", "--list", stdout=out)
    output = out.getvalue()

    for pwb in packaged_workbaskets:
        assert str(pwb) in output


def test_create_api_envelope_exits_no_packaged_workbaskets():
    """Test that create_api_envelope exits when there are no packaged
    workbaskets for which to create API envelopes."""
    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 0

    with pytest.raises(SystemExit):
        call_command("create_api_envelope")


def test_create_api_envelope_creates_specified_amount(
    successful_packaged_workbasket_factory,
    published_envelope_factory,
):
    """Test that create_api_envelope allows specifying the number of API
    envelopes to create for available packaged workbaskets."""

    pwb = successful_packaged_workbasket_factory()
    pwb2 = successful_packaged_workbasket_factory()
    published_envelope_factory(packaged_workbasket=pwb)
    published_envelope_factory(packaged_workbasket=pwb2)

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 2
    assert TAPApiEnvelope.objects.count() == 0

    call_command("create_api_envelope", "--number", "1")

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 1
    assert TAPApiEnvelope.objects.count() == 1


def test_create_api_envelope_creates_all(
    successful_packaged_workbasket_factory,
    published_envelope_factory,
):
    """Test that create_api_envelope creates API envelopes for all available
    packaged workbaskets."""

    pwb = successful_packaged_workbasket_factory()
    pwb2 = successful_packaged_workbasket_factory()
    published_envelope_factory(packaged_workbasket=pwb)
    published_envelope_factory(packaged_workbasket=pwb2)

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 2
    assert TAPApiEnvelope.objects.count() == 0

    call_command("create_api_envelope")

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 0
    assert TAPApiEnvelope.objects.count() == 2
