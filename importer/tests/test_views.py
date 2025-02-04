from os import path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from common.tests import factories
from importer.models import ImportBatch
from importer.models import ImportBatchStatus
from workbaskets.validators import WorkflowStatus

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")

pytestmark = pytest.mark.django_db

User = get_user_model()


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


def test_commodity_import_list_view_renders(superuser_client):
    factories.ImportBatchFactory.create_batch(
        2,
        goods_import=True,
    )

    response = superuser_client.get(reverse("commodity_importer-ui-list"))
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")

    assert page.find("h1", text="EU Taric import list")
    assert page.find("a", href="/commodity-importer/create/")

    assert page.find("thead").find("th", text="Taric ID number")
    assert page.find("thead").find("th", text="Date added")
    assert page.find("thead").find("th", text="Uploaded by")
    assert page.find("thead").find("th", text="Status")
    assert page.find("thead").find("th", text="Action")

    assert len(page.find_all("tr", class_="govuk-table__row")) == 3
    assert len(page.find_all("span", class_="status-badge")) == 2


@pytest.mark.parametrize(
    "import_batch_factory,goods_status_class",
    [
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.IMPORTING,
                goods_import=True,
            ),
            "empty",
        ),
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
                goods_import=True,
            ),
            "editable_goods",
        ),
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
                goods_import=True,
                taric_file="TGB.xml",
                workbasket__status=WorkflowStatus.ARCHIVED,
            ),
            "no_goods",
        ),
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.FAILED,
                goods_import=True,
            ),
            "empty",
        ),
    ],
)
def test_commodity_import_list_view_goods_status(
    superuser_client,
    import_batch_factory,
    goods_status_class,
):
    """Test that ImportBatch instances in differing states render their 'goods
    status' column correctly on the commodity import list view."""

    import_batch_factory()

    response = superuser_client.get(reverse("commodity_importer-ui-list"))
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert len(page.select(f"td.goods-status.{goods_status_class}")) == 1


def test_commodity_importer_import_new_returns_200(valid_user_client):
    url = reverse("commodity_importer-ui-create")
    response = valid_user_client.get(url)
    assert response.status_code == 200


@patch("importer.forms.CommodityImportForm.save")
def test_commodity_importer_import_new_success_redirect(mock_save, valid_user_client):
    mock_save.return_value = factories.ImportBatchFactory.create()
    url = reverse("commodity_importer-ui-create")

    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as f:
        content = f.read()

    data = {
        "workbasket_title": "12345",
        "taric_file": SimpleUploadedFile(
            "taric_file.xml",
            content,
            content_type="text/xml",
        ),
    }

    response = valid_user_client.post(url, data)
    assert response.status_code == 302

    batch = ImportBatch.objects.last()
    redirect_url = reverse(
        "commodity_importer-ui-create-success",
        kwargs={"pk": batch.pk},
    )
    assert response.url == redirect_url

    response = valid_user_client.get(redirect_url)
    assert response.status_code == 200


@pytest.mark.importer_v2
@pytest.mark.parametrize(
    "file_name,error_msg",
    [
        ("invalid.xml", "The selected file could not be uploaded - try again"),
        ("broken.xml", "The selected file could not be uploaded - try again"),
        ("dtd.xml", "The selected file could not be uploaded - try again"),
        ("invalid_type.txt", "The selected file must be XML"),
    ],
)
def test_commodity_importer_import_new_failure(file_name, error_msg, valid_user_client):
    url = reverse("commodity_importer-ui-create")
    with open(f"{TEST_FILES_PATH}/{file_name}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = valid_user_client.post(
        url,
        {"workbasket_title": "12345", "taric_file": taric_file},
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert error_msg in soup.select(".govuk-error-message")[0].text


def test_taric_import_list_filters_render(superuser_client):
    response = superuser_client.get(reverse("commodity_importer-ui-list"))
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert page.find("nav", class_="workbasket-filters")
    filter_links = []
    expected_filter_links = [
        "?status=",
        "?status=IMPORTING",
        "?status=SUCCEEDED&workbasket__status=EDITING",
        "?status=SUCCEEDED&workbasket__status=PUBLISHED",
        "?status=SUCCEEDED&workbasket__status=ARCHIVED",
        "?status=FAILED",
    ]
    for link in page.find_all(class_="govuk-link--no-visited-state"):
        filter_links.append(link.get("href"))

    assert filter_links == expected_filter_links


@pytest.mark.parametrize(
    "import_batch,filter_url,expected_status_class,expected_status_text",
    [
        (
            "importing_goods_import_batch",
            "IMPORTING",
            "status-badge",
            "IMPORTING",
        ),
        (
            "failed_goods_import_batch",
            "FAILED",
            "status-badge-red",
            "FAILED",
        ),
        (
            "completed_goods_import_batch",
            "SUCCEEDED&workbasket__status=EDITING",
            "status-badge-purple",
            "READY",
        ),
        (
            "published_goods_import_batch",
            "SUCCEEDED&workbasket__status=PUBLISHED",
            "status-badge-green",
            "PUBLISHED",
        ),
        (
            "empty_goods_import_batch",
            "SUCCEEDED&workbasket__status=ARCHIVED",
            "status-badge-grey",
            "EMPTY",
        ),
    ],
)
def test_import_list_filters_return_correct_imports(
    superuser_client,
    import_batch,
    request,
    filter_url,
    expected_status_class,
    expected_status_text,
):
    import_batch = request.getfixturevalue(import_batch)

    url = reverse("commodity_importer-ui-list")
    response = superuser_client.get(f"{url}?status={filter_url}")

    assert response.status_code == 200
    page = BeautifulSoup(str(response.content), "html.parser")

    assert len(page.find_all("tr", class_="govuk-table__row")) == 2
    assert len(page.find_all(class_=expected_status_class)) == 1
    assert page.find(class_=expected_status_class, text=expected_status_text)
    assert page.find("tbody").find("td", text=import_batch.name)


def test_notify_channel_islands_redirects(
    valid_user_client,
    completed_goods_import_batch,
):
    """Tests that, when the notify button is clicked that it redirects to the
    conformation page on successful notification trigger."""

    with patch(
        "notifications.models.send_emails_task",
        return_value=MagicMock(),
    ) as mocked_email_task:
        response = valid_user_client.get(
            reverse(
                "goods-report-notify",
                kwargs={"pk": completed_goods_import_batch.pk},
            ),
        )

        mocked_email_task.assert_called_once()
    assert response.status_code == 302
    assert response.url == reverse(
        "goods-report-notify-success",
        kwargs={"pk": completed_goods_import_batch.pk},
    )


def test_view_imported_goods_renders(valid_user_client, workbasket):
    url = reverse("review-imported-goods", kwargs={"pk": workbasket.pk})
    response = valid_user_client.get(url)
    assert response.status_code == 200
