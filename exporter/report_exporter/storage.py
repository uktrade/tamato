import logging
from os import path

from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

from django.conf import settings


class ReportsExportS3StorageBase(S3Boto3Storage):
    """Storage base class used for remotely storing Quotas Export CSV file to an
    AWS S3-like backing store (AWS S3, Minio, etc.)."""

    export_folder = "."

    def generate_filename(self, filename: str) -> str:
        pass

        filename = path.join(
            self.export_folder,
            filename,
        )
        return super().generate_filename(filename)


class QuotasExportS3StorageBase(S3Boto3Storage):
    export_folder = settings.QUOTAS_EXPORT_DESTINATION_FOLDER

    def get_default_settings(self):
        quotas_s3_settings = dict(
            super().get_default_settings(),
            bucket_name=settings.QUOTAS_EXPORT_STORAGE_BUCKET_NAME,
            access_key=settings.QUOTAS_EXPORT_S3_ACCESS_KEY_ID,
            secret_key=settings.QUOTAS_EXPORT_S3_SECRET_ACCESS_KEY,
            region_name=settings.QUOTAS_EXPORT_S3_REGION_NAME,
            endpoint_url=settings.S3_ENDPOINT_URL,
            default_acl="private",
        )
        print(quotas_s3_settings)
        return quotas_s3_settings
