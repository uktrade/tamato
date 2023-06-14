from datetime import datetime
from datetime import timezone

import pytest
from bs4 import BeautifulSoup as bs
from django.core.management.base import CommandError

from importer.management.commands import chunk_taric
from importer.models import BatchDependencies
from importer.models import ImportBatch
from importer.models import ImporterXMLChunk
from importer.tests.conftest import get_command_help_text
from importer.tests.management.commands.base import TestCommandBase

pytestmark = pytest.mark.django_db


def test_setup_batch_no_split_no_dependencies(valid_user):
    batch = chunk_taric.setup_batch("test_batch", False, [], valid_user)
    assert isinstance(batch, ImportBatch)
    assert batch.split_job is False
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert BatchDependencies.objects.filter(dependent_batch_id=batch.pk).count() == 0


def test_setup_batch_no_split_with_dependencies_creates_dependencies_records(
    valid_user,
):
    batch = chunk_taric.setup_batch("test_batch", False, [], valid_user)
    batch_with_deps = chunk_taric.setup_batch(
        "test_batch_with_deps",
        False,
        ["test_batch"],
        valid_user,
    )
    assert isinstance(batch_with_deps, ImportBatch)
    assert batch.split_job is False
    assert batch_with_deps.split_job is False
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert (
        BatchDependencies.objects.filter(dependent_batch_id=batch_with_deps.pk).count()
        == 1
    )
    assert BatchDependencies.objects.filter(depends_on_id=batch.pk).count() == 1


def test_setup_batch_with_split_no_dependencies(valid_user):
    batch = chunk_taric.setup_batch("test_batch", True, [], valid_user)
    assert isinstance(batch, ImportBatch)
    assert batch.split_job is True
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert BatchDependencies.objects.filter(dependent_batch_id=batch.pk).count() == 0


class TestChunkTaricCommand(TestCommandBase):
    TARGET_COMMAND = "chunk_taric"

    def test_dry_run(self, capsys, example_goods_taric_file_location, valid_user):
        initial_chunk_count = ImporterXMLChunk.objects.count()
        self.call_command_test(
            taric3_file=f"{example_goods_taric_file_location}",
            batch_name="test_name",
            author=valid_user,
        )

        # TODO : Currently the command does not output anything
        # (It will need to be updated with process info)
        captured = capsys.readouterr()
        assert captured.out == ""

        # Verify that a chunk was created in the database
        assert ImporterXMLChunk.objects.count() == initial_chunk_count + 1

        # verify the ImporterXMLChunk is attached to a batch
        chunk = ImporterXMLChunk.objects.last()
        assert (datetime.now(timezone.utc) - chunk.created_at).total_seconds() < 10

        actual_bs = bs(chunk.chunk_text, "xml")
        expected_bs = bs(open(example_goods_taric_file_location).read(), "xml")

        # test that the XML inside the chunk matches the imported data
        assert len(actual_bs.find_all("transaction")) == len(
            expected_bs.find_all("transaction"),
        )
        assert len(actual_bs.find_all("transaction")[0]["id"]) == len(
            expected_bs.find_all("transaction")[0]["id"],
        )
        assert len(actual_bs.find_all("envelope")) == len(
            expected_bs.find_all("envelope"),
        )
        assert len(actual_bs.find_all("envelope")[0]["id"]) == len(
            expected_bs.find_all("envelope")[0]["id"],
        )

    @pytest.mark.parametrize(
        "args,exception_type,error_msg",
        [
            (
                [],
                pytest.raises(CommandError),
                "Error: the following arguments are required: taric3_file, batch_name, author",
            ),
            (
                ["foo"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: batch_name, author",
            ),
            (
                ["foo", "bar"],
                pytest.raises(CommandError),
                "Error: the following arguments are required: batch_name, author",
            ),
            (
                ["foo", "bar", valid_user],
                pytest.raises(FileNotFoundError),
                "No such file or directory",
            ),
        ],
    )
    def test_dry_run_args_errors(self, args, exception_type, error_msg, valid_user):
        with exception_type as ex:
            self.call_command_test(*args)

        assert error_msg in str(ex.value)

    def test_help(self, capsys):
        get_command_help_text(
            capsys,
            self.TARGET_COMMAND,
            eval(self.TARGET_COMMAND).Command,
        )

        out = capsys.readouterr().out

        assert "taric3_file" in out
        assert "The TARIC3 file to be parsed." in out

        assert "name" in out
        assert "The name of the batch, the Envelope ID is recommended." in out

        assert "-s, --split-codes" in out
        assert "Split the file based on record codes" in out

        assert "-d DEPENDENCIES, --dependencies DEPENDENCIES" in out
        assert "List of batches that need to finish before the current" in out
        assert " batch can run" in out

        assert "-C, --commodities     Only import commodities" in out
