import functools
import logging
import os
from functools import cached_property
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile

import apsw
from django.core.files.storage import Storage
from django.utils import timezone
from sqlite_s3vfs import S3VFS
from storages.backends.s3boto3 import S3Boto3Storage

from exporter import sqlite

logger = logging.getLogger(__name__)


def info_log_timing(func):
    """Decorator function to log start and end time of a decorated function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = timezone.localtime()
        logger.info(
            f"Entering the function {func.__name__}() on process "
            f"pid={os.getpid()} at {start_time.isoformat()}",
        )

        result = func(*args, **kwargs)

        end_time = timezone.localtime()
        elapsed_time = end_time - start_time
        logger.info(
            f"Exited the function {func.__name__}() on "
            f"process pid={os.getpid()} at {end_time.isoformat()} after "
            f"an elapsed time of {elapsed_time}.",
        )

        return result

    return wrapper


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


class SQLiteExportMixin:
    def make_export(self, filename: str):
        """Export to SQLite database."""
        raise NotImplementedError


class SQLiteS3StorageBase(S3Boto3Storage):
    """Storage class used for remotely storing SQLite dump files."""

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

    def exists(self, filename: str) -> bool:
        return any(self.listdir(filename))


class SQLiteS3VFSStorage(SQLiteExportMixin, SQLiteS3StorageBase):
    """Remote SQLite DB creation and storage using s3sqlite to provide virtual
    file system storage (see https://pypi.org/project/s3sqlite/)."""

    @cached_property
    def vfs(self) -> apsw.VFS:
        return S3VFS(bucket=self.bucket, block_size=65536)

    @info_log_timing
    def make_export(self, filename: str):
        connection = apsw.Connection(filename, vfs=self.vfs.name)
        sqlite.make_export(connection)
        logger.info(f"Serializing {filename} to S3 storage.")
        vfs_fileobj = self.vfs.serialize_fileobj(key_prefix=filename)
        self.bucket.Object(filename).upload_fileobj(vfs_fileobj)


class SQLiteS3Storage(SQLiteExportMixin, SQLiteS3StorageBase):
    """Remote SQLite DB creation and storage."""

    @info_log_timing
    def make_export(self, filename: str):
        with NamedTemporaryFile() as temp_sqlite_db:
            connection = apsw.Connection(temp_sqlite_db.name)
            sqlite.make_export(connection)
            logger.info(f"Saving {filename} to S3 storage.")
            self.save(filename, temp_sqlite_db.file)


class SQLiteLocalStorage(SQLiteExportMixin, Storage):
    """Local file system SQLite DB creation and storage."""

    def __init__(self, location) -> None:
        self._location = Path(location).expanduser().resolve()
        logger.info(f"Normalised path `{location}` to `{self._location}`.")
        if not self._location.is_dir():
            raise Exception(f"Directory does not exist: {location}.")

    def path(self, name: str) -> str:
        return str(self._location.joinpath(name))

    def exists(self, name: str) -> bool:
        return Path(self.path(name)).exists()

    @info_log_timing
    def make_export(self, filename: str):
        connection = apsw.Connection(self.path(filename))
        logger.info(f"Saving {filename} to local file system storage.")
        sqlite.make_export(connection)
