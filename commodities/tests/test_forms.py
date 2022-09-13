from os import path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from commodities import forms

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")


def test_import_form_valid_envelope_id():
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = forms.CommodityImportForm({}, file_data)

        assert form.is_valid()


@pytest.mark.parametrize("file_name,", ("invalid_id", "dtd"))
@patch("importer.forms.capture_exception")
def test_import_form_invalid_envelope(capture_exception, file_name, settings):
    """Test that form returns generic validation error and sentry captures
    exception when given xml file with invalid id."""
    settings.SENTRY_ENABLED = True
    with open(f"{TEST_FILES_PATH}/{file_name}.xml", "rb") as upload_file:
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        form = forms.CommodityImportForm({}, file_data)

        assert not form.is_valid()

        error_message = "The selected file could not be uploaded - try again"

        assert error_message in form.errors["taric_file"]
        capture_exception.assert_called_once()


def test_import_form_non_xml_file():
    """Test that form returns incorrect file type validation error when passed a
    text file instead of xml."""
    with open(f"{TEST_FILES_PATH}/invalid_type.txt", "rb") as upload_file:
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text",
            ),
        }
        form = forms.CommodityImportForm({}, file_data)

        assert not form.is_valid()
        assert "The selected file must be XML" in form.errors["taric_file"]
