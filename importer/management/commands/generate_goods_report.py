import os
from typing import Any
from typing import Optional
from typing import TextIO

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from importer.goods_report import GoodsReporter
from importer.models import ImportBatch


class Command(BaseCommand):
    help = (
        "Generate a report detailing the goods-related elements in a TARIC3 "
        "standards-compliant XML file. The filename of the generated report "
        "will be taken from the name of the specified ImportBatch instance, "
        "with a file extension to match the output format."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--import-batch-id",
            help=(
                "The primary key ID of ImportBatch instance for which a report "
                "should be generated."
            ),
            type=int,
        )
        group.add_argument(
            "--taric-filepath",
            help=(
                "The file path to a TARIC3 standards-compliant file for which "
                "a report should be generated."
            ),
            type=str,
        )
        parser.add_argument(
            "--output-format",
            help=(
                "Specify the format of the generated report. Default behaviour "
                "is to output a plain text version of the report to stdout."
            ),
            nargs="?",
            choices=("xlsx", "md", "text"),
            default="text",
        )

        parser.add_argument(
            "--output-directory",
            help=(
                "Specify the directory location of the output file (if a "
                "file-type output format has been specified). The current "
                "directory is used by default."
            ),
            type=str,
        )

    def get_output_base_filename(self) -> str:
        """Return the base output filename without any leading path or file
        extension."""
        if self.options.get("import_batch_id"):
            import_batch = ImportBatch.objects.get(
                pk=self.options.get("import_batch_id"),
            )
            return os.path.splitext(import_batch.taric_file.name)[0]
        else:
            taric_filepath = self.options["taric_filepath"]
            return os.path.splitext(os.path.basename(taric_filepath))[0]

    def get_output_directory(self) -> str:
        """Return the file output directory, including trailing slash (/)."""
        directory = self.options.get("output_directory")
        if not directory:
            directory = os.getcwd()
        if directory[-1] != "/":
            directory += "/"
        return directory

    def get_taric_file(self) -> TextIO:
        """Get the taric file from which the report is generated."""
        if self.options.get("import_batch_id"):
            import_batch = ImportBatch.objects.get(
                pk=int(self.options["import_batch_id"]),
            )
            return import_batch.taric_file
        else:
            return open(self.options["taric_filepath"], "r")

    def validate_taric_file_source(self) -> None:
        """
        Validate that this management command has been correctly pointed toward
        a taric file.

        Raises Exception if no valid source file has been provided.
        """
        # There should always be a valid source taric file because
        # --import-batch-id and --taric-filepath are grouped together in a
        # required, XOR group.
        if (
            "import_batch_id" not in self.options
            or "taric_filepath" not in self.options
        ):
            raise Exception("Invalid source input file.")

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        self.options = options

        self.validate_taric_file_source()
        taric_file = self.get_taric_file()
        reporter = GoodsReporter(taric_file)
        goods_report = reporter.create_report()

        output_format = self.options.get("output_format")
        if output_format == "text":
            self.stdout.write(
                goods_report.plaintext(separator=", ", include_column_names=True),
            )
        else:
            directory = self.get_output_directory()
            filename = self.get_output_base_filename()
            if output_format == "xlsx":
                filepath = f"{directory}{filename}.xlsx"
                goods_report.save_xlsx(filepath)
            else:
                filepath = f"{directory}{filename}.md"
                goods_report.save_markdown(filepath)
            self.stdout.write(
                self.style.SUCCESS(f"Generated report file {filepath}"),
            )
