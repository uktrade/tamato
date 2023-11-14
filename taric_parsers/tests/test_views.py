from os import path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from common.tests import factories
from common.tests.factories import ImportBatchFactory

pytestmark = pytest.mark.django_db

TEST_FILES_PATH = path.join(path.dirname(__file__), "support")


@pytest.mark.new_importer
@pytest.mark.parametrize(
    "url_name",
    [
        "taric_parser_import_ui_details",
        "taric_parser_import_ui_list",
        "taric_parser_import_ui_create",
    ],
)
def test_import_urls_requires_superuser(
    valid_user: User,
    admin_user: User,
    client: Client,
    url_name: str,
):
    """Ensure only superusers can access the TARIC Parser views."""

    if url_name == "taric_parser_import_ui_details":
        # Seed data with import batch
        ib = ImportBatchFactory.create()
        url = reverse(url_name, args=[ib.pk])
    else:
        url = reverse(url_name)

    bad_response = client.get(url)
    assert bad_response.status_code == 302
    assert bad_response.url != url

    client.force_login(valid_user)
    bad_response = client.get(url)
    assert bad_response.status_code == 403

    client.force_login(admin_user)
    good_response = client.get(url)
    assert good_response.status_code == 200
    assert good_response.request["PATH_INFO"] == url


@pytest.mark.new_importer
@patch("taric_parsers.forms.UploadTaricForm.save")
def test_import_success_redirect(mock_save, superuser_client):
    mock_save.return_value = factories.ImportBatchFactory.create()
    url = reverse("taric_parser_import_ui_create")
    redirect_url = reverse("taric_parser_import_ui_list")
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = superuser_client.post(
        url,
        {"taric_file": taric_file, "name": "test file", "commodities_only": "on"},
    )
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.new_importer
@pytest.mark.parametrize(
    "file_name,error_msg",
    [
        (
            "invalid.xml",
            "The selected file could not be processed, please check the file and try again.",
        ),
        (
            "broken.xml",
            "The selected file could not be processed, please check the file and try again.",
        ),
        # ("dtd.xml", "The selected file could not be processed, please check the file and try again."),
        (
            "invalid_type.txt",
            "The selected file could not be processed, please check the file and try again.",
        ),
    ],
)
def test_import_failure(file_name, error_msg, superuser_client):
    url = reverse("taric_parser_import_ui_create")
    with open(f"{TEST_FILES_PATH}/{file_name}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = superuser_client.post(
        url,
        {"taric_file": taric_file, "name": "test file"},
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert error_msg in soup.select(".govuk-error-message")[0].text
