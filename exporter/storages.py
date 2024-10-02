import logging
import os
import shutil
import sqlite3
from functools import cached_property
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile

import apsw
from django.core.files.storage import Storage
from sqlite_s3vfs import S3VFS
from storages.backends.s3boto3 import S3Boto3Storage

from common.util import log_timing
from exporter import measures
from exporter import quotas
from exporter import sqlite

logger = logging.getLogger(__name__)


class EmptyFileException(Exception):
    pass


def is_valid_sqlite(file_path: str) -> bool:
    """
    `file_path` should be a path to a file on the local file system. Validation.

    includes:
    - test that a file exists at `file_path`,
    - test that the file at `file_path` has non-zero size,
    - perform a SQLite PRAGMA quick_check on file at `file_path`.

    If errors are found during validation, then exceptions that this function
    may raise include:
        - sqlite3.DatabaseError if the PRAGMA quick_check fails.
        - FileNotFoundError if no file was found at `file_path`.
        - exporter.storage.EmptyFileException if the file at `file_path` has
          zero size.

    Returns True if validation checks all pass.
    """

    if path.getsize(file_path) == 0:
        raise EmptyFileException(f"{file_path} has zero size.")

    with sqlite3.connect(file_path) as connection:
        cursor = connection.cursor()
        # Executing "PRAGMA quick_check" raises DatabaseError if the SQLite
        # database file is invalid.
        cursor.execute("PRAGMA quick_check")
    return True


def is_valid_csv(file_path: str) -> bool:
    """
    `file_path` should be a path to a file on the local file system. Validation.

    includes:
    - test that a file exists at `file_path`,
    - test that the file at `file_path` has non-zero size,

    If errors are found during validation, then exceptions that this function
    may raise include:
        - FileNotFoundError if no file was found at `file_path`.
        - exporter.storage.EmptyFileException if the file at `file_path` has
          zero size.

    Returns True if validation checks all pass.
    """

    if path.getsize(file_path) == 0:
        raise EmptyFileException(f"{file_path} has zero size.")

    return True


class HMRCStorage(S3Boto3Storage):
    def get_default_settings(self):
        # Importing settings here makes it possible for tests to override_settings
        from django.conf import settings

        return dict(
            super().get_default_settings(),
            bucket_name=settings.HMRC_STORAGE_BUCKET_NAME,
            default_acl="private",
        )

    def get_object_parameters(self, name):
        self.object_parameters.update(
            {"ContentDisposition": f"attachment; filename={path.basename(name)}"},
        )
        return super().get_object_parameters(name)


class DataExportMixin:
    """Mixin class used to define a common export API among SQLite Storage
    subclasses."""

    def export_database(self, filename: str):
        """Export Tamato's primary database to an SQLite file format, saving to
        Storage's backing store (S3, local file system, etc.)."""
        raise NotImplementedError


class SQLiteS3StorageBase(S3Boto3Storage):
    """Storage base class used for remotely storing SQLite database files to an
    AWS S3-like backing store (AWS S3, Minio, etc.)."""

    def get_default_settings(self):
        from django.conf import settings

        return dict(
            super().get_default_settings(),
            bucket_name=settings.SQLITE_STORAGE_BUCKET_NAME,
            access_key=settings.SQLITE_S3_ACCESS_KEY_ID,
            secret_key=settings.SQLITE_S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.SQLITE_S3_ENDPOINT_URL,
            default_acl="private",
        )

    def generate_filename(self, filename: str) -> str:
        from django.conf import settings

        filename = path.join(
            settings.SQLITE_STORAGE_DIRECTORY,
            filename,
        )
        return super().generate_filename(filename)


class QuotasExportS3StorageBase(S3Boto3Storage):
    """Storage base class used for remotely storing Quotas Export CSV file to an
    AWS S3-like backing store (AWS S3, Minio, etc.)."""

    def get_default_settings(self):
        from django.conf import settings

        quotas_s3_settings = dict(
            super().get_default_settings(),
            bucket_name=settings.QUOTAS_EXPORT_STORAGE_BUCKET_NAME,
            access_key=settings.QUOTAS_EXPORT_S3_ACCESS_KEY_ID,
            secret_key=settings.QUOTAS_EXPORT_S3_SECRET_ACCESS_KEY,
            region_name=settings.QUOTAS_EXPORT_S3_REGION_NAME,
            endpoint_url=settings.S3_ENDPOINT_URL,
            default_acl="private",
        )
        print(quotas_s3_settings)

        return quotas_s3_settings

    def generate_filename(self, filename: str) -> str:
        from django.conf import settings

        filename = path.join(
            settings.QUOTAS_EXPORT_DESTINATION_FOLDER,
            filename,
        )
        return super().generate_filename(filename)


class SQLiteS3VFSStorage(DataExportMixin, SQLiteS3StorageBase):
    """
    Storage class used for remotely storing SQLite database files to an AWS
    S3-like backing store.

    This class uses the s3sqlite package (
    https://pypi.org/project/s3sqlite/)
    to apply an S3 virtual file system strategy when saving the SQLite file to
    S3.
    """

    def exists(self, filename: str) -> bool:
        return any(self.listdir(filename))

    @cached_property
    def vfs(self) -> apsw.VFS:
        return S3VFS(bucket=self.bucket, block_size=65536)

    @log_timing(logger_function=logger.info)
    def export_database(self, filename: str):
        connection = apsw.Connection(filename, vfs=self.vfs.name)
        sqlite.make_export(connection)
        connection.close()
        logger.info(f"Serializing {filename} to S3 storage.")
        vfs_fileobj = self.vfs.serialize_fileobj(key_prefix=filename)
        self.bucket.Object(filename).upload_fileobj(vfs_fileobj)


class SQLiteS3Storage(DataExportMixin, SQLiteS3StorageBase):
    """
    Storage class used for remotely storing SQLite database files to an AWS
    S3-like backing store.

    This class applies a strategy that first creates a temporary instance of the
    SQLite file on the local file system before transfering its contents to S3.
    """

    @log_timing(logger_function=logger.info)
    def export_database(self, filename: str):
        with NamedTemporaryFile() as temp_sqlite_db:
            connection = apsw.Connection(temp_sqlite_db.name)
            sqlite.make_export(connection)
            connection.close()
            logger.info(f"Saving {filename} to S3 storage.")
            if is_valid_sqlite(temp_sqlite_db.name):
                # Only save to S3 if the SQLite file is valid.
                self.save(filename, temp_sqlite_db.file)


class SQLiteLocalStorage(DataExportMixin, Storage):
    """Storage class used for storing SQLite database files to the local file
    system."""

    def __init__(self, location) -> None:
        self._location = Path(location).expanduser().resolve()
        logger.info(f"Normalised path `{location}` to `{self._location}`.")
        if not self._location.is_dir():
            raise Exception(f"Directory does not exist: {location}.")

    def path(self, name: str) -> str:
        return str(self._location.joinpath(name))

    def exists(self, name: str) -> bool:
        return Path(self.path(name)).exists()

    @log_timing(logger_function=logger.info)
    def export_database(self, filename: str):
        connection = apsw.Connection(self.path(filename))
        logger.info(f"Saving {filename} to local file system storage.")
        sqlite.make_export(connection)
        connection.close()


class CSVLocalStorage(Storage):
    """Storage class used for storing quota CSV data to the local file
    system."""

    def __init__(self, location) -> None:
        self._location = Path(location).expanduser().resolve()
        logger.info(f"Normalised path `{location}` to `{self._location}`.")
        if not self._location.is_dir():
            raise Exception(f"Directory does not exist: {location}.")

    def path(self, name: str) -> str:
        return str(self._location.joinpath(name))

    def exists(self, name: str) -> bool:
        return Path(self.path(name)).exists()

    def run_export(self, filename):
        pass

    def is_valid_csv(self, filename):
        # Specific test for validity may be added in the derived classes
        return is_valid_csv(filename)

    @log_timing(logger_function=logger.info)
    def export_csv(self, filename: str):
        print("Exporting measures")
        with NamedTemporaryFile() as csv_named_temp_file:
            logger.info(f"Saving {filename} to local file system storage.")
            self.run_export(csv_named_temp_file)
            if self.is_valid_csv(csv_named_temp_file.name):
                # Only save to S3 if the CSV file is valid.
                destination_file_path = os.path.join(self._location, filename)
                self.save_local(destination_file_path, csv_named_temp_file)

    def save_local(self, destination_file_path, file_to_save):
        shutil.copy(file_to_save.name, destination_file_path)


class QuotaLocalStorage(CSVLocalStorage):
    """Define export function for quota."""

    def run_export(self, filename):
        quotas.make_export(filename)


class MeasureLocalStorage(CSVLocalStorage):
    """Define export function for quota."""

    def run_export(self, filename):
        measures.make_export(filename)


class QuotaS3Storage(DataExportMixin, QuotasExportS3StorageBase):
    """
    Storage class used for remotely storing SQLite database files to an AWS
    S3-like backing store.

    This class applies a strategy that first creates a temporary instance of the
    SQLite file on the local file system before transferring its contents to S3.
    """

    @log_timing(logger_function=logger.info)
    def export_csv(self, filename: str):
        with NamedTemporaryFile() as csv_named_temp_file:
            quotas.make_export(csv_named_temp_file)
            logger.info(f"Saving {filename} to S3 storage.")
            if is_valid_csv(csv_named_temp_file.name):
                # Only save to S3 if the CSV file is valid.
                self.save(filename, csv_named_temp_file.file)

            os.unlink(csv_named_temp_file.name)
