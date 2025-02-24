from datetime import datetime
from io import StringIO

import freezegun
import pytest
from django.core.management import call_command

from publishing import models as publishing_models
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
    call_command("publish_to_api", stdout=out)
    output = out.getvalue()

    for packaged_work_basket in packaged_work_baskets:
        assert f"envelope_id={packaged_work_basket.envelope.envelope_id}" in output


def test_publish_to_api_lists_no_envelopes(
    settings,
):
    """Test that publish_to_api lists no envelopes when none exist."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    out = StringIO()
    call_command("publish_to_api", stdout=out)
    output = out.getvalue()

    assert not output


def test_publish_to_api_exits_no_unpublished_envelopes():
    """Test that publish_to_api exists when there are no unpublished
    envelopes."""
    assert CrownDependenciesEnvelope.objects.unpublished().count() == 0

    with pytest.raises(SystemExit):
        call_command("publish_to_api", "--publish-async")


def test_publish_to_api_publishes_envelopes(successful_envelope_factory, settings):
    """Test that publish_to_api triggers the task to upload unpublished
    envelopes to the Tariff API."""
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 1

    call_command("publish_to_api", "--publish-async")

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 0


@freezegun.freeze_time("2025-01-01")
def test_next_expected_to_api_first_envelope_of_new_year(
    successful_envelope_factory,
):
    """Test that publish_to_api returns the correct ID for the first envelope of
    the new year, if the last envelope of the previous year was successful."""
    # settings.HMRC_PACKAGING_SEED_ENVELOPE_ID = '230044'
    # Publish some envelopes in the previous year
    with freezegun.freeze_time("2024-12-31"):
        # successful_envelope_factory creates successfully processed envelope,
        # WorkBasket remains in QUEUED state
        successful_envelope_factory(
            published_to_tariffs_api="2024-12-28",
        )
        successful_envelope_factory(
            published_to_tariffs_api="2024-12-29",
        )
        last_env = successful_envelope_factory(
            published_to_tariffs_api="2024-12-31",
        )
        assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 0

    # NOTE: envelope.id and envelope_id ARE NOT THE SAME THING
    # NOTE: packaged_workbasket_factory does not have an envelope!

    successful_envelope_factory()
    current_year = str(datetime.now().year)[-2:]
    last_env_last_year = publishing_models.Envelope.objects.last_envelope_for_year(
        year=int(current_year) - 1,
    )
    pwbs = PackagedWorkBasket.objects.all()
    unpublished = pwbs.get_unpublished_to_api()
    assert last_env_last_year == last_env
    assert pwbs.last_published_envelope_id() == last_env.envelope_id
    assert unpublished[0].next_expected_to_api()


# def test_next_expected_to_api_first_envelope_of_new_year_last_envelope_failed
# have the last envelope of the previous year in failed state.
# set up:
# last envelope fails
# penultimate envelope passes

# assert next_envelope_id has correct id of YYXXXX

# def test_next_expected_to_api_with_new_seed_envelope_id
# set HMRC_PACKAGING_SEED_ENVELOPE_ID to be in the current year
# set up:
# a successfully processed envelope
# updated settings.HMRC_PACKAGING_SEED_ENVELOPE_ID
# package and process new_envelope
# assert the

# EnvelopeFactory.create(envelope_id="239999").envelope_id == "239999"
