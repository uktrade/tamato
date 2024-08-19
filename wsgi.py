"""
WSGI config for tamato project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

import dotenv

# Needed for AWS X-Ray
from dbt_copilot_python.utility import is_copilot
from django.core.wsgi import get_wsgi_application
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware

dotenv.load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

application = get_wsgi_application()

if is_copilot():
    application = OpenTelemetryMiddleware(application)
