from os import path
from pathlib import Path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from common.tests import factories
from importer.models import ImportBatchStatus

TEST_FILES_PATH = path.join(Path(__file__).parents[2], "commodities/tests/test_files")

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("url_name", ["import_batch-ui-list", "import_batch-ui-create"])
def test_import_urls_requires_superuser(
    valid_user: User,
    admin_user: User,
    client: Client,
    url_name: str,
):
    """Ensure only superusers can access the importer views."""
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


@patch("importer.forms.UploadTaricForm.save")
def test_import_success_redirect(mock_save, superuser_client):
    mock_save.return_value = factories.ImportBatchFactory.create()
    url = reverse("import_batch-ui-create")
    redirect_url = reverse("import_batch-ui-list")
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = superuser_client.post(
        url,
        {"taric_file": taric_file, "name": "test file", "status": "EDITING"},
    )
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.parametrize(
    "file_name,error_msg",
    [
        ("invalid.xml", "The selected file could not be uploaded - try again"),
        ("broken.xml", "The selected file could not be uploaded - try again"),
        ("dtd.xml", "The selected file could not be uploaded - try again"),
        ("invalid_type.txt", "The selected file must be XML"),
    ],
)
def test_import_failure(file_name, error_msg, superuser_client):
    url = reverse("import_batch-ui-create")
    with open(f"{TEST_FILES_PATH}/{file_name}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = superuser_client.post(
        url,
        {"taric_file": taric_file, "name": "test file", "status": "EDITING"},
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert error_msg in soup.select(".govuk-error-message")[0].text


def test_taric_import_list_view_renders(superuser_client):
    factories.ImportBatchFactory.create_batch(5)
    response = superuser_client.get(reverse("commodity_importer-ui-list"))
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert page.find("h1", text="EU Taric import list")

    assert page.find("a", href="/import/commodities/")

    assert page.find("thead").find("th", text="Taric ID number")
    assert page.find("thead").find("th", text="Date added")
    assert page.find("thead").find("th", text="Uploaded by")
    assert page.find("thead").find("th", text="Status")

    assert len(page.find_all("tr", class_="govuk-table__row")) == 6
    assert len(page.find_all("span", class_="status-badge")) == 5


def test_import_list_filters_return_correct_imports(superuser_client):
    # Create imports that don't rely on WB statuses.
    importing_import = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.IMPORTING,
    )
    failed_import = factories.ImportBatchFactory.create(status=ImportBatchStatus.FAILED)

    # Create workbaskets for complex imports
    editing_workbasket = factories.WorkBasketFactory.create()
    published_workbasket = factories.PublishedWorkBasketFactory.create()
    archived_workbasket = factories.ArchivedWorkBasketFactory.create()

    # create complex imports that rely on wb statuses
    completed_import = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=editing_workbasket.id,
    )
    published_import = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=published_workbasket.id,
    )
    empty_import = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=archived_workbasket.id,
    )

    response = superuser_client.get(reverse("commodity_importer-ui-list"))
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")

    # Assert filters are rendered
    assert page.find("nav", class_="workbasket-filters")
    filter_links = []
    expected_filter_links = [
        "/commodity-importer/?status=",
        "/commodity-importer/?status=IMPORTING",
        "/commodity-importer/?status=SUCCEEDED",
        "/commodity-importer/?status=FAILED",
    ]
    for link in page.find_all(class_="govuk-link--no-visited-state"):
        filter_links.append(link.get("href"))

    assert filter_links == expected_filter_links

    #  Assert correct imports are shown under filters
    url = reverse("commodity_importer-ui-list")

    # Importing filter
    response = superuser_client.get(f"{url}?status=IMPORTING")
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_="status-badge")) == 1
    assert page.find(class_="status-badge", text="IMPORTING")

    # Errored filter
    response = superuser_client.get(f"{url}?status=FAILED")
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_="status-badge")) == 1
    assert page.find(class_="status-badge", text="FAILED")

    # Completed filter
    response = superuser_client.get(
        f"{url}?status=SUCCEEDED&workbasket__status=EDITING",
    )
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_="status-badge")) == 1
    assert page.find(class_="status-badge", text="SUCCEEDED")
    assert page.find("tbody").find("td", text=completed_import.name)

    # Published filter
    response = superuser_client.get(
        f"{url}?status=SUCCEEDED&workbasket__status=PUBLISHED",
    )
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_="status-badge")) == 1
    assert page.find(class_="status-badge", text="SUCCEEDED")
    assert page.find("tbody").find("td", text=published_import.name)

    # Empty filter
    response = superuser_client.get(
        f"{url}?status=SUCCEEDED&workbasket__status=ARCHIVED",
    )
    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_="status-badge")) == 1
    assert page.find(class_="status-badge", text="SUCCEEDED")
    assert page.find("tbody").find("td", text=empty_import.name)
