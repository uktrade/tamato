import pytest
from django.core.management.base import CommandError

from importer.management.commands import run_import_batch
from importer.models import ImportBatch
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


class TestImportTaricCommand(TestCommandBase):
    TARGET_COMMAND = "run_import_batch"

    def test_dry_run(self, capsys):
        ImportBatch.objects.create(name="55", split_job=False)
        self.call_command_test("55")
        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: batch",
            ),
            (
                ["55"],
                pytest.raises(ImportBatch.DoesNotExist),
                "ImportBatch matching query does not exist.",
            ),
        ],
    )
    def test_dry_run_args_errors(self, args, exception_type, error_msg):
        with exception_type as ex:
            self.call_command_test(*args)

        assert error_msg in str(ex.value)

    def test_help(self, capsys):
        get_command_help_text(capsys, self.TARGET_COMMAND, run_import_batch.Command)

        out = capsys.readouterr().out

        assert "batch                 The batch Id to be imported" in out
        assert (
            "-s {EDITING,PROPOSED,APPROVED,PUBLISHED}, --status {EDITING,PROPOSED,APPROVED,PUBLISHED}"
            in out
        )
        assert (
            "-p {SEED_FIRST,SEED_ONLY,REVISION_ONLY}, --partition-scheme {SEED_FIRST,SEED_ONLY,REVISION_ONLY}"
            in out
        )
        assert "-u USERNAME, --username USERNAME" in out
        assert "-C, --commodities     Only import commodities" in out
