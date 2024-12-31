import logging
import os

from common.celery import app
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from exporter import storages

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
def export_and_upload_sqlite(local_path: str = None) -> bool:
    """
    Generates an export of latest published data from the primary database to a
    portable SQLite database file. The most recently published Transaction's
    `order` value is used to define latest published data, and its value is used
    to name the generated SQLite database file.

    If `local_path` is provided, then the SQLite database file will be saved in
    that directory location (note that in this case `local_path` must be an
    existing directory path on the local file system).

    If `local_path` is not provided, then the SQLite database file will be saved
    to the configured S3 bucket.
    """
    db_name = get_output_filename()

    if local_path:
        logger.info("SQLite export process targeting local file system.")
        storage = storages.SQLiteLocalStorage(location=local_path)
    else:
        logger.info("SQLite export process targeting S3 file system.")
        storage = storages.SQLiteS3Storage()

    export_filename = storage.generate_filename(db_name)

    logger.info(f"Checking for existing database {export_filename}.")
    if storage.exists(export_filename):
        logger.info(
            f"Database {export_filename} already exists. Exiting process, "
            f"pid={os.getpid()}.",
        )
        return False

    logger.info(f"Generating SQLite database export {export_filename}.")
    storage.export_database(export_filename)
    logger.info(f"SQLite database export {export_filename} complete.")
    return True
