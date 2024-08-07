from fakeredis import FakeConnection

from settings.common import *

ENV = "test"
BASE_SERVICE_URL = "http://localhost"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

INSTALLED_APPS.append("common.tests")

# Bucket settings are belt-and-braces to guard against running in a real bucket
HMRC_BUCKET_STORAGE_NAME = os.environ.get("TEST_HMRC_BUCKET_STORAGE_NAME", "test-hmrc")

# HMRC API client settings
HMRC["base_url"] = "https://test-api.service.hmrc.gov.uk"
HMRC["client_id"] = "test-client-id"
HMRC["client_secret"] = "test-client-secret"
HMRC["service_reference_number"] = "test-srn"

AWS_ACCESS_KEY_ID = os.environ.get("TEST_AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("TEST_AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("TEST_AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.environ.get("TEST_AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("TEST_AWS_S3_REGION_NAME", "eu-west-2")

# Cache settings - put things in fake redis cache.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",  # Local dummy address
        "OPTIONS": {
            "REDIS_CLIENT_CLASS": "fakeredis.FakeRedis",
            "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
        },
    },
}

NURSERY_CACHE_ENGINE = "importer.cache.memory.MemoryCacheEngine"

SKIP_WORKBASKET_VALIDATION = is_truthy(os.getenv("SKIP_WORKBASKET_VALIDATION", True))
USE_IMPORTER_CACHE = is_truthy(os.getenv("USE_IMPORTER_CACHE", False))

HMRC_PACKAGING_S3_ACCESS_KEY_ID = "test_local_id"
HMRC_PACKAGING_S3_SECRET_ACCESS_KEY = "test_local_key"
IMPORTER_S3_ACCESS_KEY_ID = "test_local_id"
IMPORTER_S3_SECRET_ACCESS_KEY = "test_local_key"
S3_ENDPOINT_URL = "https://test-s3-url/"

NOTIFICATIONS_API_KEY = "test-key"

TARIFF_API_INTERFACE = "publishing.tariff_api.interface.TariffAPIStubbed"

FILE_UPLOAD_HANDLERS = ("django.core.files.uploadhandler.MemoryFileUploadHandler",)
