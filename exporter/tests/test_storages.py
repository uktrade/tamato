import csv
import os
import sqlite3
from contextlib import nullcontext
from os import path
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import sqlite_s3vfs
from django.conf import settings

from exporter.storages import EmptyFileException, is_valid_quotas_csv, SQLiteS3StorageBase, QuotasExportS3StorageBase, HMRCStorage, QuotaLocalStorage, SQLiteS3VFSStorage, SQLiteS3Storage, SQLiteLocalStorage, \
    QuotaS3Storage
from exporter.storages import is_valid_sqlite

pytestmark = pytest.mark.django_db


def get_test_file_path(filename) -> str:
    return str(path.join(
        path.dirname(path.abspath(__file__)),
        "test_files",
        filename,
    ))

@pytest.fixture()
def fake_connection():
    pass

@pytest.fixture()
def mock_make_export(fake_connection):
    def mock_make_export(*args, **kwargs):
        pass

@pytest.fixture()
def fake_apsw_connection():
    class FakeASPWConnection:
        def close(self):
            pass

    return FakeASPWConnection()

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
    target_class_location='exporter/tests/test_files'

    def get_target(self, location=None):
        if location is None:
            return self.target_class(self.target_class_location)
        return self.target_class(location)

    def test_init_bad_location(self):
        with pytest.raises(Exception) as e:
            self.get_target('zzz')

        assert str(e.value) == 'Directory does not exist: zzz.'

    def test_init_good_location(self):
        target = self.get_target()
        resolved_location = Path(self.target_class_location).expanduser().resolve()
        assert target._location == resolved_location

    def test_path(self):
        target = self.get_target()
        target_path = target.path('a.csv')
        expected_path = str(Path(self.target_class_location).expanduser().resolve()) + '/a.csv'
        assert target_path == expected_path

    def test_exists(self):
        target = self.get_target()
        target_exists = target.exists('valid.csv')
        assert target_exists

        target_exists = target.exists('zzz.csv')
        assert not target_exists



    def test_export_csv(self):
        def mocked_make_export(named_temp_file):
            with open(named_temp_file.name, 'wt') as file:
                writer = csv.writer(file)
                writer.writerow(['header1', 'header2', 'header3'])
                writer.writerow(['data1', 'data2', 'data3'])

        patch("exporter.quotas.make_export", mocked_make_export)
        target = self.get_target()
        target.export_csv('some.csv')
        assert os.path.exists(os.path.join(target._location, 'some.csv'))


@pytest.mark.exporter
class TestSQLiteS3VFSStorage:
    target_class=SQLiteS3VFSStorage

    def get_target(self):
        return self.target_class()

    @patch('exporter.storages.SQLiteS3VFSStorage.listdir', return_value=([],['xxx'],))
    def test_exists(self, mocked_list_dir):
        target = self.get_target()
        assert target.exists('xxx')
        mocked_list_dir.assert_called_once()

    def test_vfs(self):
        target = self.get_target()
        assert type(target.vfs) == sqlite_s3vfs.S3VFS

    @patch("exporter.sqlite.make_export", return_value=mock_make_export)
    def test_export_database(self, patched_make_export):
        class FakeConnection:
            def close(self):
                pass

        with patch("apsw.Connection") as mocked_connection:
            fake_bucket = MagicMock()
            mocked_connection.return_value = FakeConnection()
            target = self.get_target()
            target._bucket = fake_bucket
            target.export_database('valid.file')
            patched_make_export.assert_called_once()


@pytest.mark.exporter
class TestSQLiteS3Storage:
    target_class=SQLiteS3Storage

    def get_target(self):
        return self.target_class()


    @patch("exporter.sqlite.make_export", return_value=mock_make_export)
    @patch("exporter.storages.is_valid_sqlite", return_value=True)
    def test_export_database(self, patched_make_export, patched_is_valid_sqlite):
        class FakeConnection:
            def close(self):
                pass

        with patch("apsw.Connection") as mocked_connection:
            fake_bucket = MagicMock()
            mocked_connection.return_value = FakeConnection()
            target = self.get_target()
            target._bucket = fake_bucket
            target.export_database('valid.file')
            patched_make_export.assert_called_once()

    @patch("exporter.sqlite.make_export", return_value=mock_make_export)
    def test_export_database_zero_file_size(self, patched_make_export):
        class FakeConnection:
            def close(self):
                pass

        with patch("apsw.Connection") as mocked_connection:
            fake_bucket = MagicMock()
            mocked_connection.return_value = FakeConnection()
            target = self.get_target()
            target._bucket = fake_bucket
            with pytest.raises(EmptyFileException) as e:
                target.export_database('valid.file')

            patched_make_export.assert_called_once()

@pytest.mark.exporter
class TestSQLiteLocalStorage:
    target_class = SQLiteLocalStorage

    def get_target(self):
        return self.target_class('exporter/tests/test_files')

    def test_path(self):
        target = self.get_target()
        assert str(target.path('some_file.type')) == str(target._location.joinpath('some_file.type'))

    def test_exists(self):
        target = self.get_target()
        assert not target.exists('dfsgdfg')

    @patch("exporter.sqlite.make_export", return_value=mock_make_export)
    def test_export_database(self, patched_make_export):
        class FakeConnection:
            def close(self):
                pass

        with patch("apsw.Connection") as mocked_connection:
            fake_bucket = MagicMock()
            mocked_connection.return_value = FakeConnection()
            target = self.get_target()
            target._bucket = fake_bucket
            target.export_database('valid.file')
            patched_make_export.assert_called_once()

@pytest.mark.exporter
class TestQuotaS3Storage:
    target_class = QuotaS3Storage

    def get_target(self):
        return self.target_class()

    @patch("exporter.storages.is_valid_quotas_csv", return_value=True)
    def test_export_csv(self, patched_is_valid_quotas_csv):
        def mocked_make_export(named_temp_file):
            with open(named_temp_file.name, 'wt') as file:
                writer = csv.writer(file)
                writer.writerow(['header1', 'header2', 'header3'])
                writer.writerow(['data1', 'data2', 'data3'])

        patch("exporter.quotas.make_export", mocked_make_export)
        target = self.get_target()
        with patch.object(target, 'save') as mock_save:
            mock_save.return_value = None
            target.export_csv('valid.file')
        patched_is_valid_quotas_csv.assert_called_once()
        mock_save.assert_called_once()

    def test_export_csv_invalid(self):
        def mocked_make_export(named_temp_file):
            pass

        with patch("exporter.quotas.make_export", mocked_make_export) as patched_make_export:
            target = self.get_target()
            with pytest.raises(EmptyFileException) as e:
                target.export_csv('valid.file')
            assert 'has zero size.' in str(e.value)






