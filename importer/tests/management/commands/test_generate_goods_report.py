import os
from os import path
from unittest.mock import mock_open
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

TEST_FILES_PATH = path.join(
    path.dirname(path.dirname(path.dirname(__file__))),
    "test_files",
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "args, exception_type, error_msg",
    [
        (
            [""],
            CommandError,
            "Error: one of the arguments --import-batch-id --taric-filepath is required",
        ),
        (
            ["--import-batch-id", "1234"],
            CommandError,
            "No ImportBatch instance found with pk=1234",
        ),
        (
            ["--taric-filepath", "foo"],
            FileNotFoundError,
            "No such file or directory: 'foo'",
        ),
    ],
)
def test_generate_goods_report_required_arguments(args, exception_type, error_msg):
    """Test that `generate_goods_report` command raises errors when invalid
    arguments are provided."""
    with pytest.raises(exception_type, match=error_msg):
        call_command("generate_goods_report", *args)


@pytest.mark.parametrize(
    "output_format, mock_output",
    [
        (
            "csv",
            "importer.goods_report.GoodsReport.csv",
        ),
        (
            "md",
            "importer.goods_report.GoodsReport.markdown",
        ),
    ],
)
def test_generate_goods_report_output_format(output_format, mock_output):
    """Test that `generate_goods_report` command generates a report in the
    output format specified in the argument."""
    with patch(mock_output, return_value="") as mock:
        call_command(
            "generate_goods_report",
            "--taric-filepath",
            f"{TEST_FILES_PATH}/goods.xml",
            "--output-format",
            output_format,
        )
        mock.assert_called_once()


def test_generate_goods_report_output_xlsx_file():
    """Test that `generate_goods_report` command generates a report in the xlsx-
    file output format."""

    def mock_xlsx_open(filename, mode):
        if os.path.basename(filename) == "goods.xlsx":
            return mock_open().return_value
        return open(filename, mode)

    with patch(
        "importer.goods_report.GoodsReport.xlsx_file",
        return_value="",
    ) as mocked_xlsx_file:
        with patch(
            "importer.management.commands.generate_goods_report.open",
            mock_xlsx_open,
        ):
            call_command(
                "generate_goods_report",
                "--taric-filepath",
                f"{TEST_FILES_PATH}/goods.xml",
                "--output-format",
                "xlsx-file",
            )
            mocked_xlsx_file.assert_called_once()
