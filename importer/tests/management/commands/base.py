from abc import ABC

import pytest
from django.core.management import call_command

from importer.management.commands import chunk_taric  # noqa
from importer.management.commands import filter_taric  # noqa
from importer.management.commands import import_taric  # noqa
from importer.management.commands import renumber_taric  # noqa
from importer.management.commands import renumber_transactions  # noqa
from importer.management.commands import run_import_batch  # noqa


class TestCommandBase(ABC):
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

    def get_help(self, command_module):
        """Retrieves the help for a specific command module."""
        return command_module.Command.help

    def get_help_count(self, command_module):
        """Retrieves the count of help elements for a specific command
        module."""
        return len(self.get_help(command_module))

    def test_help_exists(self):
        try:
            self.TARGET_COMMAND
        except AttributeError:
            pytest.skip(
                "Skipping since base class does nopt have TARGET_COMMAND defined",
            )

        assert self.get_help_count(eval(self.TARGET_COMMAND)) > 0
