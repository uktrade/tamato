import datetime
import json
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

    response = valid_user_client.get(redirect_url)
    assert response.status_code == 200


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


def test_commodity_list_displays_commodity_suffix_indent_and_description(
    valid_user_client,
):
    """Test that a list of commodity codes with links and their suffixes,
    indents and descriptions are displayed on the list view template."""
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
    assert page.find("tbody").find("td", text=commodity1.suffix)
    assert page.find("tbody").find(
        "td",
        text=commodity1.get_indent_as_at(datetime.date.today()).indent,
    )
    assert page.find("tbody").find("td", text="A commodity code description")

    assert page.find("tbody").find("td", text=commodity2.item_id)
    assert page.find("tbody").find(href=f"/commodities/{commodity2.sid}/")
    assert page.find("tbody").find("td", text=commodity2.suffix)
    assert page.find("tbody").find(
        "td",
        text=commodity2.get_indent_as_at(datetime.date.today()).indent,
    )
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
    override_models = {"commodities.views.CommodityAddFootnote": GoodsNomenclature}
    assert_model_view_renders(
        view,
        url_pattern,
        valid_user_client,
        override_models=override_models,
    )


def test_goods_nomenclature(valid_user_client, date_ranges):
    past_good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.earlier,
    )
    present_good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
    )
    future_good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.later,
    )
    url = reverse("goodsnomenclature-list")
    response = valid_user_client.get(url)

    assert response.status_code == 200

    goods = json.loads(response.content)["results"]
    pks = [good["value"] for good in goods]

    assert past_good.pk not in pks
    assert present_good.pk in pks
    assert future_good.pk in pks


@pytest.fixture
def measures(commodity):
    geo_area1 = factories.GeographicalAreaFactory.create(area_id="AAA")
    geo_area2 = factories.GeographicalAreaFactory.create(area_id="BBB")
    geo_area3 = factories.GeographicalAreaFactory.create(area_id="CCC")
    measure1 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        geographical_area=geo_area1,
    )
    measure2 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        geographical_area=geo_area2,
    )
    measure3 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        geographical_area=geo_area3,
    )
    return [measure1, measure2, measure3]


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
    ],
)
def test_commodity_measures(url_name, valid_user_client, commodity, measures):
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    table_rows = soup.select(".govuk-table tbody tr")
    assert len(table_rows) == 3

    measure_sids = {
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    }
    assert not measure_sids.difference(set([m.sid for m in measures]))


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
        "commodity-ui-detail-hierarchy",
    ],
)
def test_commodity_views_200(url_name, valid_user_client, commodity, measures):
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
    ],
)
def test_commodity_measures_no_measures(url_name, valid_user_client, commodity):
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    table_rows = soup.select(".govuk-table tbody tr")
    assert len(table_rows) == 0


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
    ],
)
def test_commodity_measures_sorting_geo_area(
    url_name,
    valid_user_client,
    commodity,
    measures,
):
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=geo_area&order=desc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    measure_sids.reverse()
    assert measure_sids == [m.sid for m in measures]

    url = reverse(
        "commodity-ui-detail-measures-as-defined",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=geo_area&order=asc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [m.sid for m in measures]


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
    ],
)
def test_commodity_measures_sorting_start_date(
    url_name,
    valid_user_client,
    date_ranges,
    commodity,
):
    measure1 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        valid_between=date_ranges.starts_2_months_ago_no_end,
    )
    measure2 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        valid_between=date_ranges.starts_1_month_ago_no_end,
    )
    measure3 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        valid_between=date_ranges.starts_delta_no_end,
    )
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=start_date&order=desc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [measure3.sid, measure2.sid, measure1.sid]

    url = reverse(
        "commodity-ui-detail-measures-as-defined",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=start_date&order=asc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [measure1.sid, measure2.sid, measure3.sid]


@pytest.mark.parametrize(
    "url_name",
    [
        "commodity-ui-detail-measures-as-defined",
        "commodity-ui-detail-measures-declarable",
    ],
)
def test_commodity_measures_sorting_measure_type(
    url_name,
    valid_user_client,
    date_ranges,
    commodity,
):
    type1 = factories.MeasureTypeFactory.create(sid="111")
    type2 = factories.MeasureTypeFactory.create(sid="222")
    type3 = factories.MeasureTypeFactory.create(sid="333")
    measure1 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        measure_type=type1,
    )
    measure2 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        measure_type=type2,
    )
    measure3 = factories.MeasureFactory.create(
        goods_nomenclature=commodity,
        measure_type=type3,
    )
    url = reverse(
        url_name,
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=measure_type&order=desc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [measure3.sid, measure2.sid, measure1.sid]

    url = reverse(
        "commodity-ui-detail-measures-as-defined",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(f"{url}?sort_by=measure_type&order=asc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [measure1.sid, measure2.sid, measure3.sid]


def test_add_commodity_footnote(valid_user_client, date_ranges):
    commodity = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    footnote = factories.FootnoteFactory.create()
    url = reverse("commodity-ui-add-footnote", kwargs={"sid": commodity.sid})
    data = {
        "goods_nomenclature": commodity.id,
        "associated_footnote": footnote.id,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date": "",
    }

    # sanity check
    assert commodity.footnote_associations.count() == 0

    response = valid_user_client.post(url, data)

    assert response.status_code == 302
    assert commodity.footnote_associations.count() == 1

    new_association = commodity.footnote_associations.first()

    assert response.url == reverse(
        "commodity-ui-add-footnote-confirm",
        kwargs={"pk": new_association.pk},
    )
    assert new_association.associated_footnote == footnote
    assert new_association.goods_nomenclature == commodity


def test_add_commodity_footnote_NIG22_failure(valid_user_client, date_ranges):
    """
    Tests failure of NIG22:

    The period of the association with a footnote must be within the validity
    period of the nomenclature.
    """
    commodity = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
    )
    footnote_type = factories.FootnoteTypeFactory.create(application_code=2)
    footnote = factories.FootnoteFactory.create(footnote_type=footnote_type)
    url = reverse("commodity-ui-add-footnote", kwargs={"sid": commodity.sid})
    data = {
        "goods_nomenclature": commodity.id,
        "associated_footnote": footnote.id,
        "start_date_0": date_ranges.later.lower.day,
        "start_date_1": date_ranges.later.lower.month,
        "start_date_2": date_ranges.later.lower.year,
        "end_date": "",
    }

    response = valid_user_client.post(url, data)

    assert response.status_code == 200

    assert (
        "The period of the association with a footnote must be within the validity period of the nomenclature."
        in response.content.decode(response.charset)
    )


def test_add_commodity_footnote_form_page(valid_user_client, date_ranges):
    commodity = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    url = reverse("commodity-ui-add-footnote", kwargs={"sid": commodity.sid})
    response = valid_user_client.get(url)

    assert response.status_code == 200

    soup = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    breadcrumbs_text = [
        el.text.strip().replace("\n", "")
        for el in soup.select(".govuk-breadcrumbs__list-item")
    ]
    assert f"Commodity code: {commodity.item_id}" in breadcrumbs_text


def test_commodity_footnotes_page_200(valid_user_client):
    commodity = factories.GoodsNomenclatureFactory.create()
    url = reverse("commodity-ui-detail-footnotes", kwargs={"sid": commodity.sid})
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_commodity_footnotes_page(valid_user_client):
    commodity = factories.GoodsNomenclatureFactory.create()
    footnote1 = factories.FootnoteFactory.create()
    footnote2 = factories.FootnoteFactory.create()
    association1 = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote1,
        goods_nomenclature=commodity,
    )
    association2 = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote2,
        goods_nomenclature=commodity,
    )
    url = reverse("commodity-ui-detail-footnotes", kwargs={"sid": commodity.sid})
    response = valid_user_client.get(url)

    soup = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    footnotes = soup.select(".govuk-table__body .govuk-table__row")
    assert len(footnotes) == commodity.footnote_associations.count()

    first_footnote_description = (
        footnotes[0].select(".govuk-table__cell:nth-child(2)")[0].text.strip()
    )
    assert (
        first_footnote_description
        == commodity.footnote_associations.first()
        .associated_footnote.descriptions.first()
        .description
    )
