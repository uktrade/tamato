"""
SQLite Export
=============

The SQLite export system will copy the currently attached PostgreSQL database to
a newly created SQLite database and upload the file to an S3 bucket.

The general process is:

1. Create a new, blank SQLite database with the correct schema by running Django
   migrations.
2. Produce an "SQLite script" that copies data into the new database using the
   PostgreSQL COPY feature and the ``psql`` binary.
3. Run the SQLite script using the ``sqlite3`` binary. The binary runs the
   script and streams data directly from ``psql``.
4. Upload the final file to S3.

This process has been chosen to optimise for:

- Minimal overhead on future development: any future changes that are made to
  TaMaTo schemas will be automatically replicated in the SQLite schema.
- Simplicity and speed: the CLI tools are used to avoid having to download and
  allocate memory for objects in Python and then marshall them back out into
  SQLite – instead, the command line tools do all the heavy lifting.

There are a few things that are tricky about doing this. Firstly, SQLite does
not support the full breadth of data types that PostgreSQL does, most notably
date ranges. To account for this, the date range fields are removed when
building the SQLite schema and instead are replaced by simple start and end date
fields, and any other Postgres-specific features are ignored.
"""

from contextlib import redirect_stdout
from io import StringIO
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

from django.apps import apps
from django.conf import settings

from exporter.sqlite import runner
from exporter.sqlite import script


def make_export_script(sqlite: runner.Runner, directory: Path = None):
    directory = directory or Path(TemporaryDirectory().name)

    with script.ImportScript(directory) as import_script:
        names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
        models = chain(*[apps.get_app_config(name).get_models() for name in names])
        for model in models:
            columns = list(sqlite.read_column_order(model._meta.db_table))
            import_script.add_table(model, columns)

    return import_script


def make_export(path: Path):
    sqlite = runner.Runner(path)
    sqlite.make_empty_database()

    with TemporaryDirectory() as tempdir:
        output = StringIO()
        with redirect_stdout(output):
            make_export_script(sqlite, Path(tempdir))
        sqlite.run_sqlite_script(output.getvalue())
