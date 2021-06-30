import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

from common.celery import app
from common.models.transactions import Transaction
from exporter import sqlite

logger = logging.getLogger(__name__)


@app.task
def export_and_upload_sqlite() -> bool:
    storage = S3Boto3Storage(bucket_name=settings.SQLITE_STORAGE_BUCKET_NAME)
    latest_transaction = Transaction.latest_approved()

    target_filename = Path(settings.SQLITE_STORAGE_DIRECTORY) / "{:0>9}.db".format(
        latest_transaction.order,
    )
    export_filename = storage.generate_filename(str(target_filename))

    logger.debug("Checking for need to upload tariff database %s", export_filename)
    if storage.exists(export_filename):
        logger.debug("Database %s already present", export_filename)
        return False

    with TemporaryDirectory(prefix="sqlite") as db_dir:
        database_path = Path(db_dir) / "tariff.db"
        logger.info("Generating database %s", database_path)
        sqlite.make_export(database_path)

        logger.info("Uploading database %s", export_filename)
        with open(database_path, "rb") as database_file:
            storage.save(export_filename, database_file)

        logger.info("Upload complete")
        return True
