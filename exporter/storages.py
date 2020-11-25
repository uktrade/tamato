from storages.backends.s3boto3 import S3Boto3Storage


class HMRCStorage(S3Boto3Storage):
    def get_default_settings(self):
        # Importing settings here makes it possible for tests to override_settings
        from django.conf import settings

        return dict(
            super().get_default_settings(),
            location=settings.HMRC_STORAGE_DIRECTORY,
            default_acl="private",
        )
