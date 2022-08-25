import pytest
from django.core.management.base import CommandError

from importer.management.commands import renumber_transactions
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


class TestImportTaricCommand(TestCommandBase):
    TARGET_COMMAND = "renumber_transactions"

    def test_dry_run(self, example_goods_taric_file_location):
        self.call_command_test(f"{example_goods_taric_file_location}", "55")

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: file, number",
            ),
            (
                ["foo"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: number",
            ),
            (
                ["foo", "bar"],
                pytest.raises(CommandError),
                "Error: argument number: invalid int value: 'bar'",
            ),
            (
                ["foo", "7"],
                pytest.raises(FileNotFoundError),
                "No such file or directory",
            ),
        ],
    )
    def test_dry_run_args_errors(self, args, exception_type, error_msg):
        with exception_type as ex:
            self.call_command_test(*args)

        assert error_msg in str(ex.value)

    def test_help(self, capsys):
        get_command_help_text(
            capsys,
            self.TARGET_COMMAND,
            renumber_transactions.Command,
        )

        out = capsys.readouterr().out

        assert "file                  The XML file to renumber, in place" in out
        assert "number                The number to start from" in out
