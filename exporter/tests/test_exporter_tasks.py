from exporter.tasks import upload_workbaskets
from unittest import mock

from lxml import etree

import pytest
from django.core.management import call_command

from common.tests.factories import RegulationFactory, FootnoteTypeFactory
from common.tests.util import validate_taric_xml_record_order, taric_xml_record_codes

pytestmark = pytest.mark.django_db


def test_upload_task_uploads_approved_workbasket_to_s3(
    approved_workbasket,
    hmrc_storage,
    s3,
    s3_object_exists,
):
    """
    Exercise HMRCStorage and verify content is saved to bucket.
    """
    expected_bucket = "test-hmrc"
    expected_key = "test-hmrc/tohmrc/staging/DIT200001.xml"

    RegulationFactory.create(workbasket=approved_workbasket)
    FootnoteTypeFactory.create(workbasket=approved_workbasket)

    with mock.patch(
        "exporter.storages.HMRCStorage.save",
        wraps=mock.MagicMock(side_effect=hmrc_storage.save),
    ) as mock_save:
        upload_workbaskets.apply()

        mock_save.assert_called_once()

    assert s3_object_exists(
        expected_bucket, expected_key
    ), "File was not uploaded with expected name."

    envelope = s3.get_object(Bucket=expected_bucket, Key=expected_key)["Body"].read()
    xml = etree.XML(envelope)

    validate_taric_xml_record_order(xml)

    # tuples of (record_code, subrecord_code).
    expected_codes = [
        ("100", "00"),  # FootnoteType
        ("100", "05"),  # FootnoteType description
        ("150", "00"),  # Group
        ("150", "05"),  # Group description
        ("285", "00"),  # Regulation
    ]

    codes = taric_xml_record_codes(xml)

    assert codes == expected_codes
