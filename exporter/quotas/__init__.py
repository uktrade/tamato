"""
quotas Export
=============

The quotas export system will query the TAP database for published quota data and store in a CSV
file.

The general process is:

1. query the TAP database for the correct dataset to export.
2. Iterate the query result and create the data for the output.
3. Write the data to the CSV file
4. Upload the result to the designated storage (S3 or Local)


This process has been chosen to optimise for:

- Speed, query and data production speed will be a lot faster when processed at source.
- Testability, We have the facility to test the output and process within TAP effectively
- Adaptability, With test coverage highlighting any issues caused by database changes etc., the adaptability
if this implementation is high
- Data Quality, Using TAP to produce the data will improve the quality of the output as it's using the same filters
and joins as TAP its self does - removing the need to run queries in SQL which has been problematic, and is
difficult to maintain.
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

def make_export():
    with NamedTemporaryFile() as quotas_csv:
        # Create Runner instance with its SQLite file name pointing at a path on
        # the local file system. This is only required temporarily in order to
        # create an in-memory plan that can be run against a target database
        # object.
        plan_runner = runner.Runner.make_tamato_database(
            Path(temp_sqlite_db.name),
        )
        plan = make_export_plan(plan_runner)
        # Runner.make_tamato_database() (above) creates a Connection instance
        # that needs closing once an in-memory plan has been created from it.
        plan_runner.database.close()

    export_runner = runner.Runner(connection)
    export_runner.run_operations(plan.operations)
