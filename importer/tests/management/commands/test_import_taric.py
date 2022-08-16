from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test.utils import override_settings

from importer.management.commands import import_taric
from importer.tests.conftest import get_command_help_text

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = "import_taric"

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
        assert len(import_taric.Command.help) > 0

    @override_settings(
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_ALWAYS_EAGER=True,
        BROKER_BACKEND="memory",
    )
    def test_dry_run(self, capsys, example_goods_taric_file_location):
        with patch("importer.tasks.import_chunk.delay") as delay_mock:
            self.call_command_test(f"{example_goods_taric_file_location}", "test_name")
            captured = capsys.readouterr()
            assert captured.out == ""
            assert delay_mock.called

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test()

        assert "Error: the following arguments are required: taric3_file, name" in str(
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
        get_command_help_text(capsys, self.TARGET_COMMAND, import_taric.Command)

        out = capsys.readouterr().out

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
