from os import path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest

from importer import forms
from workbaskets.validators import WorkflowStatus

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
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


@pytest.mark.importer_v2
@pytest.mark.parametrize("file_name,", ("invalid_id", "dtd"))
@patch("importer.forms.capture_exception")
def test_upload_taric_form_invalid_envelope(capture_exception, file_name, settings):
    """Test that form returns generic validation error and sentry captures
    xception when given xml file with invalid id or document type
    declaration."""
    settings.SENTRY_ENABLED = True
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
        capture_exception.assert_called_once()


@pytest.mark.importer_v2
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
        form = forms.UploadTaricForm({}, file_data)

        assert not form.is_valid()
        assert "The selected file must be XML" in form.errors["taric_file"]


# https://uktrade.atlassian.net/browse/TP2000-486
# We forgot to add `self` to process_file params and no tests caught it.
@pytest.mark.importer_v2
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
        assert batch.goods_import == False
        assert batch.split_job == False
        assert batch.workbasket

        run_batch.assert_called_once()
        chunk_taric.assert_called_once()


@patch("importer.forms.chunk_taric")
@patch("importer.forms.run_batch_v2")
@pytest.mark.importer_v2
def test_commodity_import_form_valid_envelope(
    run_batch,
    chunk_taric,
    superuser,
    importer_storage,
):
    chunk_taric.return_value = 1
    """Test that form is valid when given valid xml file."""
    mock_request = MagicMock()

    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as upload_file:
        content = upload_file.read()

    file_data = {
        "taric_file": SimpleUploadedFile(
            upload_file.name,
            content,
            content_type="text/xml",
        ),
    }
    data = {
        "workbasket_title": "12345",
    }
    mock_request.user = superuser
    mock_request.FILES = file_data

    form = forms.CommodityImportForm(data, file_data, request=mock_request)
    assert form.is_valid()

    with patch(
        "importer.storages.CommodityImporterStorage.save",
        wraps=MagicMock(side_effect=importer_storage.save),
    ):
        batch = form.save()
        assert batch.name.find(file_data["taric_file"].name) != -1
        assert batch.goods_import is True
        assert batch.split_job is False
        assert batch.author.id == superuser.id
        assert batch.workbasket is None

        # run_batch.assert_called_once()
        chunk_taric.assert_called_once()


@pytest.mark.importer_v2
@pytest.mark.parametrize("file_name,", ("invalid_id", "dtd"))
@patch("importer.forms.capture_exception")
def test_commodity_import_form_invalid_envelope(capture_exception, file_name, settings):
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


@pytest.mark.importer_v2
def test_commodity_import_form_non_xml_file():
    """Test that form returns incorrect file type validation error when passed a
    text file instead of xml."""
    with open(f"{TEST_FILES_PATH}/invalid_type.txt", "rb") as upload_file:
        form_req = HttpRequest()
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text",
            ),
        }

        form = forms.CommodityImportForm({}, file_data, request=form_req)

        assert not form.is_valid()
        assert "The selected file must be XML" in form.errors["taric_file"]


@pytest.mark.importer_v2
# https://uktrade.atlassian.net/browse/TP2000-571
def test_commodity_import_form_long_definition_description(superuser):
    """Tests that form is valid when provided with QuotaDefinition description
    longer than 500 characters."""
    mock_request = MagicMock()
    with open(f"{TEST_FILES_PATH}/quota_definition.xml", "rb") as upload_file:
        data = {
            "workbasket_title": "12345",
        }
        file_data = {
            "taric_file": SimpleUploadedFile(
                upload_file.name,
                upload_file.read(),
                content_type="text/xml",
            ),
        }
        mock_request.user = superuser
        mock_request.FILES = file_data
        form = forms.CommodityImportForm(data, file_data, request=mock_request)

    assert form.is_valid()
