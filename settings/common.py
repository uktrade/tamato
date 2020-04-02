"""
Django settings for tamato project.
"""
import os
import sys
from os.path import abspath
from os.path import dirname
from os.path import join

from common.util import is_truthy


# Name of the deployment environment (dev/alpha)
ENV = os.environ.get("ENV", "dev")


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


# -- Application

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    # "health_check",
    # "health_check.db",
    # "health_check.cache",
    # "health_check.storage",
    "webpack_loader",
    "common",
    "commodities",
    "measures",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": ["node_modules/govuk-frontend/govuk",],
        "APP_DIRS": True,
        "OPTIONS": {"environment": "common.jinja2.environment",},
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

# TODO - tie in to DIT SSO?


# -- Security
SECRET_KEY = os.environ.get("SECRET_KEY", "@@i$w*ct^hfihgh21@^8n+&ba@_l3x")

# Whitelist values for the HTTP Host header, to prevent certain attacks
ALLOWED_HOSTS = [host for host in os.environ.get("ALLOWED_HOSTS", "").split() if host]

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", PROJECT_NAME),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

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
        "": {"handlers": ["console"], "level": "WARNING",},
        "commodities": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "common": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
        "measures": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        },
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
            before_send=lambda event, hint: None,
        )


# -- Testing

# Override default Django test runner
TEST_RUNNER = "settings.tests.runner.PytestTestRunner"
