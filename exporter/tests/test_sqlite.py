import tempfile
from io import BytesIO
from os import path
from pathlib import Path
from unittest import mock

import apsw
import pytest

from common.models.transactions import TransactionPartition
from common.tests import factories
from exporter.sqlite import plan
from exporter.sqlite import tasks
from exporter.sqlite.runner import Runner
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def sqlite_template() -> Runner:
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
def sqlite_database(sqlite_template: Runner) -> Runner:
    """Copies the template file to a new location that will be cleaned up at the
    end of one test."""
    in_memory_database = apsw.Connection(":memory:")
    in_memory_database.deserialize("main", sqlite_template.database.serialize("main"))
    yield Runner(in_memory_database)


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
        transaction__workbasket__status=WorkflowStatus.PROPOSED,
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


def test_export_task_does_not_reupload(sqlite_storage, s3_object_names, settings):
    """
    If a file has already been generated for this database state, we don't need
    to upload it again.

    This idempotency allows us to regularly run an export check without
    constantly uploading files and wasting bandwidth/money.
    """
    factories.SeedFileTransactionFactory.create(
        order="999",
    )
    factories.ApprovedTransactionFactory.create(order="123")
    expected_key = path.join(
        settings.SQLITE_STORAGE_DIRECTORY,
        "000000123.db",
        "0" * 10,
    )
    sqlite_storage.save(expected_key, BytesIO(b""))

    names_before = s3_object_names(sqlite_storage.bucket_name)
    with mock.patch("exporter.sqlite.tasks.SQLiteStorage", new=lambda: sqlite_storage):
        returned = tasks.export_and_upload_sqlite()
        assert returned is False

    names_after = s3_object_names(sqlite_storage.bucket_name)
    assert names_before == names_after


def test_export_task_uploads(sqlite_storage, s3_object_names, settings):
    """The export system should actually upload a file to S3."""
    factories.SeedFileTransactionFactory.create(order="999")
    factories.ApprovedTransactionFactory.create(order="123")
    expected_key = path.join(settings.SQLITE_STORAGE_DIRECTORY, "000000123.db")

    with mock.patch("exporter.sqlite.tasks.SQLiteStorage", new=lambda: sqlite_storage):
        returned = tasks.export_and_upload_sqlite()
        assert returned is True

    assert any(
        n.startswith(expected_key) for n in s3_object_names(sqlite_storage.bucket_name)
    )


def test_export_task_ignores_unapproved_transactions(
    sqlite_storage,
    s3_object_names,
    settings,
):
    """Only transactions that have been approved should be included in the
    upload as draft data may be sensitive and unpublished, and shouldn't be
    included."""
    factories.SeedFileTransactionFactory.create(order="999")
    factories.ApprovedTransactionFactory.create(order="123")
    factories.UnapprovedTransactionFactory.create(order="124")
    expected_key = path.join(
        settings.SQLITE_STORAGE_DIRECTORY,
        "000000123.db",
        "0" * 10,
    )
    sqlite_storage.save(expected_key, BytesIO(b""))

    names_before = s3_object_names(sqlite_storage.bucket_name)
    with mock.patch("exporter.sqlite.tasks.SQLiteStorage", new=lambda: sqlite_storage):
        returned = tasks.export_and_upload_sqlite()
        assert returned is False

    names_after = s3_object_names(sqlite_storage.bucket_name)
    assert names_before == names_after
