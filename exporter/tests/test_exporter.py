from unittest import mock

from lxml import etree

import pytest
from django.core.management import call_command

from common.tests.factories import RegulationFactory, FootnoteTypeFactory
from common.tests.util import validate_taric_xml_record_order, taric_xml_record_codes

pytestmark = pytest.mark.django_db


def test_upload_command_uploads_approved_workbasket_to_s3(
    approved_workbasket, hmrc_storage, s3
):
    """
    Exercise HMRCStorage and verify expected content is saved to bucket.
    """
    expected_bucket_name = "test-hmrc"

    # Expected items.
    RegulationFactory.create(workbasket=approved_workbasket)
    FootnoteTypeFactory.create(workbasket=approved_workbasket)
    # Un
    RegulationFactory.create(workbasket=workbasket)

    with mock.patch(
        "exporter.storages.HMRCStorage.save",
        wraps=mock.MagicMock(side_effect=hmrc_storage.save),
    ) as mock_save:
        call_command("upload_workbaskets")

        mock_save.assert_called_once()
        # Don't check what content was passed in here, ask moto what was saved later.

    bucket_names = [bucket_info["Name"] for bucket_info in s3.list_buckets()["Buckets"]]
    assert (
        expected_bucket_name in bucket_names
    ), "Bucket named in HMRC_BUCKET_NAME setting was not created."

    object_names = [
        contents["Key"]
        for contents in s3.list_objects(Bucket=expected_bucket_name)["Contents"]
    ]
    assert (
        "test-hmrc/tohmrc/staging/DIT200001.xml" in object_names
    ), "File was not uploaded with expected name."

    # Attempt to fetch data from Motos fake s3
    object = s3.get_object(
        Bucket="test-hmrc", Key="test-hmrc/tohmrc/staging/DIT200001.xml"
    )
    envelope = object["Body"].read()
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


def test_dump_command_outputs_approved_workbasket_to_stdout(
    approved_workbasket, settings, capsys
):
    """
    Exercise HMRCStorage and verify content is saved to bucket.
    """
    settings.HMRC_BUCKET_NAME = "test-hmrc-bucket"
    with capsys.disabled():
        RegulationFactory.create(workbasket=approved_workbasket)
        # RegulationFactory also creates a Group
        FootnoteTypeFactory.create(workbasket=approved_workbasket)

    call_command("dump_workbaskets")

    envelope, _ = capsys.readouterr()
    with capsys.disabled():
        xml = etree.XML(envelope.encode("utf-8"))

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
