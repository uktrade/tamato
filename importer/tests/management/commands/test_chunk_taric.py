import os
import sys
import conftest
from datetime import datetime, timezone
from io import StringIO

import pytest
from django.core.management import call_command, CommandParser
from django.core.management.base import DjangoHelpFormatter, BaseCommand, CommandError

from importer.management.commands import chunk_taric
from importer.models import ImportBatch, ImporterXMLChunk, BatchDependencies

pytestmark = pytest.mark.django_db


def test_setup_batch_no_split_no_dependencies():
    batch = chunk_taric.setup_batch('test_batch', False, [])
    assert isinstance(batch, ImportBatch)
    assert batch.split_job is False
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert BatchDependencies.objects.filter(dependent_batch_id=batch.pk).count() == 0


def test_setup_batch_no_split_with_dependencies_creates_dependencies_records():
    batch = chunk_taric.setup_batch('test_batch', False, [])
    batch_with_deps = chunk_taric.setup_batch('test_batch_with_deps', False, ['test_batch'])
    assert isinstance(batch_with_deps, ImportBatch)
    assert batch.split_job is False
    assert batch_with_deps.split_job is False
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert BatchDependencies.objects.filter(dependent_batch_id=batch_with_deps.pk).count() == 1
    assert BatchDependencies.objects.filter(depends_on_id=batch.pk).count() == 1


def test_setup_batch_with_split_no_dependencies():
    batch = chunk_taric.setup_batch('test_batch', True, [])
    assert isinstance(batch, ImportBatch)
    assert batch.split_job is True
    assert ImporterXMLChunk.objects.filter(batch_id=batch.pk).count() == 0
    assert BatchDependencies.objects.filter(dependent_batch_id=batch.pk).count() == 0


class TestChunkTaricCommand:

    TARGET_COMMAND = 'chunk_taric'

    def example_goods_taric_file_location(self):
        taric_file_location = f'{conftest.TEST_CWD}/importer/tests/test_files/goods.xml'
        return taric_file_location

    def call_command_test(self, out=None, error=None, return_error=False, *args, **kwargs, ):
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
        chunk_taric.Command().print_help(self.TARGET_COMMAND, '')
        print(out.getvalue())
        sys.stdout = sys.__stdout__  # Reset redirect.
        return out.getvalue()

    def test_help_exists(self):
        assert len(chunk_taric.Command.help) > 0

    def test_dry_run(self):
        initial_chunk_count = ImporterXMLChunk.objects.count()
        out = self.call_command_test(None, None, False, f"{self.example_goods_taric_file_location()}", "test_name")

        # TODO : Currently the command does not output anything
        # (It will  need to be updated with process info)
        assert out == ''

        # Verify that a chunk was created in the database
        assert ImporterXMLChunk.objects.count() == initial_chunk_count + 1

        # verify the ImporterXMLChunk is attached to a batch
        chunk = ImporterXMLChunk.objects.last()
        assert (datetime.now(timezone.utc) - chunk.created_at).total_seconds() < 10

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, return_error=True)

        assert 'Error: the following arguments are required: taric3_file, name' in str(ex)

    def test_dry_run_error_no_name(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, None, True, f"{self.example_goods_taric_file_location()}")

        assert 'Error: the following arguments are required: name' in str(ex)

    def test_dry_run_error_file_not_found(self):
        ex = None
        with pytest.raises(FileNotFoundError) as ex:
            self.call_command_test(None, None, True, f"dfgdfg", 'sdfsdfsdf')

        assert 'No such file or directory' in str(ex)

    def test_help(self):
        out = self.call_command_help()
        assert 'taric3_file' in out
        assert 'The TARIC3 file to be parsed.' in out

        assert 'name' in out
        assert 'The name of the batch, the Envelope ID is recommended.' in out

        assert '-s, --split-codes' in out
        assert 'Split the file based on record codes' in out

        assert '-d DEPENDENCIES, --dependencies DEPENDENCIES' in out
        assert 'List of batches that need to finish before the current' in out
        assert ' batch can run' in out

        assert '-C, --commodities     Only import commodities' in out
