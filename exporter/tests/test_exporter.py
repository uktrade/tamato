import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_upload_command_uploads_approved_workbasket_to_s3(
    approved_workbasket, hmrc_storage, s3, settings
):
    """
    Exercise HMRCStorage and verify content is saved to bucket.
    """
    settings.HMRC_BUCKET_NAME = "test-hmrc-bucket"

    call_command("upload_workbaskets")

    bucket_names = [bucket_info["Name"] for bucket_info in s3.list_buckets()["Buckets"]]
    assert (
        "test-hmrc-bucket" in bucket_names
    ), "Bucket named in HMRC_BUCKET_NAME setting created."

    object_names = [
        contents["Key"]
        for contents in s3.list_objects(Bucket="test-hmrc-bucket")["Contents"]
    ]
    assert "test-hmrc-bucket/tohmrc/staging/DIT200001.xml" in object_names

    # TODO - assert expected TrackedModels were saved.


def test_dump_command_outputs_approved_workbasket(
    approved_workbasket, hmrc_storage, s3, settings
):
    """
    Exercise HMRCStorage and verify content is saved to bucket.
    """
    settings.HMRC_BUCKET_NAME = "test-hmrc-bucket"

    from exporter.management.commands import upload_workbaskets

    call_command("dump_workbaskets")

    bucket_names = [bucket_info["Name"] for bucket_info in s3.list_buckets()["Buckets"]]
    assert (
        "test-hmrc-bucket" in bucket_names
    ), "Bucket named in HMRC_BUCKET_NAME setting created."

    object_names = [
        contents["Key"]
        for contents in s3.list_objects(Bucket="test-hmrc-bucket")["Contents"]
    ]
    assert "test-hmrc-bucket/tohmrc/staging/DIT200001.xml" in object_names

    # TODO - assert expected TrackedModels were output.
