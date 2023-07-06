from typing import Any
from typing import Optional

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

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        if options.get("import_batch_id"):
            import_batch = ImportBatch.objects.get(
                pk=int(options["import_batch_id"]),
            ).taric_file
            taric_file = import_batch.taric_file
            self.stdout.write(
                f"Generating report for {repr(import_batch)}...",
            )
        else:
            taric_file = open(options["taric_filepath"], "r")
            self.stdout.write(
                f"Generating report for {taric_file.name}...",
            )

        reporter = GoodsReporter(taric_file)
        goods_report = reporter.create_report()

        # print("*** goods_report.report_lines")
        output_format = options.get("output_format")
        if output_format == "text":
            self.stdout.write(
                goods_report.plaintext(separator=", ", include_column_names=True),
            )
        elif output_format == "md":
            self.stdout.write("TODO")
        elif output_format == "xlsx":
            self.stdout.write("TODO")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated report file {taric_file.name}.xlsx.",
                ),
            )
