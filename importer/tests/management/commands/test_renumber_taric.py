import pytest
from django.core.management.base import CommandError

from importer.management.commands import renumber_taric
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


class TestImportTaricCommand(TestCommandBase):
    TARGET_COMMAND = "renumber_taric"

    def test_dry_run(self, capsys, example_goods_taric_file_location):
        self.call_command_test(
            f"{example_goods_taric_file_location}",
            "55",
            "fff",
            "sid",
        )
        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: file, number, record, attribute",
            ),
            (
                ["foo"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: number, record, attribute",
            ),
            (
                ["foo", "bar"],
                pytest.raises(CommandError),
                "Error: argument number: invalid int value: 'bar'",
            ),
            (
                ["foo", "7"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: record, attribute",
            ),
            (
                ["foo", "7", "zar"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: attribute",
            ),
            (
                ["foo", "7", "zar", "par"],
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
