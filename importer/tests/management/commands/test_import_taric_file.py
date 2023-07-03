from unittest.mock import patch

import pytest
from django.core.management.base import CommandError
from django.test.utils import override_settings

from importer.management.commands import import_taric_file
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


class TestImportTaricFileCommand(TestCommandBase):
    TARGET_COMMAND = "import_taric_file"

    @override_settings(
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_ALWAYS_EAGER=True,
        BROKER_BACKEND="memory",
    )
    def test_dry_run(
        self,
        example_goods_taric_file_location,
        valid_user,
    ):
        with patch(
            "importer.management.commands.import_taric_file.run_batch",
        ) as run_mock:
            self.call_command_test(
                f"{example_goods_taric_file_location}",
                valid_user.email,
            )
            assert run_mock.called

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: taric_file, author",
            ),
            (
                ["foo"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: author",
            ),
            (
                ["foo", "author"],
                pytest.raises(FileNotFoundError),
                "No such file or directory",
            ),
        ],
    )
    def test_dry_run_args_errors(self, args, exception_type, error_msg, valid_user):
        args = [valid_user.email if i == "author" else i for i in args]
        with exception_type as ex:
            self.call_command_test(*args)

        assert error_msg in str(ex.value)

    def test_help(self, capsys):
        get_command_help_text(capsys, self.TARGET_COMMAND, import_taric_file.Command)

        out = capsys.readouterr().out

        assert "taric_file author" in out
        assert "Import data from an EU TARIC XML file into Tamato" in out
        assert "The TARIC3 file to be parsed." in out
        assert "-wid WORKBASKET_ID" in out
        assert "-r RECORD_GROUP" in out
        assert (
            "-S {ARCHIVED,EDITING,QUEUED,PUBLISHED,ERRORED}, "
            "--status {ARCHIVED,EDITING,QUEUED,PUBLISHED,ERRORED}" in out
        )
        assert (
            "-p {SEED_FIRST,SEED_ONLY,REVISION_ONLY}, --partition-scheme {SEED_FIRST,SEED_ONLY,REVISION_ONLY}"
            in out
        )
