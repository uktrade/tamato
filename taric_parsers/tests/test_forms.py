from os import path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from taric_parsers.forms import UploadTaricForm

pytestmark = pytest.mark.django_db

TEST_FILES_PATH = path.join(path.dirname(__file__), "support")


@pytest.mark.importer_v2
def test_upload_taric_form_valid_envelope_id():
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        data = {
            "name": "test_upload",
        }
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = UploadTaricForm(data, file_data)

        assert form.is_valid()


@pytest.mark.importer_v2
@patch("taric_parsers.forms.chunk_taric")
@patch("taric_parsers.forms.run_batch")
def test_upload_taric_form_save(run_batch, chunk_taric, superuser):
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        chunk_taric.return_value = 1

        data = {
            "name": "test_upload",
        }
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = UploadTaricForm(data, file_data)
        form.is_valid()
        batch = form.save(user=superuser)

        assert batch.name == "test_upload"
        assert batch.goods_import is False
        assert batch.split_job is False
        # workbasket will not be created / associated until the background task has been run
        assert batch.workbasket is None

        run_batch.assert_called_once()
        chunk_taric.assert_called_once()
