import os
import sys
from datetime import datetime, timezone
from io import StringIO

import pytest
from django.core.management import call_command, CommandParser
from django.core.management.base import DjangoHelpFormatter, BaseCommand, CommandError

import conftest
from importer.management.commands import import_taric

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:

    TARGET_COMMAND = "import_taric"

    def call_command_test(
        self,
        out=None,
        error=None,
        return_error=False,
        *args,
        **kwargs,
    ):
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
        import_taric.Command().print_help(self.TARGET_COMMAND, "")
        print(out.getvalue())
        sys.stdout = sys.__stdout__  # Reset redirect.
        return out.getvalue()

    def test_help_exists(self):
        assert len(import_taric.Command.help) > 0

    def test_dry_run(self, example_goods_taric_file_location):
        out = self.call_command_test(
            None,
            None,
            False,
            f"{example_goods_taric_file_location}",
            "test_name",
        )

        assert out == ""

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, return_error=True)

        assert "Error: the following arguments are required: taric3_file, name" in str(
            ex
        )

    def test_dry_run_error_no_name(self, example_goods_taric_file_location):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(
                None, None, True, f"{example_goods_taric_file_location}"
            )

        assert "Error: the following arguments are required: name" in str(ex)

    def test_dry_run_error_file_not_found(self):
        ex = None
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(None, None, True, f"dfgdfg", "sdfsdfsdf")

        assert "No such file or directory" in str(ex)

    def test_help(self):
        out = self.call_command_help()
        print(out)

        assert "taric3_file name" in out
        assert "Import data from a TARIC XML file into TaMaTo" in out

        assert "taric3_file           The TARIC3 file to be parsed." in out
        assert (
            "name                  The name of the batch, the Envelope ID is recommended."
            in out
        )
        assert "-u USERNAME, --username USERNAME" in out
        assert "The username to use for the owner of the workbaskets" in out
        assert (
            "-S {ARCHIVED,EDITING,PROPOSED,APPROVED,SENT,PUBLISHED,ERRORED}, "
            "--status {ARCHIVED,EDITING,PROPOSED,APPROVED,SENT,PUBLISHED,ERRORED}"
            in out
        )
        assert "The status of the workbaskets containing the import" in out
        assert (
            "-p {SEED_FIRST,SEED_ONLY,REVISION_ONLY}, --partition-scheme {SEED_FIRST,SEED_ONLY,REVISION_ONLY}"
            in out
        )
        assert "Partition to place transactions in approved" in out
        assert "-s, --split-codes     Split the file based on record codes" in out
        assert "-d DEPENDENCIES, --dependencies DEPENDENCIES" in out
        assert "List of batches that need to finish before the current" in out
        assert "-c, --commodities     Only import commodities" in out
