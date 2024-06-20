import re
from datetime import datetime
from unittest import mock

import pytest
from lxml import etree
from requests import Response

from common.tests import factories
from common.tests.util import taric_xml_record_codes
from publishing.models import CrownDependenciesPublishingTask
from publishing.models import PackagedWorkBasket
from publishing.models.state import ApiPublishingState
from publishing.tariff_api.interface import TariffAPIStubbed
from publishing.tasks import create_xml_envelope_file
from publishing.tasks import publish_to_api

pytestmark = pytest.mark.django_db


def test_create_and_upload_envelope(
    packaged_workbasket_factory,
    envelope_storage,
    s3_bucket_names,
    s3_object_names,
    s3,
):
    """Exercise EnvelopeStorage and verify content is saved to bucket."""

    expected_bucket = "hmrc-packaging"
    packaged_work_basket = packaged_workbasket_factory()

    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        create_xml_envelope_file.apply(
            (packaged_work_basket.pk, True),
        )
        mock_save.assert_called_once()

    assert expected_bucket in s3_bucket_names()

    envelope_name = f"DIT{datetime.now():%y}0001"
    object_key = next(
        name
        for name in s3_object_names(expected_bucket)
        if re.match(
            rf"^envelope/{envelope_name}__.*\.xml$",
            name,
        )
    )
    assert object_key is not None

    s3_object = s3.get_object(Bucket=expected_bucket, Key=object_key)
    envelope = s3_object["Body"].read()
    xml = etree.XML(envelope)

    # tuples of (record_code, subrecord_code).
    expected_codes = [
        ("100", "00"),  # FootnoteType
        ("100", "05"),  # FootnoteType description
        ("120", "00"),
        ("120", "05"),
        ("245", "00"),
    ]
    codes = taric_xml_record_codes(xml)
    assert codes == expected_codes


def test_create_and_upload_envelope_fails(
    queued_workbasket,
    packaged_workbasket_factory,
    envelope_storage,
):
    """Verify EnvelopeStorage is not created as there are validation errors due
    to the envelope containing no transactions."""

    packaged_work_basket = packaged_workbasket_factory(
        workbasket=queued_workbasket,
    )

    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        create_xml_envelope_file.apply(
            (packaged_work_basket.pk, True),
        )
        # assert not called as it didn't pass validate
        mock_save.assert_not_called()


def test_publish_to_api_successfully_published(successful_envelope_factory, settings):
    """Test when an envelope has been successfully published to the Tariff API
    that its state and published fields are updated accordingly."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    pwbs = PackagedWorkBasket.objects.get_unpublished_to_api()
    assert pwbs.count() == 1
    pwb = pwbs.last()

    assert not pwb.crown_dependencies_envelope

    publish_to_api()
    pwb.refresh_from_db()

    assert pwb.crown_dependencies_envelope
    assert (
        pwb.crown_dependencies_envelope.publishing_state
        == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    )
    assert pwb.crown_dependencies_envelope.published


def test_publish_to_api_failed_publishing(
    successful_envelope_factory,
    settings,
):
    """Test when an envelope fails publishing to Tariff API that its state and
    published fields are updated accordingly."""

    from publishing.tasks import CrownDependenciesException

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()
    pwb = PackagedWorkBasket.objects.get_unpublished_to_api().last()
    assert not pwb.envelope.published_to_tariffs_api

    response = Response()
    response.status_code = 400
    with mock.patch.object(
        TariffAPIStubbed,
        "post_envelope",
        return_value=response,
    ):
        with pytest.raises(CrownDependenciesException):
            publish_to_api()

    pwb.refresh_from_db()

    assert pwb.crown_dependencies_envelope
    assert (
        pwb.crown_dependencies_envelope.publishing_state
        == ApiPublishingState.FAILED_PUBLISHING
    )
    assert not pwb.crown_dependencies_envelope.published
    assert not pwb.envelope.published_to_tariffs_api


def test_publish_to_api_failed_publishing_to_successfully_published(
    successful_envelope_factory,
    settings,
):
    """Test that an envelope in state FAILED_PUBLISHING can be published to the
    Tariff API."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    successful_envelope_factory()
    pwb = PackagedWorkBasket.objects.get_unpublished_to_api().last()
    crown_dependencies_envelope = factories.CrownDependenciesEnvelopeFactory(
        packaged_work_basket=pwb,
    )

    crown_dependencies_envelope.publishing_failed()
    assert (
        crown_dependencies_envelope.publishing_state
        == ApiPublishingState.FAILED_PUBLISHING
    )

    publish_to_api()
    crown_dependencies_envelope.refresh_from_db()

    assert (
        crown_dependencies_envelope.publishing_state
        == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    )
    assert crown_dependencies_envelope.published


def test_publish_to_api_currently_publishing_to_successfully_published(
    successful_envelope_factory,
    settings,
):
    """Test that an envelope in state CURRENTLY_PUBLISHING can be published to
    the Tariff API."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    successful_envelope_factory()
    pwb = PackagedWorkBasket.objects.get_unpublished_to_api().last()
    crown_dependencies_envelope = factories.CrownDependenciesEnvelopeFactory(
        packaged_work_basket=pwb,
    )

    publish_to_api()
    crown_dependencies_envelope.refresh_from_db()

    assert (
        crown_dependencies_envelope.publishing_state
        == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    )
    assert crown_dependencies_envelope.published


def test_publish_to_api_has_been_published(
    successful_envelope_factory,
    settings,
):
    """Test that an envelope that has already been published but is stuck in
    state CURRENTLY_PUBLISHING can be updated accordingly."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    successful_envelope_factory()
    pwb = PackagedWorkBasket.objects.get_unpublished_to_api().last()
    crown_dependencies_envelope = factories.CrownDependenciesEnvelopeFactory(
        packaged_work_basket=pwb,
    )

    response = Response()
    response.status_code = 200
    with mock.patch.object(
        TariffAPIStubbed,
        "get_envelope",
        return_value=response,
    ):
        publish_to_api()
    crown_dependencies_envelope.refresh_from_db()

    assert (
        crown_dependencies_envelope.publishing_state
        == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    )
    assert crown_dependencies_envelope.published


def test_publish_to_api_published_in_sequence(successful_envelope_factory, settings):
    """Test that envelopes are published in sequence to the Tariff API."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()
    successful_envelope_factory()
    successful_envelope_factory()

    pwbs = list(PackagedWorkBasket.objects.get_unpublished_to_api())
    assert len(pwbs) == 3

    publish_to_api()

    for pwb in pwbs:
        pwb.refresh_from_db()

    assert (
        pwbs[2].crown_dependencies_envelope.published
        > pwbs[1].crown_dependencies_envelope.published
        > pwbs[0].crown_dependencies_envelope.published
    )


def test_publish_to_api_creates_crown_dependencies_publishing_task(
    successful_envelope_factory,
    settings,
):
    """Test that a CrownDependenciesPublishingTask instance is created."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    publishing_tasks = CrownDependenciesPublishingTask.objects.all()
    assert publishing_tasks.count() == 0

    publish_to_api()

    assert publishing_tasks.count() == 1


def test_publish_to_api_paused_publishing(
    successful_envelope_factory,
    settings,
    pause_publishing,
):
    """Test that no envelopes can be published when publishing is paused."""

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 1

    publish_to_api()

    assert PackagedWorkBasket.objects.get_unpublished_to_api().count() == 1
