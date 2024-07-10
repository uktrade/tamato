import logging
import os

from django.utils import timezone

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
    Generates an export of the currently attached database to a portable SQLite
    file and uploads it to the configured S3 bucket.

    If an SQLite export of the current state of the database (as given by the
    most recently approved transaction ID) already exists, no action is taken.
    Returns a boolean that is ``True`` if a file was uploaded and ``False`` if
    not.
    """
    start_time = timezone.localtime()
    logger.info(
        f"SQLite export process, pid={os.getpid()}, started at {start_time.isoformat()}",
    )

    db_name = get_output_filename()

    if local_path:
        logger.info("SQLite export process targetting local file system.")
        storage = storages.SQLiteLocalStorage(location=local_path)
    else:
        logger.info("SQLite export process targetting S3 file system.")
        storage = storages.SQLiteS3VFSStorage()

    export_filename = storage.generate_filename(db_name)

    logger.info(f"Checking for existing database {export_filename}")
    if storage.exists(export_filename):
        elapsed_time = timezone.localtime() - start_time
        logger.info(
            f"Database {export_filename} already exists. "
            f"Exiting process, pid={os.getpid()}, after elapsed time {elapsed_time}.",
        )
        return False

    storage.make_export(export_filename)

    elapsed_time = timezone.localtime() - start_time
    logger.info(
        f"SQLite export process, pid={os.getpid()}, "
        f"done creating {export_filename} after elapsed time of {elapsed_time}.",
    )
    return True
