"""
SQLite Export
=============

The SQLite export system will copy the currently attached PostgreSQL database to
a newly created SQLite database and upload the file to an S3 bucket.

The general process is:

1. Create a new, blank SQLite database with the correct schema by running Django
   migrations.
2. Produce a set of operations to copy data into the new database.
3. Run the SQL operations using the ``sqlite3`` library.
4. Upload the final file to S3.

This process has been chosen to optimise for:

- Minimal overhead on future development: any future changes that are made to
  TaMaTo schemas will be automatically replicated in the SQLite schema.

SQLite does not support the full breadth of data types that PostgreSQL does,
most notably date ranges. To account for this, the date range fields are removed
when building the SQLite schema and instead are replaced by simple start and end
date fields, and any other Postgres-specific features are ignored.
"""

from itertools import chain
from pathlib import Path
from tempfile import NamedTemporaryFile

import apsw
from django.apps import apps
from django.conf import settings

from exporter.sqlite import plan
from exporter.sqlite import runner
from exporter.sqlite import tasks  # noqa

SKIPPED_MODELS = {
    "QuotaEvent",
}


def make_export_plan(sqlite_runner: runner.Runner) -> plan.Plan:
    app_names = (
        name.split(".")[0]
        for name in settings.DOMAIN_APPS
        if name not in settings.SQLITE_EXCLUDED_APPS
    )
    all_models = chain(*[apps.get_app_config(name).get_models() for name in app_names])
    models_by_table = {model._meta.db_table: model for model in all_models}

    import_script = plan.Plan()
    for table, create_table_statement in sqlite_runner.tables:
        model = models_by_table.get(table)
        if model is None or model.__name__ in SKIPPED_MODELS:
            continue

        columns = list(sqlite_runner.read_column_order(model._meta.db_table))
        import_script.add_schema(create_table_statement)
        import_script.add_data(model, columns)

    return import_script


def make_export(connection: apsw.Connection):
    with NamedTemporaryFile() as temp_sqlite_db:
        # Create Runner instance with its SQLite file name pointing at a path on
        # the local file system. This is only required temporarily in order to
        # create an in-memory plan that can be run against a target database
        # object.
        plan_runner = runner.Runner.make_tamato_database(
            Path(temp_sqlite_db.name),
        )
        plan = make_export_plan(plan_runner)
        # make_export_plan() creates a Connection instance that needs closing
        # once an in-memory plan has been created from it.
        plan_runner.database.close()

    export_runner = runner.Runner(connection)
    export_runner.run_operations(plan.operations)
