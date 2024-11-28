import logging
import os
import shutil
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile

from exporter.quotas import runner
from exporter.report_exporter.commodities_runner import CommodityCodeExport
from exporter.report_exporter.storage import QuotasExportS3StorageBase
from exporter.report_exporter.storage import ReportsExportS3StorageBase

logger = logging.getLogger(__name__)


class EmptyFileException(Exception):
    pass


class ReportExporter:
    s3_storage: ReportsExportS3StorageBase = None

    # To be defined by the different report exporter
    def make_export(self, filename: NamedTemporaryFile):
        pass

    def __init__(self, location="", save_locally=True) -> None:
        self._save_locally = save_locally
        if self._save_locally and location == "":
            raise Exception(f"Request to save locally, but filename not specified.")

        if location:
            self._location = Path(location).expanduser().resolve()
            logger.info(f"Normalised path `{location}` to `{self._location}`.")
            if not self._location.is_dir():
                raise Exception(f"Directory does not exist: {location}.")

    def exists(self, name: str) -> bool:
        if self._save_locally:
            return Path(self.path(name)).exists()
        else:
            pass

    def is_valid_export_csv(self, filename: str):
        """
        `file_path` should be a path to a file on the local file system.
        Validation.

        includes:
        - test that a file exists at `file_path`,
        - test that the file at `file_path` has non-zero size,

        If errors are found during validation, then exceptions that this function
        may raise include:
            - FileNotFoundError if no file was found at `file_path`.
            - exporter.storage.EmptyFileException if the file at `file_path` has
              zero size.

        Returns True if validation checks all pass.
        """

        if path.getsize(filename) == 0:
            raise EmptyFileException(f"{filename} has zero size.")

        return True

    def export_csv(self, filename: str):
        with NamedTemporaryFile() as named_temp_file:
            logger.info(f"Saving {filename} to local file system storage.")
            self.make_export(named_temp_file)
            if self.is_valid_export_csv(named_temp_file.name):
                # Only save to S3 if the CSV file is valid.

                if self._save_locally:
                    destination_file_path = os.path.join(self._location, filename)
                    shutil.copy(named_temp_file.name, destination_file_path)
                else:
                    self.S3Boto3Storage.save(named_temp_file)
                    os.unlink(named_temp_file.name)


class QuotaReportExporter(ReportExporter):
    s3_storage = QuotasExportS3StorageBase

    def make_export(self, filename):
        quota_csv_exporter = runner.QuotaExport(filename)
        quota_csv_exporter.run()


class CommoditiesReportExporter(ReportExporter):

    s3_storage = QuotasExportS3StorageBase

    def make_export(self, filename):
        CommodityCodeExport(filename.run())
