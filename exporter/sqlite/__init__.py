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

from django.apps import apps
from django.conf import settings

from exporter.sqlite import plan
from exporter.sqlite import runner
from exporter.sqlite import tasks  # noqa


def make_export_plan(sqlite: runner.Runner) -> plan.Plan:
    import_script = plan.Plan()
    names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
    models = chain(*[apps.get_app_config(name).get_models() for name in names])
    for model in models:
        if model.__name__ == "QuotaEvent":
            continue
        columns = list(sqlite.read_column_order(model._meta.db_table))
        import_script.add_table(model, columns)

    return import_script


def make_export() -> bytes:
    sqlite = runner.Runner.from_empty_database()
    plan = make_export_plan(sqlite)
    sqlite.run_operations(plan.operations)
    return sqlite.get_bytes()
