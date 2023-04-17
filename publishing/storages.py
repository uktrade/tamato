from os import path

from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage


class EnvelopeStorage(S3Boto3Storage):
    def get_default_settings(self):
        # Importing settings here makes it possible for tests to override_settings
        from django.conf import settings

        return dict(
            super().get_default_settings(),
            bucket_name=settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME,
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION_NAME,
            default_acl="private",
        )

    def generate_filename(self, filename: str) -> str:
        from django.conf import settings

        # Suffix the filename with a time stamp so that envelopes are not
        # overwritten on S3 instances with versioning disabled.
        name, extension = path.splitext(filename)
        date_time = timezone.now().isoformat()
        filename = f"{name}__{date_time}{extension}"
        filepath = path.join(settings.HMRC_ENVELOPE_STORAGE_DIRECTORY, filename)

        return super().generate_filename(filepath)

    def get_object_parameters(self, name):
        self.object_parameters.update(
            {"ContentDisposition": f"attachment; filename={path.basename(name)}"},
        )
        return super().get_object_parameters(name)


class LoadingReportStorage(S3Boto3Storage):
    def get_default_settings(self):
        # Importing settings here makes it possible for tests to override_settings
        from django.conf import settings

        return dict(
            super().get_default_settings(),
            bucket_name=settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME,
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION_NAME,
            default_acl="private",
        )

    def generate_filename(self, filename: str) -> str:
        from django.conf import settings

        # Use a time-based filename prefix to avoid overwriting stored files
        # that have the same name and to make sorting by date / time easier.
        filename = path.join(
            settings.HMRC_LOADING_REPORTS_STORAGE_DIRECTORY,
            timezone.now().isoformat() + "__" + filename,
        )
        return super().generate_filename(filename)

    def get_object_parameters(self, name):
        self.object_parameters.update(
            {"ContentDisposition": f"attachment; filename={path.basename(name)}"},
        )
        return super().get_object_parameters(name)
