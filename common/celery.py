import os

from celery import Celery
from celery.signals import setup_logging
from dbt_copilot_python.celery_health_check import healthcheck
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

app = Celery("tamato")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# this should be automactically configured via ^^ config_from_object
# but it isn't so here it's configured here
app.conf.task_routes = settings.CELERY_ROUTES

# Setup and expose the DBT Celery healthcheck interface.
app = healthcheck.setup(app)
