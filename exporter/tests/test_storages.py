import sqlite3
from contextlib import nullcontext
from os import path

import pytest
from django.conf import settings

from exporter.storages import EmptyFileException, is_valid_quotas_csv, SQLiteS3StorageBase, QuotasExportS3StorageBase, HMRCStorage, QuotaLocalStorage
from exporter.storages import is_valid_sqlite

pytestmark = pytest.mark.django_db


def get_test_file_path(filename) -> str:
    return str(path.join(
        path.dirname(path.abspath(__file__)),
        "test_files",
        filename,
    ))

@pytest.mark.parametrize(
    ("test_file_path, expect_context"),
    (
        (
            get_test_file_path("valid_sqlite.db"),
            nullcontext(),
        ),
        (
            "/invalid/file/path",
            pytest.raises(FileNotFoundError),
        ),
        (
            get_test_file_path("empty_sqlite.db"),
            pytest.raises(EmptyFileException),
        ),
        (
            get_test_file_path("invalid_sqlite.db"),
            pytest.raises(sqlite3.DatabaseError),
        ),
    ),
)
@pytest.mark.exporter
def test_is_valid_sqlite(test_file_path, expect_context):
    """Test that `is_valid_sqlite()` raises correct exceptions for invalid
    SQLite files and succeeds for valid SQLite files."""
    with expect_context:
        is_valid_sqlite(test_file_path)


@pytest.mark.parametrize(
    ("test_file_path, expect_context"),
    (
        (
            get_test_file_path("valid_sqlite.db"),
            nullcontext(),
        ),
        (
            "/invalid/file/path",
            pytest.raises(FileNotFoundError),
        ),
        (
            get_test_file_path("empty.csv"),
            pytest.raises(EmptyFileException),
        ),
    ),
)
@pytest.mark.exporter
def test_is_valid_quotas_csv(test_file_path, expect_context):
    """Test that `is_valid_sqlite()` raises correct exceptions for invalid
    SQLite files and succeeds for valid SQLite files."""
    with expect_context:
        is_valid_quotas_csv(test_file_path)

@pytest.mark.exporter
class TestSQLiteS3StorageBase:
    target_class=SQLiteS3StorageBase

    def get_target(self):
        return self.target_class()

    def test_get_default_settings(self):
        target = self.get_target()
        default_settings = target.get_default_settings()

        assert default_settings['bucket_name'] ==  settings.SQLITE_STORAGE_BUCKET_NAME
        assert default_settings['access_key'] ==  settings.SQLITE_S3_ACCESS_KEY_ID
        assert default_settings['secret_key'] ==  settings.SQLITE_S3_SECRET_ACCESS_KEY
        assert default_settings['endpoint_url'] ==  settings.SQLITE_S3_ENDPOINT_URL
        assert default_settings['default_acl'] ==  "private"

    def test_generate_filename(self):
        target = self.get_target()
        file_name = target.generate_filename('zzz.zzz')
        assert file_name == 'sqlite/zzz.zzz'

@pytest.mark.exporter
class TestQuotasExportS3StorageBase:
    target_class=QuotasExportS3StorageBase

    def get_target(self):
        return self.target_class()

    def test_get_default_settings(self):
        target = self.get_target()
        default_settings = target.get_default_settings()

        assert default_settings['bucket_name'] ==  settings.QUOTAS_EXPORT_STORAGE_BUCKET_NAME
        assert default_settings['access_key'] ==  settings.QUOTAS_EXPORT_S3_ACCESS_KEY_ID
        assert default_settings['secret_key'] ==  settings.QUOTAS_EXPORT_S3_SECRET_ACCESS_KEY
        assert default_settings['endpoint_url'] ==  settings.S3_ENDPOINT_URL
        assert default_settings['default_acl'] ==  "private"

    def test_generate_filename(self):
        target = self.get_target()
        file_name = target.generate_filename('zzz.zzz')
        assert file_name == 'quotas_export/zzz.zzz'

@pytest.mark.exporter
class TestHMRCStorage:
    target_class=HMRCStorage

    def get_target(self):
        return self.target_class()

    def test_get_default_settings(self):
        target = self.get_target()
        default_settings = target.get_default_settings()

        assert default_settings['bucket_name'] ==  settings.HMRC_STORAGE_BUCKET_NAME
        assert default_settings['default_acl'] ==  "private"

    def test_get_object_parameters(self):
        target = self.get_target()
        params = target.get_object_parameters('file.ext')
        assert params == {'ContentDisposition': 'attachment; filename=file.ext'}

@pytest.mark.exporter
class TestQuotaLocalStorage:
    target_class=QuotaLocalStorage

    def get_target(self, location='zzz'):
        return self.target_class(location)

    def test_init_bad_location(self):
        target = self.get_target()
        params = target.get_object_parameters('file.ext')
        assert params == {'ContentDisposition': 'attachment; filename=file.ext'}

