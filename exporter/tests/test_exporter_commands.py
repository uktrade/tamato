from unittest import mock

import pytest
from django.core.management import call_command
from lxml import etree

from common.tests.factories import FootnoteTypeFactory
from common.tests.factories import RegulationFactory
from common.tests.util import taric_xml_record_codes
from common.tests.util import validate_taric_xml_record_order

pytestmark = pytest.mark.django_db


@pytest.mark.skip()
def test_upload_command_uploads_approved_workbasket_to_s3(
    approved_transaction,
    hmrc_storage,
    s3,
    s3_object_exists,
    settings,
):
    """Exercise HMRCStorage and verify content is saved to bucket."""
    expected_bucket = "test-hmrc"
    expected_key = "tohmrc/staging/DIT200001.xml"

    settings.HMRC_STORAGE_BUCKET_NAME = expected_bucket

    RegulationFactory.create(transaction=approved_transaction)
    FootnoteTypeFactory.create(transaction=approved_transaction)

    with mock.patch(
        "exporter.storages.HMRCStorage.save",
        wraps=mock.MagicMock(side_effect=hmrc_storage.save),
    ) as mock_save:
        call_command("upload_transactions")

        mock_save.assert_called_once()

    assert s3_object_exists(
        expected_bucket,
        expected_key,
    ), f"File was not uploaded with expected name, uploaded: Bucket: {expected_bucket} Key: {expected_key}"

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


@pytest.mark.skip(reason="broken test - TODO")
def test_dump_command_outputs_approved_workbasket(approved_transaction, capsys):
    """Exercise HMRCStorage and verify content is saved to bucket."""
    with capsys.disabled():
        RegulationFactory.create(transaction=approved_transaction)
        # RegulationFactory also creates a Group
        FootnoteTypeFactory.create(transaction=approved_transaction)

    call_command("dump_transactions")

    envelope_bytes, _ = capsys.readouterr()
    with capsys.disabled():
        xml = etree.XML(envelope_bytes.encode("utf-8"))

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
