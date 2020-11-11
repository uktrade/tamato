from settings.common import *


ENV = "test"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

INSTALLED_APPS.append("common.tests")

# Bucket settings are belt-and-braces to guard against running in a real bucket
HMRC_BUCKET_NAME = os.environ.get("TEST_HMRC_BUCKET_NAME", "test-hmrc")

AWS_ACCESS_KEY_ID = os.environ.get("TEST_AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("TEST_AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("TEST_AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.environ.get("TEST_AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("TEST_AWS_S3_REGION_NAME", "eu-west-2")
