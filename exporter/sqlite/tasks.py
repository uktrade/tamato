import logging

from common.celery import app
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from exporter import sqlite
from exporter.storages import SQLiteStorage

logger = logging.getLogger(__name__)


def normalised_order(order):
    """Return a transaction's normalised order value - left-padded with zeroes
    to a normalised width of nine digits."""
    return f"{order:0>9}"


def get_output_filename():
    """
    Generate output filename with transaction order field.

    If no revisions are present the filename is prefixed with seed_.
    """
    tx = Transaction.objects.published().last()
    order = tx.order if tx else 0
    if tx.partition == TransactionPartition.REVISION:
        return f"{normalised_order(order)}.db"

    return f"seed_{normalised_order(order)}.db"


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
    db_name = get_output_filename()

    export_filename = storage.generate_filename(db_name)

    logger.debug("Checking for need to upload tariff database %s", export_filename)
    if storage.exists(export_filename):
        logger.debug("Database %s already present", export_filename)
        return False

    logger.info("Generating database %s", export_filename)
    sqlite.make_export(storage.get_connection(export_filename))
    logger.info("Generation complete")

    logger.info("Serializing %s", export_filename)
    storage.serialize(export_filename)
    logger.info("Serializing complete")

    logger.info("Upload complete")
    return True
