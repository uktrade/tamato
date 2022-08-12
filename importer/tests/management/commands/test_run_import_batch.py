import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from importer.management.commands import run_import_batch
from importer.models import ImportBatch
from importer.tests.conftest import get_command_help_text

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = "run_import_batch"

    def call_command_test(self, *args, **kwargs):
        call_command(
            self.TARGET_COMMAND,
            *args,
            **kwargs,
        )

    def test_help_exists(self):
        assert len(run_import_batch.Command.help) > 0

    def test_dry_run(self, capsys):
        ImportBatch.objects.create(name="55", split_job=False)
        self.call_command_test("55")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_batch_does_not_exist(self):
        with pytest.raises(ImportBatch.DoesNotExist) as ex:
            self.call_command_test("55")

        assert "ImportBatch matching query does not exist." in str(ex)

    def test_dry_run_error_no_args(self):
        with pytest.raises(CommandError) as ex:
            self.call_command_test()

        assert "Error: the following arguments are required: batch" in str(ex)

    def test_help(self, capsys):
        out = get_command_help_text(capsys, self.TARGET_COMMAND)

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
