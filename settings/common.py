"""
Django settings for tamato project.
"""
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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "django_filters",
    # "health_check",
    # "health_check.db",
    # "health_check.cache",
    # "health_check.storage",
    "authbroker_client",
    "polymorphic",
    "rest_framework",
    "webpack_loader",
    "common",
    "additional_codes.apps.AdditionalCodesConfig",
    "certificates.apps.CertificatesConfig",
    "commodities.apps.CommoditiesConfig",
    "footnotes.apps.FootnotesConfig",
    "geo_areas.apps.GeoAreasConfig",
    "hmrc_sdes",
    "importer",
    "measures.apps.MeasuresConfig",
    "quotas.apps.QuotasConfig",
    "regulations.apps.RegulationsConfig",
    # XXX need to keep this for migrations. delete later.
    "taric",
    "workbaskets",
    "exporter",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            ]
        },
    },
]


# -- Auth
LOGIN_URL = reverse_lazy("authbroker_client:login")
LOGIN_REDIRECT_URL = reverse_lazy("index")

AUTHBROKER_URL = os.environ.get("AUTHBROKER_URL", "https://sso.trade.gov.uk")
AUTHBROKER_CLIENT_ID = os.environ.get("AUTHBROKER_CLIENT_ID")
AUTHBROKER_CLIENT_SECRET = os.environ.get("AUTHBROKER_CLIENT_SECRET")

AUTHENTICATION_BACKENDS = (
    "authbroker_client.backends.AuthbrokerBackend",
    "django.contrib.auth.backends.ModelBackend",
)

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

# -- Cache

CACHE_URL = os.getenv("CACHE_URL", "redis://0.0.0.0:6379/1")

if VCAP_SERVICES.get("redis"):
    for redis_instance in VCAP_SERVICES["redis"]:
        if redis_instance["name"] == "DJANGO_CACHE":
            CACHE_URL = redis_instance["credentials"]["uri"]
            break
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "TIMEOUT": None,
        },
    }
}

NURSERY_CACHE_ENGINE = os.getenv(
    "NURSERY_CACHE_ENGINE", "importer.cache.memory.MemoryCacheEngine"
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
            CELERY_BROKER_URL = redis_instance["credentials"]["uri"]
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
        "default": {"format": "%(asctime)s %(name)s %(levelname)s %(message)s"}
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "loggers": {
        "root": {"handlers": ["console"], "level": "WARNING"},
        "importer": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
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

if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        environment=ENV,
        integrations=[DjangoIntegration()],
    )
    if "shell" in sys.argv or "shell_plus" in sys.argv:
        sentry_sdk.init(
            # discard all events
            before_send=lambda event, hint: None
        )


# -- Testing

# Override default Django test runner
TEST_RUNNER = "settings.tests.runner.PytestTestRunner"


# -- REST Framework
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
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
        "HMRC_API_BASE_URL", "https://test-api.service.hmrc.gov.uk"
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
