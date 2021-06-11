"""Django settings for tamato project."""
import json
import os
import sys
import uuid
from os.path import abspath
from os.path import dirname
from os.path import join

import dj_database_url
from django.urls import reverse_lazy

from common.util import is_truthy

# Name of the deployment environment (dev/alpha)
ENV = os.environ.get("ENV", "dev")

# Global variables
SSO_ENABLED = is_truthy(os.environ.get("SSO_ENABLED", "true"))
VCAP_SERVICES = json.loads(os.environ.get("VCAP_SERVICES", "{}"))

# -- Paths

# Name of the project
PROJECT_NAME = "tamato"

# Absolute path of project Django directory
BASE_DIR = dirname(dirname(abspath(__file__)))

# Directory to collect static files into
STATIC_ROOT = join(BASE_DIR, "run", "static")

# Directory for user uploaded files
MEDIA_ROOT = join(BASE_DIR, "run", "uploads")

# Django looks in these locations for additional static assets to collect
STATICFILES_DIRS = [
    join(BASE_DIR, "static"),
    join(BASE_DIR, "node_modules", "govuk-frontend", "govuk", "assets"),
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# -- Application

DJANGO_CORE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_extensions",
    "django_filters",
    "polymorphic",
    "rest_framework",
    "webpack_loader",
]
if SSO_ENABLED:
    THIRD_PARTY_APPS += [
        "authbroker_client",
    ]

if os.getenv("ELASTIC_TOKEN"):
    THIRD_PARTY_APPS += [
        "elasticapm.contrib.django",
    ]

    ELASTIC_APM = {
        "SERVICE_NAME": "TaMaTo",
        "SECRET_TOKEN": os.getenv("ELASTIC_TOKEN"),
        "SERVER_URL": "https://apm.elk.uktrade.digital",
        "ENVIRONMENT": ENV,
        "SERVER_TIMEOUT": os.getenv("ELASTIC_TIMEOUT", "20s"),
    }

DOMAIN_APPS = [
    "common",
    "additional_codes.apps.AdditionalCodesConfig",
    "certificates.apps.CertificatesConfig",
    "commodities.apps.CommoditiesConfig",
    "footnotes.apps.FootnotesConfig",
    "geo_areas.apps.GeoAreasConfig",
    "measures.apps.MeasuresConfig",
    "quotas.apps.QuotasConfig",
    "regulations.apps.RegulationsConfig",
]

TAMATO_APPS = [
    "hmrc_sdes",
    "importer",
    # XXX need to keep this for migrations. delete later.
    "taric",
    "workbaskets",
    "exporter",
    "crispy_forms",
    "crispy_forms_gds",
]

INSTALLED_APPS = [*DJANGO_CORE_APPS, *THIRD_PARTY_APPS, *TAMATO_APPS, *DOMAIN_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if SSO_ENABLED:
    MIDDLEWARE += [
        "authbroker_client.middleware.ProtectAllViewsMiddleware",
    ]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [
            "node_modules/govuk-frontend/govuk",
        ],
        "APP_DIRS": True,
        "OPTIONS": {"environment": "common.jinja2.environment"},
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# -- Auth
LOGIN_URL = reverse_lazy("login")
if SSO_ENABLED:
    LOGIN_URL = reverse_lazy("authbroker_client:login")

LOGIN_REDIRECT_URL = reverse_lazy("index")

AUTHBROKER_URL = os.environ.get("AUTHBROKER_URL", "https://sso.trade.gov.uk")
AUTHBROKER_CLIENT_ID = os.environ.get("AUTHBROKER_CLIENT_ID")
AUTHBROKER_CLIENT_SECRET = os.environ.get("AUTHBROKER_CLIENT_SECRET")

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
if SSO_ENABLED:
    AUTHENTICATION_BACKENDS += [
        "authbroker_client.backends.AuthbrokerBackend",
    ]

# -- Security
SECRET_KEY = os.environ.get("SECRET_KEY", "@@i$w*ct^hfihgh21@^8n+&ba@_l3x")

# Whitelist values for the HTTP Host header, to prevent certain attacks
# App runs inside GOV.UK PaaS, so we can allow all hosts
ALLOWED_HOSTS = ["*"]

# Sets the X-XSS-Protection: 1; mode=block header
SECURE_BROWSER_XSS_FILTER = True

# Sets the X-Content-Type-Options: nosniff header
SECURE_CONTENT_TYPE_NOSNIFF = True

# Secure the CSRF cookie
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Secure the session cookie
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

# Check specified header for whether connection is via HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -- Running Django

# Path to WSGI application
WSGI_APPLICATION = "wsgi.application"

# Path to root URL configuration
ROOT_URLCONF = f"urls"

# URL path where static files are served
STATIC_URL = "/assets/"

# -- Debug

# Activates debugging
DEBUG = is_truthy(os.environ.get("DEBUG", False))

# -- Database

if VCAP_SERVICES.get("postgres"):
    DB_URL = VCAP_SERVICES["postgres"][0]["credentials"]["uri"]
else:
    DB_URL = os.environ.get("DATABASE_URL", "postgres://localhost:5432/tamato")

DATABASES = {
    "default": dj_database_url.parse(DB_URL),
}

SQLITE = DB_URL.startswith("sqlite")

# -- Cache

CACHE_URL = os.getenv("CACHE_URL", "redis://0.0.0.0:6379/1")

if VCAP_SERVICES.get("redis"):
    for redis_instance in VCAP_SERVICES["redis"]:
        if redis_instance["name"] == "DJANGO_CACHE":
            credentials = redis_instance["credentials"]
            CACHE_URL = credentials["uri"]
            CACHE_URL += "?ssl_cert_reqs=required"
            break
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "TIMEOUT": None,
            "SOCKET_CONNECT_TIMEOUT": 5,
        },
    },
}

NURSERY_CACHE_ENGINE = os.getenv(
    "NURSERY_CACHE_ENGINE",
    "importer.cache.memory.MemoryCacheEngine",
)

# Settings about retrying uploads if the bucket or endpoint cannot be contacted.
# Names correspond to celery settings for retrying tasks:
#   https://docs.celeryproject.org/en/master/userguide/tasks.html#automatic-retry-for-known-exceptions
EXPORTER_UPLOAD_MAX_RETRIES = int(os.environ.get("EXPORTER_UPLOAD_MAX_RETRIES", "3"))
EXPORTER_UPLOAD_RETRY_BACKOFF_MAX = int(
    os.environ.get("EXPORTER_UPLOAD_RETRY_BACKOFF_MAX", "600"),
)
EXPORTER_UPLOAD_DEFAULT_RETRY_DELAY = int(
    os.environ.get("EXPORTER_UPLOAD_DEFAULT_RETRY_DELAY", "8"),
)


EXPORTER_MAXIMUM_ENVELOPE_SIZE = 39 * 1024 * 1024
EXPORTER_DISABLE_NOTIFICATION = is_truthy(
    os.environ.get("EXPORTER_DISABLE_NOTIFICATION", "false"),
)

# Wrap each request in a transaction
ATOMIC_REQUESTS = True

# -- Internationalization

# Enable Django translation system
USE_I18N = False

# Enable localized formatting of numbers and dates
USE_L10N = False

# Language code - ignored unless USE_I18N is True
LANGUAGE_CODE = "en-gb"

# Make Django use timezone-aware datetimes internally
USE_TZ = True

# Time zone
TIME_ZONE = "UTC"

# HMRC AWS settings (override the defaults)
HMRC_STORAGE_BUCKET_NAME = os.environ.get("HMRC_STORAGE_BUCKET_NAME", "hmrc")
HMRC_STORAGE_DIRECTORY = os.environ.get("HMRC_STORAGE_DIRECTORY", "tohmrc/staging/")

# SQLite AWS settings
SQLITE_STORAGE_BUCKET_NAME = os.environ.get("SQLITE_STORAGE_BUCKET_NAME")
SQLITE_STORAGE_DIRECTORY = os.environ.get("SQLITE_STORAGE_DIRECTORY", "sqlite/")

# Default AWS settings.
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_PRELOAD_METADATA = False
AWS_DEFAULT_ACL = None
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_REGION_NAME = "eu-west-2"

# Pickle could be used as a serializer here, as this always runs in a DMZ

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", CACHES["default"]["LOCATION"])

if VCAP_SERVICES.get("redis"):
    for redis_instance in VCAP_SERVICES["redis"]:
        if redis_instance["name"] == "CELERY_BROKER":
            credentials = redis_instance["credentials"]
            CELERY_BROKER_URL = credentials["uri"]
            CELERY_BROKER_URL += "?ssl_cert_reqs=required"
            break

CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# -- Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(name)s %(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
        "importer": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "exporter": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "commodities": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "common": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "footnotes": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "measures": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
    },
    "celery": {
        "handlers": ["celery", "console"],
        "level": os.environ.get("CELERY_LOG_LEVEL", "DEBUG"),
    },
}

# -- Sentry error tracking

SENTRY_ENABLED = is_truthy(os.environ.get("SENTRY_DSN", "False"))

if SENTRY_ENABLED:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_kwargs = {
        "dsn": os.environ["SENTRY_DSN"],
        "environment": ENV,
        "integrations": [DjangoIntegration(), RedisIntegration()],
    }
    if "shell" in sys.argv or "shell_plus" in sys.argv:
        sentry_kwargs["before_send"] = lambda event, hint: None

    if os.getenv("GIT_COMMIT"):
        sentry_kwargs["release"] = os.getenv("GIT_COMMIT")

    sentry_sdk.init(**sentry_kwargs)

# -- Testing

# Override default Django test runner
TEST_RUNNER = "settings.tests.runner.PytestTestRunner"

# -- REST Framework
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

TARIC_XSD = os.path.join(BASE_DIR, "common", "assets", "taric3.xsd")

DATA_IMPORT_USERNAME = os.environ.get("TAMATO_IMPORT_USERNAME", "test")

# -- HMRC API client settings
# See https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/application-restricted-endpoints
# And https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/secure-data-exchange-notifications/1.0
# And https://developer.service.hmrc.gov.uk/guides/fraud-prevention/
HMRC = {
    "base_url": os.environ.get(
        "HMRC_API_BASE_URL",
        "https://test-api.service.hmrc.gov.uk",
    ),
    "client_id": os.environ.get("HMRC_API_CLIENT_ID"),
    "client_secret": os.environ.get("HMRC_API_CLIENT_SECRET"),
    "token_url": os.environ.get("HMRC_API_TOKEN_URL", "/oauth/token"),
    "service_reference_number": os.environ.get("HMRC_API_SERVICE_REFERENCE_NUMBER"),
    "device_id": str(uuid.uuid4()),
}

SKIP_VALIDATION = is_truthy(os.getenv("SKIP_VALIDATION", False))
SKIP_WORKBASKET_VALIDATION = is_truthy(os.getenv("SKIP_WORKBASKET_VALIDATION", False))
USE_IMPORTER_CACHE = is_truthy(os.getenv("USE_IMPORTER_CACHE", True))

CRISPY_ALLOWED_TEMPLATE_PACKS = ["gds"]
CRISPY_TEMPLATE_PACK = "gds"
