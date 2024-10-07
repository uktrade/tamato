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

import os
import shutil
from itertools import chain
from pathlib import Path
from tempfile import NamedTemporaryFile

import apsw
from django.apps import apps
from django.conf import settings

from exporter.quotas import runner
from exporter.quotas import tasks


def make_export(quotas_csv_named_temp_file: NamedTemporaryFile):
    quota_csv_exporter = runner.QuotaExport(quotas_csv_named_temp_file)
    quota_csv_exporter.run()

