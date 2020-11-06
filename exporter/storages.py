from functools import lru_cache

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class HMRCStorage(S3Boto3Storage):
    default_acl = "private"
    location = settings.HMRC_BUCKET_NAME


@lru_cache(None)
def get_hmrc_storage():
    return HMRCStorage()
