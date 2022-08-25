import pytest
from django.core.management.base import CommandError

from importer.management.commands import filter_taric
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


class TestFilterTaricCommand(TestCommandBase):
    TARGET_COMMAND = "filter_taric"

    def test_dry_run(self, capsys, example_goods_taric_file_location):
        self.call_command_test(
            f"{example_goods_taric_file_location}",
            "test_name",
            "some_values",
        )
        captured = capsys.readouterr()

        assert captured.out == ""

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: file, name, values",
            ),
            (
                ["foo"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: name, values",
            ),
            (
                ["foo", "bar"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: values",
            ),
            (
                ["foo", "bar", "zar"],
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
        get_command_help_text(capsys, self.TARGET_COMMAND, filter_taric.Command)

        out = capsys.readouterr().out

        print(out)

        assert (
            "Removes transactions from the passed TARIC XML tree where the passed tag name\n"
            "is present and has the passed value. For example, calling ``filter_taric(root,\n"
            '"oub:measure.sid", "12345678", "23456789")`` will remove any transaction\n'
            "containing any reference to a measure SID 12345678 or 23456789. This might be\n"
            "the measure itself or it might also include any conditions or components that\n"
            "reference the measure." in out
        )

        assert "file                  The XML file to filter, in place" in out
        assert "name                  The XML tag name to look for" in out
        assert (
            "values                String value that the XML tag should have to be"
            in out
        )
        assert "                        removed" in out
