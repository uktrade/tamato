import os
import sys
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from importer.management.commands import run_import_batch
from importer.models import ImportBatch

pytestmark = pytest.mark.django_db


class TestImportTaricCommand:
    TARGET_COMMAND = 'run_import_batch'

    def example_goods_taric_file_location(self):
        cwd = os.getcwd()
        taric_file_location = f'{cwd}/../../test_files/goods.xml'
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
        run_import_batch.Command().print_help(self.TARGET_COMMAND, '')
        print(out.getvalue())
        sys.stdout = sys.__stdout__  # Reset redirect.
        return out.getvalue()

    def test_help_exists(self):
        assert len(run_import_batch.Command.help) > 0

    def test_dry_run(self):
        ImportBatch.objects.create(name='55', split_job=False)
        out = self.call_command_test(None, None, False, "55")

        assert out == ''

    def test_batch_does_not_exist(self):

        ex = None
        with pytest.raises(ImportBatch.DoesNotExist) as ex:
            self.call_command_test(None, None, False, "55")

        assert 'ImportBatch matching query does not exist.' in str(ex)

    def test_dry_run_error_no_args(self):
        ex = None
        with pytest.raises(CommandError) as ex:
            self.call_command_test(None, return_error=True)

        assert 'Error: the following arguments are required: batch' in str(ex)

    def test_help(self):
        out = self.call_command_help()
        print(out)

        assert 'batch                 The batch Id to be imported' in out
        assert '-s {EDITING,PROPOSED,APPROVED,PUBLISHED}, --status {EDITING,PROPOSED,APPROVED,PUBLISHED}' in out
        assert '-p {SEED_FIRST,SEED_ONLY,REVISION_ONLY}, --partition-scheme {SEED_FIRST,SEED_ONLY,REVISION_ONLY}' in out
        assert '-u USERNAME, --username USERNAME' in out
        assert '-C, --commodities     Only import commodities' in out
