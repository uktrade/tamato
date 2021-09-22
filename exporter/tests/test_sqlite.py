import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from common.tests import factories
from exporter.sqlite import plan
from exporter.sqlite import tasks
from exporter.sqlite.runner import Runner
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def sqlite_template() -> Path:
    """
    Provides a template SQLite file with the correct TaMaTo schema but without
    any data.

    This makes tests quicker because it skips the (slow) step of applying
    migrations to create a new db. This file lasts for as long as all of the
    tests in this module are executing and is then cleaned up.
    """
    with tempfile.TemporaryDirectory() as f:
        template_db = Path(f) / "template.db"
        Runner(template_db).make_empty_database()
        yield template_db


@pytest.fixture(scope="function")
def sqlite_database(sqlite_template) -> Path:
    """Copies the template file to a new location that will be cleaned up at the
    end of one test."""
    with tempfile.TemporaryDirectory() as f:
        test_path = Path(f) / "test.db"
        shutil.copyfile(sqlite_template, test_path)
        yield test_path


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
def test_table_export(factory, sqlite_database: Path):
    """Check that it's possible to export each table that we want in the
    output."""
    published = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
    )
    unpublished = factory.create(
        transaction__workbasket__status=WorkflowStatus.PROPOSED,
    )

    table = factory._meta.model._meta.db_table
    run = Runner(sqlite_database)
    ops = plan.Plan()
    ops.add_table(factory._meta.model, list(run.read_column_order(table)))
    run.run_operations(ops.operations)

    conn = sqlite3.connect(sqlite_database)
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
def test_valid_between_export(factory, date_ranges, date_range, sqlite_database: Path):
    """Check that the exported date range columns contain the correct values."""
    object = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
        valid_between=getattr(date_ranges, date_range),
    )

    table = factory._meta.model._meta.db_table
    run = Runner(sqlite_database)
    ops = plan.Plan()
    ops.add_table(factory._meta.model, list(run.read_column_order(table)))
    run.run_operations(ops.operations)

    conn = sqlite3.connect(sqlite_database)
    validity_start, validity_end = conn.execute(
        f"SELECT validity_start, validity_end FROM {table}",
    ).fetchone()

    assert validity_start == object.valid_between.lower.strftime(r"%Y-%m-%d")
    if object.valid_between.upper:
        assert validity_end == object.valid_between.upper.strftime(r"%Y-%m-%d")
    else:
        assert validity_end is None


def test_export_task_does_not_reupload():
    """
    If a file has already been generated for this database state, we don't need
    to upload it again.

    This idempotency allows us to regularly run an export check without
    constantly uploading files and wasting bandwidth/money.
    """
    factories.ApprovedTransactionFactory.create(order="999")  # seed file
    factories.ApprovedTransactionFactory.create(order="123")

    with mock.patch(
        "exporter.sqlite.tasks.SQLiteStorage",
        autospec=True,
    ) as mock_storage:
        mock_storage.return_value.exists.return_value = True

        returned = tasks.export_and_upload_sqlite()

        assert returned is False
        mock_storage.return_value.generate_filename.assert_called_once_with(
            "sqlite/000000123.db",
        )
        mock_storage.return_value.save.assert_not_called()


def test_export_task_uploads(
    sqlite_storage,
    s3_bucket_names,
    s3_object_names,
    settings,
):
    """The export system should actually upload a file to S3."""

    expected_bucket = "sqlite"
    expected_key = "sqlite/000000123.db"
    settings.SQLITE_STORAGE_BUCKET_NAME = expected_bucket

    factories.ApprovedTransactionFactory.create(order="999")  # seed file
    factories.ApprovedTransactionFactory.create(order="123")

    with mock.patch(
        "exporter.storages.SQLiteStorage.save",
        wraps=mock.MagicMock(
            side_effect=sqlite_storage.save,
        ),
    ) as mock_save:
        returned = tasks.export_and_upload_sqlite()

        assert returned is True
        mock_save.assert_called_once()

    assert expected_bucket in s3_bucket_names()
    assert expected_key in s3_object_names(expected_bucket)


def test_export_task_ignores_unapproved_transactions():
    """Only transactions that have been approved should be included in the
    upload as draft data may be sensitive and unpublished, and shouldn't be
    included."""
    factories.ApprovedTransactionFactory.create(order="999")  # seed file
    factories.ApprovedTransactionFactory.create(order="123")
    factories.UnapprovedTransactionFactory.create(order="124")

    with mock.patch("exporter.sqlite.tasks.SQLiteStorage") as mock_storage:
        mock_storage.return_value.exists.return_value = True

        tasks.export_and_upload_sqlite()

        mock_storage.return_value.generate_filename.assert_called_once_with(
            "sqlite/000000123.db",
        )
        mock_storage.return_value.save.assert_not_called()
