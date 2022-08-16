import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from importer.management.commands import renumber_transactions
from importer.tests.conftest import get_command_help_text

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = "renumber_transactions"

    def call_command_test(self, *args, **kwargs):
        call_command(
            self.TARGET_COMMAND,
            *args,
            **kwargs,
        )

    def test_help_exists(self):
        assert len(renumber_transactions.Command.help) > 0

    def test_dry_run(self, example_goods_taric_file_location):
        self.call_command_test(f"{example_goods_taric_file_location}", "55")

    def test_dry_run_error_no_args(self):
        with pytest.raises(CommandError) as ex:
            self.call_command_test()

        assert "Error: the following arguments are required: file, number" in str(ex)

    def test_dry_run_error_no_number(self, example_goods_taric_file_location):
        with pytest.raises(CommandError) as ex:
            self.call_command_test(f"{example_goods_taric_file_location}")

        assert "Error: the following arguments are required: number" in str(ex)

    def test_dry_run_error_file_not_found(self):
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(f"dfgdfg", "55")

        assert "No such file or directory" in str(ex)

    def test_help(self, capsys):
        get_command_help_text(capsys, self.TARGET_COMMAND, renumber_transactions.Command)

        out = capsys.readouterr().out

        assert "file                  The XML file to renumber, in place" in out
        assert "number                The number to start from" in out
