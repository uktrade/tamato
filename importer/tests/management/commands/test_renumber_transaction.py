import os
import sys
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

import conftest
from importer.management.commands import renumber_transactions

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = 'renumber_transactions'

    def example_goods_taric_file_location(self):
        taric_file_location = f'{conftest.TEST_CWD}/importer/tests/test_files/goods.xml'
        return taric_file_location

    def call_command_test(self, out=None, error=None, return_error=False, *args, **kwargs):
        if out is None:
            out = StringIO()

        if error is None:
            error = StringIO()

        call_command(
            self.TARGET_COMMAND,
            *args,
            stdout=out,
            stderr=error,
            **kwargs,
        )
        if return_error:
            return error.getvalue()

        return out.getvalue()

    def call_command_help(self):
        out = StringIO()
        sys.stdout = out
        renumber_transactions.Command().print_help(self.TARGET_COMMAND, '')
        print(out.getvalue())
        sys.stdout = sys.__stdout__  # Reset redirect.
        return out.getvalue()

    def test_help_exists(self):
        assert len(renumber_transactions.Command.help) > 0

    def test_dry_run(self):
        out = self.call_command_test(None, None, False, f"{self.example_goods_taric_file_location()}", "55")

        assert out == ''

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, return_error=True)

        assert 'Error: the following arguments are required: file, number' in str(ex)

    def test_dry_run_error_no_number(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, None, True, f"{self.example_goods_taric_file_location()}")

        assert 'Error: the following arguments are required: number' in str(ex)

    def test_dry_run_error_file_not_found(self):
        ex = None
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(None, None, True, f"dfgdfg", '55')

        assert 'No such file or directory' in str(ex)

    def test_help(self):
        out = self.call_command_help()
        print(out)

        assert 'file                  The XML file to renumber, in place' in out
        assert 'number                The number to start from' in out
