import logging
from functools import cached_property
from os import path
from pathlib import Path

import apsw
from django.core.files.storage import Storage
from sqlite_s3vfs import S3VFS
from storages.backends.s3boto3 import S3Boto3Storage

from exporter import sqlite

logger = logging.getLogger(__name__)


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


class SQLiteStorageMixin:
    def make_export(self, filename: str):
        """Export to SQLite database."""
        raise NotImplementedError


class SQLiteS3VFSStorage(SQLiteStorageMixin, S3Boto3Storage):
    """Remote Sqlite DB storage using s3sqlite to provide virtual file system
    storage (see https://pypi.org/project/s3sqlite/)."""

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

    @cached_property
    def vfs(self) -> apsw.VFS:
        return S3VFS(bucket=self.bucket, block_size=65536)

    def make_export(self, filename: str):
        logger.info(f"Generating SQLite database {filename}")

        connection = apsw.Connection(filename, vfs=self.vfs.name)
        sqlite.make_export(connection)

        logger.info(f"Serializing {filename}")

        vfs_fileobj = self.vfs.serialize_fileobj(key_prefix=filename)
        self.bucket.Object(filename).upload_fileobj(vfs_fileobj)

        logger.info(f"Export {filename} complete")


class SQLiteLocalStorage(SQLiteStorageMixin, Storage):
    def __init__(self, location) -> None:
        self._location = Path(location).expanduser().resolve()
        logger.info(f"Normalised path `{location}` to `{self._location}`.")
        if not self._location.is_dir():
            raise Exception(f"Directory does not exist: {location}.")

    def path(self, name: str) -> str:
        return str(self._location.joinpath(name))

    def exists(self, name: str) -> bool:
        return Path(self.path(name)).exists()

    def make_export(self, filename: str):
        logger.info(f"Generating SQLite database {filename} ...")

        connection = apsw.Connection(self.path(filename))
        sqlite.make_export(connection)

        logger.info(f"Export {filename} done")
