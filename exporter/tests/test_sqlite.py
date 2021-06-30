import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from common.tests import factories
from exporter.sqlite import script
from exporter.sqlite.runner import Runner
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def sqlite_template() -> Path:
    with tempfile.TemporaryDirectory() as f:
        template_db = Path(f) / "template.db"
        Runner(template_db).make_empty_database()
        yield template_db


@pytest.fixture(scope="function")
def sqlite_database(sqlite_template) -> Path:
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
    published = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
    )
    unpublished = factory.create(
        transaction__workbasket__status=WorkflowStatus.AWAITING_APPROVAL,
    )

    table = factory._meta.model._meta.db_table
    run = Runner(sqlite_database)
    ops = script.ImportScript()
    ops.add_table(factory._meta.model, list(run.read_column_order(table)))
    run.run_sqlite_script(ops.operations)

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
    object = factory.create(
        transaction__workbasket__status=WorkflowStatus.PUBLISHED,
        valid_between=getattr(date_ranges, date_range),
    )

    table = factory._meta.model._meta.db_table
    run = Runner(sqlite_database)
    ops = script.ImportScript()
    ops.add_table(factory._meta.model, list(run.read_column_order(table)))
    run.run_sqlite_script(ops.operations)

    conn = sqlite3.connect(sqlite_database)
    validity_start, validity_end = conn.execute(
        f"SELECT validity_start, validity_end FROM {table}",
    ).fetchone()

    assert validity_start == object.valid_between.lower.strftime(r"%Y-%m-%d")
    if object.valid_between.upper:
        assert validity_end == object.valid_between.upper.strftime(r"%Y-%m-%d")
    else:
        assert validity_end is None
