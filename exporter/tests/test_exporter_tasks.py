import os
from datetime import datetime
from unittest import mock

import pytest
from apiclient.exceptions import APIRequestError
from botocore.exceptions import ConnectionError
from lxml import etree

from common.tests.factories import ApprovedTransactionFactory
from common.tests.factories import FootnoteTypeFactory
from common.tests.factories import RegulationFactory
from common.tests.util import taric_xml_record_codes
from common.tests.util import validate_taric_xml_record_order
from exporter.tasks import upload_workbaskets
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


class SentinelError(Exception):
    # Special exception to signify test should exit.
    pass


def test_upload_workbaskets_uploads_queued_workbasket_to_s3(
    approved_transaction,
    hmrc_storage,
    s3,
    s3_bucket_names,
    s3_object_names,
    settings,
):
    """Exercise HMRCStorage and verify content is saved to bucket."""
    assert WorkBasket.objects.filter(status=WorkflowStatus.QUEUED).exists() == False

    now = datetime.now()
    expected_bucket = "hmrc"
    expected_key = f"tohmrc/staging/DIT{now:%y}0001.xml"

    settings.HMRC_STORAGE_BUCKET_NAME = expected_bucket

    RegulationFactory.create(
        transaction=approved_transaction,
        regulation_group__transaction=approved_transaction,
    )
    FootnoteTypeFactory.create(transaction=approved_transaction)

    with mock.patch(
        "exporter.storages.HMRCStorage.save",
        wraps=mock.MagicMock(side_effect=hmrc_storage.save),
    ) as mock_save:
        upload_workbaskets.apply()

        mock_save.assert_called_once()

    assert expected_bucket in s3_bucket_names()
    assert expected_key in s3_object_names(expected_bucket)

    s3_object = s3.get_object(Bucket=expected_bucket, Key=expected_key)
    filename = os.path.basename(expected_key)

    assert s3_object.get("ContentDisposition") == f"attachment; filename={filename}"

    envelope = s3_object["Body"].read()
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

    assert WorkBasket.objects.filter(status=WorkflowStatus.QUEUED).exists() == True


@mock.patch(
    "exporter.storages.HMRCStorage.save",
    side_effect=[
        ConnectionError(error={"endpoint_url": "http://example.com"}),
        SentinelError(),
    ],
)
def test_upload_workbaskets_retries(mock_save, settings):
    """Verify if HMRCStorage.save raises a boto.ConnectionError the task
    upload_workflow task retries based on
    settings.EXPORTER_UPLOAD_MAX_RETRIES."""
    settings.EXPORTER_DISABLE_NOTIFICATION = True
    # Notifications are disabled, as they are not being tested here.
    settings.EXPORTER_UPLOAD_MAX_RETRIES = 1

    with ApprovedTransactionFactory.create():
        RegulationFactory.create(),
        FootnoteTypeFactory.create()

    # On the first run, the test makes .save trigger ConnectionError which
    # should not be propagated to here, but should make the task retry.
    # On first retry, the SentinelError defined above is triggered,
    # and caught here.
    with pytest.raises(SentinelError):
        upload_workbaskets.apply().get()

    assert mock_save.call_count == 2


@mock.patch(
    "apiclient.client.APIClient.post",
    side_effect=[
        APIRequestError(message="", info="", status_code=500),
        SentinelError(),
    ],
)
def test_notify_hmrc_retries(mock_post, settings, hmrc_storage, responses):
    """Verify if HMRCStorage.save raises a boto.ConnectionError the task
    upload_workflow task retries based on
    settings.EXPORTER_UPLOAD_MAX_RETRIES."""
    responses.add(
        responses.POST,
        url="https://test-api.service.hmrc.gov.uk/oauth/token",
        json={
            "access_token": "access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token",
            "scope": "write:transfer-complete write:transfer-ready",
        },
    )

    settings.EXPORTER_DISABLE_NOTIFICATION = False
    # Notifications are disabled, as they are not being tested here.
    settings.EXPORTER_UPLOAD_MAX_RETRIES = 1

    with ApprovedTransactionFactory.create():
        RegulationFactory.create(),
        FootnoteTypeFactory.create()

    # On the first run, the test makes .save trigger APIRequestError which
    # causes the task to retry, raising SentinelError.

    with pytest.raises(SentinelError):
        upload_workbaskets.apply().get()

    assert mock_post.call_count == 2
