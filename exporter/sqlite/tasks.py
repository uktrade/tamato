import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

from common.celery import app
from exporter import sqlite
from taric.models import Envelope

logger = logging.getLogger(__name__)


@app.task
def export_and_upload_sqlite():
    storage = S3Boto3Storage(bucket_name=settings.SQLITE_STORAGE_BUCKET_NAME)
    latest_envelope = Envelope.objects.order_by("envelope_id").last()
    export_filename = storage.generate_filename(
        f"{settings.SQLITE_STORAGE_DIRECTORY}{latest_envelope.envelope_id}.db",
    )

    logger.debug("Checking for need to upload tariff database %s", export_filename)
    if storage.exists(export_filename):
        logger.debug("Database %s already present", export_filename)
        return

    with TemporaryDirectory(prefix="sqlite") as db_dir:
        database_path = Path(db_dir) / "tariff.db"
        logger.info("Generating database %s", database_path)
        sqlite.make_export(database_path)

        logger.info("Uploading database %s", export_filename)
        with open(database_path, "rb") as database_file:
            storage.save(export_filename, database_file)

        logger.info("Upload complete")
