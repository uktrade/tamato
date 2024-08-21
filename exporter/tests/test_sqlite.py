import sqlite3
import tempfile
from io import BytesIO
from os import path
from pathlib import Path
from typing import Iterator
from unittest import mock

import apsw
import pytest

from common.models.transactions import TransactionPartition
from common.tests import factories
from exporter.sqlite import plan
from exporter.sqlite import tasks
from exporter.sqlite.runner import Runner
from exporter.sqlite.runner import SQLiteMigrator
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def sqlite_template() -> Iterator[Runner]:
    """
    Provides a template SQLite file with the correct TaMaTo schema but without
    any data.

    This makes tests quicker because it skips the (slow) step of applying
    migrations to create a new db. This file lasts for as long as all of the
    tests in this module are executing and is then cleaned up.
    """
    with tempfile.TemporaryDirectory() as f:
        template_db = Path(f) / "template.db"
        yield Runner.make_tamato_database(template_db)


@pytest.fixture(scope="function")
def sqlite_database(sqlite_template: Runner) -> Iterator[Runner]:
    """Copies the template file to a new location that will be cleaned up at the
    end of one test."""
    in_memory_database = apsw.Connection(":memory:")
    in_memory_database.deserialize("main", sqlite_template.database.serialize("main"))
    yield Runner(in_memory_database)


@pytest.mark.parametrize(
    ("migrations_in_tmp_dir"),
    (False, True),
)
def test_sqlite_migrator(migrations_in_tmp_dir):
    """Test SQLiteMigrator."""
    with tempfile.NamedTemporaryFile() as sqlite_file:
        sqlite_migrator = SQLiteMigrator(
            sqlite_file=Path(sqlite_file.name),
            migrations_in_tmp_dir=migrations_in_tmp_dir,
        )
        sqlite_migrator.migrate()

        connection = sqlite3.connect(sqlite_file.name)
        cursor = connection.cursor()
        # Executing "PRAGMA quick_check" raises DatabaseError if the generated
        # database file is invalid, failing this test.
        cursor.execute("PRAGMA quick_check")


FACTORIES_EXPORTED = [
    factory
    for factory in factories.TrackedModelMixin.__subclasses__()
    if factory
    not in (
        factories.QuotaEventFactory,
        factories.TestModel1Factory,
        factories.TestModel2Factory,
        factories.TestModel3Factory,
        factories.TestModelDescription1Factory,
    )
]


@pytest.mark.parametrize(
    ("factory"),
    FACTORIES_EXPORTED,
    ids=(f._meta.model.__name__ for f in FACTORIES_EXPORTED),
)
def test_table_export(factory, sqlite_database: Runner):
    """Check that it's possible to export each table that we want in the
    output."""
    published = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
    )
    unpublished = factory.create(
        transaction__workbasket__status=WorkflowStatus.EDITING,
        transaction__partition=TransactionPartition.DRAFT,
    )

    table = factory._meta.model._meta.db_table
    run = sqlite_database
    ops = plan.Plan()
    ops.add_data(factory._meta.model, list(run.read_column_order(table)))
    run.run_operations(ops.operations)

    conn = run.database.cursor()
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()

    assert len(rows) == 1
    assert published.id == rows[0][0]


VALIDITY_FACTORIES_EXPORTED = [
    factory
    for factory in FACTORIES_EXPORTED
    if issubclass(factory, factories.ValidityFactoryMixin)
]


@pytest.mark.parametrize(
    ("factory"),
    VALIDITY_FACTORIES_EXPORTED,
    ids=(f._meta.model.__name__ for f in VALIDITY_FACTORIES_EXPORTED),
)
@pytest.mark.parametrize(
    ("date_range"),
    ("no_end", "normal"),
)
def test_valid_between_export(
    factory,
    date_ranges,
    date_range,
    sqlite_database: Runner,
):
    """Check that the exported date range columns contain the correct values."""
    object = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
        valid_between=getattr(date_ranges, date_range),
    )

    table = factory._meta.model._meta.db_table
    run = sqlite_database
    ops = plan.Plan()
    ops.add_data(factory._meta.model, list(run.read_column_order(table)))
    run.run_operations(ops.operations)

    conn = run.database.cursor()
    validity_start, validity_end = conn.execute(
        f"SELECT validity_start, validity_end FROM {table}",
    ).fetchone()

    assert validity_start == object.valid_between.lower.strftime(r"%Y-%m-%d")
    if object.valid_between.upper:
        assert validity_end == object.valid_between.upper.strftime(r"%Y-%m-%d")
    else:
        assert validity_end is None


def test_s3_export_task_does_not_reupload(sqlite_storage, s3_object_names, settings):
    """
    If a file has already been generated and uploaded to S3 for this database
    state, we don't need to upload it again.

    This idempotency allows us to regularly run an export check without
    constantly uploading files and wasting bandwidth/money.
    """
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create()

    expected_key = path.join(
        settings.SQLITE_STORAGE_DIRECTORY,
        f"{tasks.normalised_order(transaction.order)}.db",
        "0" * 10,
    )
    sqlite_storage.save(expected_key, BytesIO(b""))

    names_before = s3_object_names(sqlite_storage.bucket_name)
    with mock.patch(
        "exporter.sqlite.tasks.storages.SQLiteS3Storage",
        new=lambda: sqlite_storage,
    ):
        returned = tasks.export_and_upload_sqlite()
        assert returned is False

    names_after = s3_object_names(sqlite_storage.bucket_name)
    assert names_before == names_after


def test_local_export_task_does_not_replace(tmp_path):
    """Test that if an SQLite file has already been generated on the local file
    system at a specific directory location for this database state, then no
    attempt is made to create it again."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create()

    sqlite_file_path = tmp_path / f"{tasks.normalised_order(transaction.order)}.db"
    sqlite_file_path.write_bytes(b"")
    files_before = set(tmp_path.iterdir())

    assert not tasks.export_and_upload_sqlite(tmp_path)
    assert files_before == set(tmp_path.iterdir())


def test_s3_export_task_uploads(sqlite_storage, s3_object_names, settings):
    """The export system should actually upload a file to S3."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create()

    expected_key = path.join(
        settings.SQLITE_STORAGE_DIRECTORY,
        f"{tasks.normalised_order(transaction.order)}.db",
    )

    with mock.patch(
        "exporter.sqlite.tasks.storages.SQLiteS3Storage",
        new=lambda: sqlite_storage,
    ):
        returned = tasks.export_and_upload_sqlite()
        assert returned is True

    assert any(
        n.startswith(expected_key) for n in s3_object_names(sqlite_storage.bucket_name)
    )


def test_local_export_task_saves(tmp_path):
    """Test that export correctly saves a file to the local file system."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create()

    sqlite_file_path = tmp_path / f"{tasks.normalised_order(transaction.order)}.db"
    files_before = set(tmp_path.iterdir())

    assert tasks.export_and_upload_sqlite(tmp_path)
    assert files_before | {sqlite_file_path} == set(tmp_path.iterdir())


def test_s3_export_task_ignores_unpublished_and_unapproved_transactions(
    sqlite_storage,
    s3_object_names,
    settings,
):
    """Only transactions that have been published should be included in the
    upload as draft and queued data may be sensitive and unpublished, and should
    therefore not be included."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create(order="123")
    factories.ApprovedTransactionFactory.create(order="124")
    factories.UnapprovedTransactionFactory.create(order="125")

    expected_key = path.join(
        settings.SQLITE_STORAGE_DIRECTORY,
        f"{tasks.normalised_order(transaction.order)}.db",
        "0" * 10,
    )
    sqlite_storage.save(expected_key, BytesIO(b""))

    names_before = s3_object_names(sqlite_storage.bucket_name)
    with mock.patch(
        "exporter.sqlite.tasks.storages.SQLiteS3Storage",
        new=lambda: sqlite_storage,
    ):
        returned = tasks.export_and_upload_sqlite()
        assert returned is False

    names_after = s3_object_names(sqlite_storage.bucket_name)
    assert names_before == names_after


def test_local_export_task_ignores_unpublished_and_unapproved_transactions(tmp_path):
    """Only transactions that have been published should be included in the
    upload as draft and queued data may be sensitive and unpublished, and should
    therefore not be included."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create(order="123")
    factories.ApprovedTransactionFactory.create(order="124")
    factories.UnapprovedTransactionFactory.create(order="125")

    sqlite_file_path = tmp_path / f"{tasks.normalised_order(transaction.order)}.db"
    files_before = set(tmp_path.iterdir())

    assert tasks.export_and_upload_sqlite(tmp_path)
    assert files_before | {sqlite_file_path} == set(tmp_path.iterdir())
