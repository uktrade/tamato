import logging
import sys

import kombu
from django.core.management import BaseCommand

from exporter.tasks import upload_workbaskets
from exporter.util import UploadStatus

logger = logging.getLogger(__name__)


def run_task_or_exit(task, local=False, *args, **kwargs):
    """
    Run celery task, block then return the return value of the task, or exit..

    :param local:  Run locally (bypass celery)
    :param task:  Celery task to run.
    :return: Result of task.

    Utility function for management commands that require the ability
    to start a celery task, then wait for the result.

    Tasks may optionally be run locally, which can be useful if the
    user needs to run a task, but celery infrastructure is unavailable.
    """
    try:
        if local:
            return task.apply(args=args, kwargs=kwargs).get()
        return task.apply_async(args=args, kwargs=kwargs).get()
    except kombu.exceptions.OperationalError:
        # OperationalError here usually indicate that it was not possible to
        # connect to the celery backend, e.g. redis is not accessible/up.
        logger.error(
            "OperationalError - This usually indicates celery or redis are unavailable.",
        )
        raise


class Command(BaseCommand):
    """
    Upload envelope to HMRC s3 storage.

    Invalid envelopes are NOT uploaded.
    """

    help = "Upload workbaskets ready for export to HMRC S3 Storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "-l",
            dest="local",
            action="store_true",
            help="Run task locally [bypass celery].",
        )

    def handle(self, *args, **options):
        local = options["local"]
        upload_status = UploadStatus(
            **run_task_or_exit(upload_workbaskets, local=local)
        )
        upload_status.output(self.stdout)

        sys.exit(0 if upload_status.success else 1)
