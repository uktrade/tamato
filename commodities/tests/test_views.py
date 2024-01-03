import datetime
import json

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from commodities.models.orm import GoodsNomenclature
from commodities.views import CommodityList
from common.jinja2 import format_date_string
from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tariffs_api import Endpoints
from common.tests import factories
from common.tests.factories import GoodsNomenclatureDescriptionFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


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
    requests_mock,
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
        requests_mock=requests_mock,
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
        "commodity-ui-detail-descriptions",
        "commodity-ui-detail-indent-history",
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
    response = valid_user_client.get(f"{url}?sort_by=geo_area&ordered=desc")
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
    response = valid_user_client.get(f"{url}?sort_by=geo_area&ordered=asc")
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
    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=desc")
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
    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=asc")
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
    response = valid_user_client.get(f"{url}?sort_by=measure_type&ordered=desc")
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
    response = valid_user_client.get(f"{url}?sort_by=measure_type&ordered=asc")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    measure_sids = [
        int(el.text) for el in soup.select(".govuk-table tbody tr td:first-child")
    ]
    assert measure_sids == [measure1.sid, measure2.sid, measure3.sid]


def test_add_commodity_footnote(client_with_current_workbasket, date_ranges):
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

    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert commodity.footnote_associations.count() == 1

    new_association = commodity.footnote_associations.first()

    assert response.url == reverse(
        "commodity-ui-add-footnote-confirm",
        kwargs={"pk": new_association.pk},
    )
    assert new_association.associated_footnote == footnote
    assert new_association.goods_nomenclature == commodity


def test_add_commodity_footnote_NIG22_failure(
    client_with_current_workbasket,
    date_ranges,
):
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

    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 200

    assert (
        "The period of the association with a footnote must be within the validity period of the nomenclature."
        in response.content.decode(response.charset)
    )


def test_add_commodity_footnote_form_page(client_with_current_workbasket, date_ranges):
    commodity = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    url = reverse("commodity-ui-add-footnote", kwargs={"sid": commodity.sid})
    response = client_with_current_workbasket.get(url)

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

    page_footnote_descriptions = {
        element.select(".govuk-table__cell:nth-child(2)")[0].text.strip()
        for element in footnotes
    }
    footnote_descriptions = {
        footnote_association.associated_footnote.descriptions.first().description
        for footnote_association in commodity.footnote_associations.all()
    }
    assert not footnote_descriptions.difference(page_footnote_descriptions)


def test_commodity_footnote_update_success(client_with_current_workbasket, date_ranges):
    commodity = factories.GoodsNomenclatureFactory.create()
    footnote1 = factories.FootnoteFactory.create()
    association1 = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote1,
        goods_nomenclature=commodity,
    )
    url = association1.get_url("edit")
    data = {
        "goods_nomenclature": commodity.id,
        "associated_footnote": footnote1.id,
        "start_date_0": date_ranges.later.lower.day,
        "start_date_1": date_ranges.later.lower.month,
        "start_date_2": date_ranges.later.lower.year,
        "end_date": "",
    }
    response = client_with_current_workbasket.post(url, data)
    tx = Transaction.objects.last()
    updated_association = (
        FootnoteAssociationGoodsNomenclature.objects.approved_up_to_transaction(
            tx,
        ).first()
    )
    assert response.status_code == 302
    assert response.url == updated_association.get_url("confirm-update")


def test_footnote_association_delete(client_with_current_workbasket):
    commodity = factories.GoodsNomenclatureFactory.create()
    footnote1 = factories.FootnoteFactory.create()
    association1 = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote1,
        goods_nomenclature=commodity,
    )
    url = association1.get_url("delete")
    response = client_with_current_workbasket.post(url, {"submit": "Delete"})

    assert response.status_code == 302
    assert response.url == reverse(
        "footnote_association_goods_nomenclature-ui-confirm-delete",
        kwargs={"sid": commodity.sid},
    )

    tx = Transaction.objects.last()

    assert tx.workbasket.tracked_models.first().associated_footnote == footnote1
    assert tx.workbasket.tracked_models.first().goods_nomenclature == commodity
    assert tx.workbasket.tracked_models.first().update_type == UpdateType.DELETE

    confirm_response = client_with_current_workbasket.get(response.url)
    soup = BeautifulSoup(
        confirm_response.content.decode(response.charset),
        "html.parser",
    )
    h1 = soup.select("h1")[0]

    assert h1.text.strip() == (
        f"Footnote association {footnote1.footnote_type.footnote_type_id}{footnote1.footnote_id} for commodity code {commodity.item_id} has been deleted"
    )


def test_commodity_measures_vat_excise_no_data(valid_user_client, requests_mock):
    commodity = factories.GoodsNomenclatureFactory.create()
    requests_mock.get(url=f"{Endpoints.COMMODITIES.value}{commodity.item_id}", json={})
    url = reverse(
        "commodity-ui-detail-measures-vat-excise",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_commodity_measures_vat_excise_with_data(
    valid_user_client,
    requests_mock,
    mock_commodity_data_vat_excise,
    mock_commodity_data_vat_duty_expression,
    mock_commodity_data_geo_area,
    mock_commodity_data_vat_measure_type,
    mock_commodity_data_vat_measure,
):
    commodity = factories.GoodsNomenclatureFactory.create()
    requests_mock.get(
        url=f"{Endpoints.COMMODITIES.value}{commodity.item_id}",
        json=mock_commodity_data_vat_excise,
    )
    url = reverse(
        "commodity-ui-detail-measures-vat-excise",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    cells = soup.select(".govuk-table__body > .govuk-table__row:first-child > td")
    cells[0].text == mock_commodity_data_vat_measure["id"]
    cells[1].text == mock_commodity_data_vat_measure_type["attributes"]["description"]
    cells[2].text == mock_commodity_data_geo_area["attributes"]["description"]
    cells[4].text == mock_commodity_data_vat_duty_expression["attributes"][
        "verbose_duty"
    ]
    cells[5].text == format_date_string(
        mock_commodity_data_vat_measure["attributes"]["effective_start_date"],
    )


def test_commodity_measures_vat_excise_no_measures(
    valid_user_client,
    requests_mock,
    mock_commodity_data_no_vat_excise,
):
    commodity = factories.GoodsNomenclatureFactory.create()
    requests_mock.get(
        url=f"{Endpoints.COMMODITIES.value}{commodity.item_id}",
        json=mock_commodity_data_no_vat_excise,
    )
    url = reverse(
        "commodity-ui-detail-measures-vat-excise",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_commodity_measures_vat_excise_get_related(
    valid_user_client,
    requests_mock,
    mock_commodity_data_vat_excise,
    mock_commodity_data_vat_measure,
):
    commodity = factories.GoodsNomenclatureFactory.create()

    measure = mock_commodity_data_vat_measure.copy()
    del measure["relationships"]["duty_expression"]

    data = mock_commodity_data_vat_excise.copy()
    data["included"].append(mock_commodity_data_vat_measure)
    requests_mock.get(
        url=f"{Endpoints.COMMODITIES.value}{commodity.item_id}",
        json=data,
    )
    url = reverse(
        "commodity-ui-detail-measures-vat-excise",
        kwargs={"sid": commodity.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    cells = soup.select(".govuk-table__body > .govuk-table__row:first-child > td")
    # duty sentence
    assert cells[4].text == "—"
