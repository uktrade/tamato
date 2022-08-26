from os import path
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from importer import forms
from workbaskets.validators import WorkflowStatus

TEST_FILES_PATH = path.join(Path(__file__).parents[2], "commodities/tests/test_files")

pytestmark = pytest.mark.django_db


def test_upload_taric_form_valid_envelope_id():
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        data = {
            "name": "test_upload",
            "status": WorkflowStatus.EDITING,
        }
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = forms.UploadTaricForm(data, file_data)

        assert form.is_valid()


@pytest.mark.parametrize("file_name,", ("invalid_id", "dtd"))
def test_upload_taric_form_invalid_envelope_id(file_name):
    with open(f"{TEST_FILES_PATH}/{file_name}.xml", "rb") as upload_file:
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = forms.UploadTaricForm({}, file_data)

        assert not form.is_valid()
        assert (
            "The selected file could not be uploaded - try again"
            in form.errors["taric_file"]
        )


# https://uktrade.atlassian.net/browse/TP2000-486
# We forgot to add `self` to process_file params and no tests caught it.
@patch("importer.forms.chunk_taric")
@patch("importer.forms.run_batch")
def test_upload_taric_form_save(run_batch, chunk_taric, superuser):
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        data = {
            "name": "test_upload",
            "status": WorkflowStatus.EDITING,
        }
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = forms.UploadTaricForm(data, file_data)
        form.is_valid()
        batch = form.save(user=superuser)

        assert batch.name == "test_upload"
        assert batch.split_job == False

        run_batch.assert_called_once()
        chunk_taric.assert_called_once()
