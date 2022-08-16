import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from importer.management.commands import renumber_taric
from importer.tests.conftest import get_command_help_text

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = "renumber_taric"

    def call_command_test(
        self,
        *args,
        **kwargs,
    ):
        call_command(
            self.TARGET_COMMAND,
            *args,
            **kwargs,
        )

    def test_help_exists(self):
        assert len(renumber_taric.Command.help) > 0

    def test_dry_run(self, capsys, example_goods_taric_file_location):
        self.call_command_test(
            f"{example_goods_taric_file_location}",
            "55",
            "fff",
            "sid",
        )
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_dry_run_error_no_args(self):
        with pytest.raises(CommandError) as ex:
            self.call_command_test()

        assert (
            "Error: the following arguments are required: file, number, record, attribute"
            in str(ex)
        )

    def test_dry_run_error_no_number_record_or_attribute(
        self,
        example_goods_taric_file_location,
    ):
        with pytest.raises(CommandError) as ex:
            self.call_command_test(
                f"{example_goods_taric_file_location}",
            )

        assert (
            "Error: the following arguments are required: number, record, attribute"
            in str(ex)
        )

    def test_dry_run_error_no_record_or_attribute(
        self,
        example_goods_taric_file_location,
    ):
        with pytest.raises(CommandError) as ex:
            self.call_command_test(f"{example_goods_taric_file_location}", "55")

        assert "Error: the following arguments are required: record, attribute" in str(
            ex,
        )

    def test_dry_run_error_no_attribute(self, example_goods_taric_file_location):
        with pytest.raises(CommandError) as ex:
            self.call_command_test(f"{example_goods_taric_file_location}", "55", "f")

        assert "Error: the following arguments are required: attribute" in str(ex)

    def test_dry_run_error_file_not_found(self):
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(f"dfgdfg", "55", "f", "sid")

        assert "No such file or directory" in str(ex)

    def test_help(self, capsys):
        get_command_help_text(capsys, self.TARGET_COMMAND, renumber_taric.Command)

        out = capsys.readouterr().out

        assert "file                  The XML file to renumber, in place" in out
        assert "number                The number to start from" in out
        assert (
            "record                TARIC record name to renumber, with XML namespace"
            in out
        )
        assert (
            "attribute             TARIC record attribute to renumber, with XML namespace"
            in out
        )
