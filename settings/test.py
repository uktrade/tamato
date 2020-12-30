from settings.common import *


ENV = "test"

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

# Cache settings - put things in memory to minimise dependencies.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

NURSERY_CACHE_ENGINE = "importer.cache.memory.MemoryCacheEngine"

SKIP_WORKBASKET_VALIDATION = is_truthy(os.getenv("SKIP_WORKBASKET_VALIDATION", True))
