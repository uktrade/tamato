from os import path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from commodities.models.orm import GoodsNomenclature
from commodities.views import CommodityList
from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.factories import GoodsNomenclatureDescriptionFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import ImportBatchFactory
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")


def test_commodities_import_200(valid_user_client):
    url = reverse("commodity-ui-import")
    response = valid_user_client.get(url)
    assert response.status_code == 200


@patch("commodities.forms.CommodityImportForm.save")
def test_commodities_import_success_redirect(mock_save, valid_user_client):
    mock_save.return_value = ImportBatchFactory.create()
    url = reverse("commodity-ui-import")
    redirect_url = reverse("commodity-ui-import-success")
    with open(f"{TEST_FILES_PATH}/valid.xml", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = valid_user_client.post(url, {"taric_file": taric_file})
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
def test_commodities_import_failure(file_name, error_msg, valid_user_client):
    url = reverse("commodity-ui-import")
    with open(f"{TEST_FILES_PATH}/{file_name}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("taric_file.xml", content, content_type="text/xml")
    response = valid_user_client.post(url, {"taric_file": taric_file})
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert error_msg in soup.select(".govuk-error-message")[0].text


def test_commodity_list_displays_commodity_and_description(valid_user_client):
    """Test that a list of commodity codes with links and their descriptions are
    displayed on the list view template."""
    commodity1 = GoodsNomenclatureDescriptionFactory.create(
        description="A commodity code description",
    ).described_goods_nomenclature
    commodity2 = GoodsNomenclatureDescriptionFactory.create(
        description="A second commodity code description",
    ).described_goods_nomenclature

    url = reverse("commodity-ui-list")
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    assert page.find("tbody").find("td", text=commodity1.item_id)
    assert page.find("tbody").find(href=f"/commodities/{commodity1.sid}/")
    assert page.find("tbody").find("td", text="A commodity code description")
    assert page.find("tbody").find("td", text=commodity2.item_id)
    assert page.find("tbody").find(href=f"/commodities/{commodity2.sid}/")
    assert page.find("tbody").find("td", text="A second commodity code description")


def test_commodity_list_queryset():
    """Tests that commodity list queryset orders commodities by item_id."""
    view = CommodityList()
    good_1 = factories.SimpleGoodsNomenclatureFactory.create(item_id="1010000000")
    good_2 = factories.SimpleGoodsNomenclatureFactory.create(item_id="1000000000")
    tx = Transaction.objects.last()
    commodity_count = GoodsNomenclature.objects.approved_up_to_transaction(tx).count()
    with override_current_transaction(tx):
        qs = view.get_queryset()

        assert qs.count() == commodity_count
        assert qs.first().item_id == good_2.item_id
        assert qs.last().item_id == good_1.item_id


@pytest.mark.parametrize("search_terms", ["0", "010", "01010", "0101010"])
def test_commodity_list_filter(search_terms, valid_user_client):
    """Tests that passing an item_id to the filter retrieves the right commodity
    code."""
    commodity = GoodsNomenclatureFactory.create(item_id="0101010101")

    list_url = reverse("commodity-ui-list")
    url = f"{list_url}?item_id={search_terms}"
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    assert page.find("tbody").find(
        "td",
        text=commodity.descriptions.first().description,
    )
    assert page.find("tbody").find("td", text=commodity.item_id)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "commodities/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_commodities_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that commodity detail views are under the url commodities/ and
    don't return an error."""

    assert_model_view_renders(view, url_pattern, valid_user_client)
