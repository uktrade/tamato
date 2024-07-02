import re
from io import StringIO

import pytest
from django.core.management import call_command

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_importer_list():
    import_batches = factories.ImportBatchFactory.create_batch(2)

    out = StringIO()
    call_command("importer", "list", "--number", "20", stdout=out)
    output = out.getvalue()

    # Ensure --number flag has been correctly parsed.
    assert "Showing a maximum of 20 most recent ImportBatch instances" in output
    # Check that all imports are reported in the output.
    for import_batch in import_batches:
        assert str(import_batch.pk) in output


def test_importer_inspect(importing_goods_import_batch):
    out = StringIO()
    call_command(
        "importer",
        "inspect",
        f"{importing_goods_import_batch.pk}",
        stdout=out,
    )
    output_lines = out.getvalue().splitlines()

    assert "ImportBatch details" in output_lines[0]

    def get_value_from_line_name(output_lines, line_name):
        """
        The importer command's output lines are generally of the form:

        code-block::
            Name:     value

        This method returns the value of a line's value given its name, if the
        name is found amongst output_lines, else None.
        """
        matched_line = next(l for l in output_lines if l.startswith(line_name))
        tokens = re.split(r"\W+", matched_line)
        return tokens[1] if tokens and len(tokens) > 1 else None

    assert str(importing_goods_import_batch.pk) == get_value_from_line_name(
        output_lines,
        "PK",
    )
    assert importing_goods_import_batch.status == get_value_from_line_name(
        output_lines,
        "Status",
    )
