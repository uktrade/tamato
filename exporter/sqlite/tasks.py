import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings

from common.celery import app
from common.models.transactions import Transaction
from exporter import sqlite
from exporter.storages import SQLiteStorage

logger = logging.getLogger(__name__)


@app.task
def export_and_upload_sqlite() -> bool:
    """
    Generates an export of the currently attached database to a portable SQLite
    file and uploads it to the configured S3 bucket.

    If an SQLite export of the current state of the database (as given by the
    most recently approved transaction ID) already exists, no action is taken.
    Returns a boolean that is ``True`` if a file was uploaded and ``False`` if
    not.
    """
    storage = SQLiteStorage()
    latest_transaction = Transaction.latest_approved()
    db_name = f"{latest_transaction.order:0>9}.db"

    target_filename = Path(settings.SQLITE_STORAGE_DIRECTORY) / db_name
    export_filename = storage.generate_filename(str(target_filename))

    logger.debug("Checking for need to upload tariff database %s", export_filename)
    if storage.exists(export_filename):
        logger.debug("Database %s already present", export_filename)
        return False

    logger.info("Generating database")
    database = BytesIO(sqlite.make_export())

    logger.info("Uploading database %s", export_filename)
    storage.save(export_filename, database)

    logger.info("Upload complete")
    return True
