from os import path
from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

from publishing.forms import LoadingReportForm

pytestmark = pytest.mark.django_db

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")


def test_loading_report_form_multiple_reports():
    """Test that form is valid when multiple, valid loading report files are
    submitted."""

    with open(f"{TEST_FILES_PATH}/valid_loading_report.html", "rb") as upload_file:
        content = upload_file.read()

    report1 = SimpleUploadedFile(
        "valid_loading_report.html",
        content,
        content_type="text/html",
    )
    report2 = SimpleUploadedFile(
        "valid_loading_report2.html",
        content,
        content_type="text/html",
    )

    files_data = {
        "files": [report1, report2],
    }
    form_data = {
        "files": [report1, report2],
        "comments": "Test comment",
    }

    loading_reports = QueryDict("", mutable=True)
    loading_reports.update(MultiValueDict(files_data))

    mock_request = MagicMock()
    mock_request.FILES = loading_reports

    form = LoadingReportForm(form_data, request=mock_request)
    assert form.is_valid()


def test_loading_report_form_report_invalid_mime_type():
    """Test that form is invalid when a loading report file is not HTML."""
    invalid_report = SimpleUploadedFile(
        name="invalid_loading_report.xml",
        content=b"invalid",
        content_type="text/xml",
    )

    file_data = {
        "files": invalid_report,
    }
    form_data = {
        "files": invalid_report,
        "comments": "Test comment",
    }

    loading_report = QueryDict("", mutable=True)
    loading_report.update(file_data)

    mock_request = MagicMock()
    mock_request.FILES = loading_report

    form = LoadingReportForm(form_data, request=mock_request)
    assert not form.is_valid()
    assert "The selected loading report files must be HTML" in form.errors["files"]


def test_loading_report_form_reject_report_required():
    """Test that a loading report is required to be uploaded if rejecting an
    envelope."""

    mock_request = MagicMock()
    mock_request.path = "/publishing/envelope-queue/reject/123/"
    mock_request.user.is_superuser = False
    mock_request.FILES = QueryDict("", mutable=True)

    form = LoadingReportForm({}, request=mock_request)
    assert not form.is_valid()
    assert "Select a loading report" in form.errors["files"]

    mock_request.user.is_superuser = True
    form = LoadingReportForm({}, request=mock_request)
    assert form.is_valid()
