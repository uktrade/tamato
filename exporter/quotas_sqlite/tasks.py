import logging
import os
from datetime import date

import settings
from common.celery import app
from exporter import storages

logger = logging.getLogger(__name__)


def get_output_filename():
    """
    Generate output filename with transaction order field.

    If no revisions are present the filename is prefixed with seed_.
    """
    date_str = f"{date.today().strftime('%Y%m%d')}"
    return f"quotas_export_{date_str}.sqlite"


@app.task
def export_and_upload_quotas_sqlite(local_path: str = None) -> bool:
    """
    Generates an export of latest published quota data from the TAP database to
    an SQLite file.

    If `local_path` is provided, then the quotas SQLite file will be saved in
    that directory location (note that in this case `local_path` must be an
    existing directory path on the local file system).

    If `local_path` is not provided, then the quotas SQLite file will be saved
    to the configured S3 bucket.
    """
    sqlite_file_name = get_output_filename()
    if local_path:
        logger.info("Quota SQLite export process targeting local file system.")
        storage = storages.QuotaSQLiteLocalStorage(location=local_path)
        export_filename = storage.generate_filename(sqlite_file_name)
    else:
        logger.info("Quota SQLite export process targeting S3 file system.")
        storage = storages.QuotaSQLiteS3Storage()
        export_filename = storage.generate_filename(sqlite_file_name)




    logger.info(f"Checking for existing file {export_filename}.")
    if storage.exists(export_filename):
        logger.info(
            f"file {export_filename} already exists. Exiting process, "
            f"pid={os.getpid()}.",
        )
        return False

    logger.info(f"Generating quotas SQLite export {export_filename}.")
    storage.export_sqlite(export_filename)
    logger.info(f"Quotas SQLite export {export_filename} complete.")
    return True
