import re
from datetime import datetime
from unittest import mock

import pytest
from lxml import etree

from common.tests import factories
from common.tests.util import taric_xml_record_codes
from common.tests.util import validate_taric_xml_record_order
from publishing.tasks import create_xml_envelope_file

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
