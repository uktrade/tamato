import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from importer.management.commands import filter_taric
from importer.tests.conftest import get_command_help_text

pytestmark = pytest.mark.django_db


class TestFilterTaricCommand:
    TARGET_COMMAND = "filter_taric"

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
        assert len(filter_taric.Command.help) > 0

    def test_dry_run(self, capsys, example_goods_taric_file_location):
        self.call_command_test(
            f"{example_goods_taric_file_location}",
            "test_name",
            "some_values",
        )
        captured = capsys.readouterr()

        assert captured.out == ""

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test()

        assert "Error: the following arguments are required: file, name, values" in str(
            ex,
        )

    def test_dry_run_error_no_name(self, example_goods_taric_file_location):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(f"{example_goods_taric_file_location}")

        assert "Error: the following arguments are required: name" in str(ex)

    def test_dry_run_error_file_not_found(self):
        ex = None
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(f"dfgdfg", "sdfsdfsdf")

        assert "No such file or directory" in str(ex)

    def test_help(self, capsys):
        out = get_command_help_text(capsys, self.TARGET_COMMAND)

        assert (
            "file name [values [values ...]]\n\n"
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
