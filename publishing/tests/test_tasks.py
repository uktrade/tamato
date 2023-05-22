import re
from datetime import datetime
from unittest import mock

import pytest
from lxml import etree
from requests import Response

from common.tests import factories
from common.tests.util import taric_xml_record_codes
from common.tests.util import validate_taric_xml_record_order
from publishing.models import TAPApiEnvelope
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
            f"^envelope/{envelope_name}__.*\.xml$",
            name,
        )
    )
    assert object_key is not None

    s3_object = s3.get_object(Bucket=expected_bucket, Key=object_key)
    envelope = s3_object["Body"].read()
    xml = etree.XML(envelope)

    validate_taric_xml_record_order(xml)

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
    """Verify EnvelopeStorage is not called as there are validation errors."""

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


def test_create_and_upload_envelope_fails_record_order(
    queued_workbasket,
    packaged_workbasket_factory,
    envelope_storage,
):
    """Verify EnvelopeStorage is not called as there are validation errors."""

    packaged_work_basket = packaged_workbasket_factory(
        workbasket=queued_workbasket,
    )

    approved_transaction = queued_workbasket.transactions.approved().last()

    # out of order
    factories.FootnoteTypeFactory(transaction=approved_transaction)
    factories.FootnoteDescriptionFactory(transaction=approved_transaction)
    factories.FootnoteFactory(transaction=approved_transaction)

    with mock.patch(
        "publishing.storages.EnvelopeStorage.save",
        wraps=mock.MagicMock(side_effect=envelope_storage.save),
    ) as mock_save:
        create_xml_envelope_file.apply(
            (packaged_work_basket.pk, True),
        )
        # assert not called as it didn't pass validate
        mock_save.assert_not_called()


def test_publish_to_api_successfully_published(successful_envelope_factory):
    """Test when an envelope has been successfully published to the Tariff API
    that its state and published fields are updated accordingly."""

    successful_envelope_factory()

    envelope = TAPApiEnvelope.objects.all()
    assert envelope.count() == 1
    pwb = envelope[0].packagedworkbaskets.last()

    assert envelope[0].publishing_state == ApiPublishingState.AWAITING_PUBLISHING
    assert not envelope[0].staging_published
    assert not envelope[0].production_published
    assert not pwb.envelope.published_to_tariffs_api

    publish_to_api()
    pwb.envelope.refresh_from_db()
    envelope[0].refresh_from_db()

    assert envelope[0].publishing_state == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    assert envelope[0].staging_published
    assert envelope[0].production_published
    assert pwb.envelope.published_to_tariffs_api


def test_publish_to_api_failed_publishing_staging(
    successful_envelope_factory,
):
    """Test when an envelope fails publishing to Tariff API staging that its
    state and published fields are updated accordingly."""

    successful_envelope_factory()

    envelope = TAPApiEnvelope.objects.all()
    assert envelope.count() == 1
    pwb = envelope[0].packagedworkbaskets.last()

    assert envelope[0].publishing_state == ApiPublishingState.AWAITING_PUBLISHING
    assert not envelope[0].staging_published
    assert not envelope[0].production_published
    assert not pwb.envelope.published_to_tariffs_api

    response = Response()
    response.status_code = 400
    with mock.patch.object(
        TariffAPIStubbed,
        "post_envelope_staging",
        return_value=response,
    ):
        publish_to_api()

    pwb.envelope.refresh_from_db()
    envelope[0].refresh_from_db()

    assert envelope[0].publishing_state == ApiPublishingState.FAILED_PUBLISHING_STAGING
    assert not envelope[0].staging_published
    assert not envelope[0].production_published
    assert not pwb.envelope.published_to_tariffs_api


def test_publish_to_api_failed_publishing_production(
    successful_envelope_factory,
):
    """Test when an envelope fails publishing to Tariff API production that its
    state and published fields are updated accordingly."""

    successful_envelope_factory()

    envelope = TAPApiEnvelope.objects.all()
    assert envelope.count() == 1
    pwb = envelope[0].packagedworkbaskets.last()

    assert envelope[0].publishing_state == ApiPublishingState.AWAITING_PUBLISHING
    assert not envelope[0].staging_published
    assert not envelope[0].production_published
    assert not pwb.envelope.published_to_tariffs_api

    response = Response()
    response.status_code = 400
    with mock.patch.object(
        TariffAPIStubbed,
        "post_envelope_production",
        return_value=response,
    ):
        publish_to_api()

    pwb.envelope.refresh_from_db()
    envelope[0].refresh_from_db()

    assert (
        envelope[0].publishing_state == ApiPublishingState.FAILED_PUBLISHING_PRODUCTION
    )
    assert envelope[0].staging_published
    assert not envelope[0].production_published
    assert not pwb.envelope.published_to_tariffs_api


def test_publish_to_api_failed_publishing_staging_to_successfully_published(
    successful_envelope_factory,
):
    """Test that an envelope with state FAILED_PUBLISHING_STAGING can be
    published to the Tariff API."""

    successful_envelope_factory()

    envelope = TAPApiEnvelope.objects.all()
    assert envelope.count() == 1
    pwb = envelope[0].packagedworkbaskets.last()

    envelope[0].begin_publishing()
    envelope[0].publishing_staging_failed()
    assert envelope[0].publishing_state == ApiPublishingState.FAILED_PUBLISHING_STAGING

    publish_to_api()
    pwb.envelope.refresh_from_db()
    envelope[0].refresh_from_db()

    assert envelope[0].publishing_state == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    assert envelope[0].staging_published
    assert envelope[0].production_published
    assert pwb.envelope.published_to_tariffs_api


def test_publish_to_api_failed_publishing_production_to_successfully_published(
    successful_envelope_factory,
):
    """Test that an envelope with state FAILED_PUBLISHING_PRODUCTION can be
    published to the Tariff API."""

    successful_envelope_factory()

    envelope = TAPApiEnvelope.objects.all()
    assert envelope.count() == 1
    pwb = envelope[0].packagedworkbaskets.last()

    envelope[0].begin_publishing()
    envelope[0].publishing_production_failed()
    assert (
        envelope[0].publishing_state == ApiPublishingState.FAILED_PUBLISHING_PRODUCTION
    )

    publish_to_api()
    pwb.envelope.refresh_from_db()
    envelope[0].refresh_from_db()

    assert envelope[0].publishing_state == ApiPublishingState.SUCCESSFULLY_PUBLISHED
    assert envelope[0].production_published
    assert pwb.envelope.published_to_tariffs_api


def test_publish_to_api_published_in_sequence(successful_envelope_factory):
    """Test that envelopes are published in sequence to the Tariff API."""

    successful_envelope_factory()
    successful_envelope_factory()
    successful_envelope_factory()

    envelopes = TAPApiEnvelope.objects.order_by("pk")
    assert envelopes.count() == 3

    publish_to_api()

    for envelope in envelopes:
        envelope.refresh_from_db()

    assert (
        envelopes[2].staging_published
        > envelopes[1].staging_published
        > envelopes[0].staging_published
    )
    assert (
        envelopes[2].production_published
        > envelopes[1].production_published
        > envelopes[0].production_published
    )
