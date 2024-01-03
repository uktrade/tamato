import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from rest_framework.reverse import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from geo_areas.forms import GeoMembershipAction
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode
from geo_areas.views import GeoAreaDetailMeasures
from geo_areas.views import GeoAreaList

pytestmark = pytest.mark.django_db


def test_geo_area_delete(use_delete_form):
    use_delete_form(factories.GeographicalAreaFactory())


def test_geo_area_description_delete_form(use_delete_form):
    geo_area = factories.GeographicalAreaFactory()
    (
        description1,
        description2,
    ) = factories.GeographicalAreaDescriptionFactory.create_batch(
        2,
        described_geographicalarea=geo_area,
    )
    use_delete_form(description1)
    try:
        use_delete_form(description2)
    except ValidationError as e:
        assert (
            "This description cannot be deleted because at least one description record is mandatory."
            in e.message
        )


def test_geographical_area_description_create(
    client_with_current_workbasket,
    date_ranges,
):
    """Tests that a geographical area description can be created."""

    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.earlier,
    )
    current_geo_area = geo_area.new_version(
        geo_area.transaction.workbasket,
        valid_between=date_ranges.normal,
    )

    form_data = {
        "described_geographicalarea": current_geo_area.pk,
        "validity_start_0": date_ranges.future.lower.day,
        "validity_start_1": date_ranges.future.lower.month,
        "validity_start_2": date_ranges.future.lower.year,
        "description": "New test description",
    }
    url = reverse(
        "geo_area-ui-description-create",
        kwargs={"sid": current_geo_area.sid},
    )
    response = client_with_current_workbasket.post(url, form_data)
    assert response.status_code == 302

    with override_current_transaction(Transaction.objects.last()):
        new_description = current_geo_area.get_description()
        assert new_description.description == form_data["description"]
        assert new_description.validity_start == date_ranges.future.lower


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "geographical-areas/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_geographical_area_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that geographical detail views are under the url geographical-
    areas and don't return an error."""
    model_overrides = {
        "geo_areas.views.GeoAreaDescriptionCreate": GeographicalArea,
        "geo_areas.views.GeographicalMembershipsCreate": GeographicalArea,
    }

    assert_model_view_renders(view, url_pattern, valid_user_client, model_overrides)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "geographical-areas/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[GeoAreaList],
    ),
    ids=view_urlpattern_ids,
)
def test_geographical_area_list_view(view, url_pattern, valid_user_client):
    """Verify that geographical list view is under the url geographical-areas/
    and doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


def test_geographical_area_list_queryset():
    """Tests that geo area list queryset contains only the latest version of a
    geo_area annotated with the current description."""
    description = factories.GeographicalAreaDescriptionFactory.create(
        description="Englund",  # /PS-IGNORE
    )
    new_description = description.new_version(
        description.transaction.workbasket,
        description="England",  # /PS-IGNORE
    )
    new_area = new_description.described_geographicalarea.new_version(
        description.transaction.workbasket,
    )
    view = GeoAreaList()
    qs = view.get_queryset()

    with override_current_transaction(new_area.transaction):
        assert qs.count() == 1
        assert qs.first().description == "England"  # /PS-IGNORE
        assert qs.first() == new_area


# https://uktrade.atlassian.net/browse/TP2000-225
@pytest.mark.parametrize("search_terms", ["greenla", "gREEnla", "GL", "gl"])
def test_geographical_area_list_filter(search_terms, valid_user_client):
    """Tests that an updated geographical area is still searchable by the
    description created alongside the original version."""
    geo_area = factories.GeographicalAreaDescriptionFactory.create(
        description="Greenland",
        described_geographicalarea__area_id="GL",
    ).described_geographicalarea
    geo_area.new_version(geo_area.transaction.workbasket)
    list_url = reverse("geo_area-ui-list")
    url = f"{list_url}?search={search_terms}"
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    assert page.find("tbody").find("td", text="Greenland")


def test_geo_area_api_list_view(valid_user_client):
    expected_results = [factories.GeographicalAreaFactory.create()]
    assert_read_only_model_view_returns_list(
        "geo_area",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_geo_area_update_view_200(client_with_current_workbasket):
    geo_area = factories.GeographicalAreaFactory.create()
    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": geo_area.sid},
    )
    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200


def test_geo_area_edit_update_view_200(client_with_current_workbasket):
    geo_area = factories.GeographicalAreaFactory.create()
    url = reverse(
        "geo_area-ui-edit-update",
        kwargs={"sid": geo_area.sid},
    )
    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200


def test_geo_area_update_view_edit_end_date(
    valid_user_client,
    session_workbasket,
    date_ranges,
):
    """Tests that a geographical area's end date can be edited."""
    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )

    form_data = {
        "end_date_0": date_ranges.later.upper.day,
        "end_date_1": date_ranges.later.upper.month,
        "end_date_2": date_ranges.later.upper.year,
    }
    new_end_date = date_ranges.later.upper

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": geo_area.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-confirm-update",
        kwargs={"sid": geo_area.sid},
    )
    assert response.url == redirect_url

    geo_areas = GeographicalArea.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for geo_area in geo_areas:
        assert geo_area.valid_between.upper == new_end_date
        assert geo_area.update_type == UpdateType.UPDATE


def test_geo_area_update_view_membership_add_country_or_region(
    valid_user_client,
    session_workbasket,
):
    """Tests that a country or region can be added as a member of the area group
    being edited."""
    area_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    country = factories.GeographicalAreaFactory.create(area_code=AreaCode.COUNTRY)

    membership = GeographicalMembership.objects.filter(
        geo_group__sid=area_group.sid,
        member__sid=country.sid,
    )
    assert not membership

    form_data = {
        "member": "COUNTRY",
        "country": country.pk,
        "new_membership_start_date_0": area_group.valid_between.lower.day,
        "new_membership_start_date_1": area_group.valid_between.lower.month,
        "new_membership_start_date_2": area_group.valid_between.lower.year,
    }
    expected_valid_between = area_group.valid_between

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": area_group.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-confirm-update",
        kwargs={"sid": area_group.sid},
    )
    assert response.url == redirect_url

    workbasket = GeographicalMembership.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for membership in workbasket:
        assert membership.valid_between == expected_valid_between
        assert membership.update_type == UpdateType.CREATE


def test_geo_area_update_view_membership_add_to_group(
    valid_user_client,
    session_workbasket,
):
    """Tests that the country or region being edited can be added as a member of
    an area group."""
    region = factories.GeographicalAreaFactory.create(area_code=AreaCode.REGION)
    area_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)

    membership = GeographicalMembership.objects.filter(
        geo_group__sid=area_group.sid,
        member__sid=region.sid,
    )
    assert not membership

    form_data = {
        "geo_group": area_group.pk,
        "new_membership_start_date_0": area_group.valid_between.lower.day,
        "new_membership_start_date_1": area_group.valid_between.lower.month,
        "new_membership_start_date_2": area_group.valid_between.lower.year,
    }
    expected_valid_between = area_group.valid_between

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": region.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-confirm-update",
        kwargs={"sid": region.sid},
    )
    assert response.url == redirect_url

    workbasket = GeographicalMembership.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for membership in workbasket:
        assert membership.valid_between == expected_valid_between
        assert membership.update_type == UpdateType.CREATE


def test_geo_area_update_view_membership_edit_end_date(
    valid_user_client,
    session_workbasket,
    date_ranges,
):
    """Tests that an end date for a geographical membership can be edited."""
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    form_data = {
        "membership": membership.pk,
        "action": GeoMembershipAction.END_DATE,
        "membership_end_date_0": area_group.valid_between.upper.day,
        "membership_end_date_1": area_group.valid_between.upper.month,
        "membership_end_date_2": area_group.valid_between.upper.year,
    }

    expected_end_date = area_group.valid_between.upper

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": country.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-confirm-update",
        kwargs={"sid": country.sid},
    )
    assert response.url == redirect_url

    workbasket = GeographicalMembership.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for membership in workbasket:
        assert membership.valid_between.upper == expected_end_date
        assert membership.update_type == UpdateType.UPDATE


def test_geo_area_update_view_membership_deletion(
    valid_user_client,
    session_workbasket,
    date_ranges,
):
    """Tests that a country or region can be deleted as a member of an area
    group."""
    country = factories.CountryFactory.create()
    area_group = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country,
    )

    form_data = {
        "membership": membership.pk,
        "action": GeoMembershipAction.DELETE,
    }

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": country.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-confirm-update",
        kwargs={"sid": country.sid},
    )
    assert response.url == redirect_url

    workbasket = GeographicalMembership.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for membership in workbasket:
        assert membership.update_type == UpdateType.DELETE


def test_geo_area_create_view(valid_user_client, session_workbasket, date_ranges):
    """Tests that a geographical area can be created."""
    form_data = {
        "area_code": AreaCode.COUNTRY,
        "area_id": "TC",
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Test country",
    }
    expected_valid_between = date_ranges.normal

    url = reverse("geo_area-ui-create")
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    with override_current_transaction(Transaction.objects.last()):
        geo_area = GeographicalArea.objects.get(
            transaction__workbasket=session_workbasket,
        )
        assert geo_area.update_type == UpdateType.CREATE
        assert geo_area.area_code == form_data["area_code"]
        assert geo_area.area_id == form_data["area_id"]
        assert geo_area.valid_between == expected_valid_between
        assert geo_area.get_description().description == form_data["description"]


def test_geo_area_edit_create_view(
    use_edit_view,
    workbasket,
    date_ranges,
):
    """Tests that geographical area CREATE instances can be edited."""
    geo_area = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.REGION,
        area_id="TR",
        valid_between=date_ranges.no_end,
        transaction=workbasket.new_transaction(),
    )

    data_changes = {**date_post_data("end_date", date_ranges.normal.upper)}
    with raises_if(ValidationError, not True):
        use_edit_view(geo_area, data_changes)


def test_geographical_membership_create_view(
    valid_user_client,
    session_workbasket,
    date_ranges,
):
    """Tests that multiple geographical memberships can be created."""
    country = factories.CountryFactory.create(valid_between=date_ranges.no_end)
    area_groups = factories.GeoGroupFactory.create_batch(
        2,
        valid_between=date_ranges.no_end,
    )

    form_data = {
        "geo_membership-group-formset-0-geo_group": area_groups[0].pk,
        "geo_membership-group-formset-0-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-group-formset-0-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-group-formset-0-start_date_2": date_ranges.no_end.lower.year,
        "geo_membership-group-formset-1-geo_group": area_groups[1].pk,
        "geo_membership-group-formset-1-start_date_0": date_ranges.no_end.lower.day,
        "geo_membership-group-formset-1-start_date_1": date_ranges.no_end.lower.month,
        "geo_membership-group-formset-1-start_date_2": date_ranges.no_end.lower.year,
    }

    url = reverse("geo_area-ui-membership-create", kwargs={"sid": country.sid})
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    redirect_url = reverse(
        "geo_area-ui-membership-confirm-create",
        kwargs={"sid": country.sid},
    )
    assert response.url == redirect_url

    memberships = GeographicalMembership.objects.filter(
        transaction__workbasket=session_workbasket,
    )
    for i, membership in enumerate(memberships):
        assert membership.update_type == UpdateType.CREATE
        assert membership.member == country
        assert membership.geo_group == area_groups[i]
        assert membership.valid_between == date_ranges.no_end


def test_geo_area_detail_measures_view(valid_user_client):
    """Test that `GeoAreaDetailMeasures` view returns 200 and renders actions
    link and other tabs."""
    geo_area = factories.GeographicalAreaFactory.create()

    url_kwargs = {
        "sid": geo_area.sid,
    }
    details_tab_url = reverse("geo_area-ui-detail", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "geo_area-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("geo_area-ui-detail-measures", kwargs=url_kwargs)
    descriptions_tab_url = reverse("geo_area-ui-detail-descriptions", kwargs=url_kwargs)
    memberships_tab_url = reverse("geo_area-ui-detail-memberships", kwargs=url_kwargs)
    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Memberships": memberships_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }

    response = valid_user_client.get(measures_tab_url)
    assert response.status_code == 200

    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    actions = page.find("h2", text="Actions").find_next("a")
    assert actions.text == "View in find and edit measures"
    assert (
        actions.attrs["href"]
        == f"{reverse('measure-ui-list')}?geographical_area={geo_area.pk}"
    )


def test_geo_area_detail_measures_view_lists_measures(valid_user_client):
    """Test that `GeoAreaDetailMeasures` view displays a paginated list of
    measures for a geo area."""
    geo_area = factories.GeographicalAreaFactory.create()
    measures = factories.MeasureFactory.create_batch(
        21,
        geographical_area=geo_area,
    )

    url = reverse(
        "geo_area-ui-detail-measures",
        kwargs={
            "sid": geo_area.sid,
        },
    )
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    table_rows = page.select(".govuk-table tbody tr")
    assert len(table_rows) == GeoAreaDetailMeasures.paginate_by

    table_measure_sids = {
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    }
    assert table_measure_sids.issubset({m.sid for m in measures})

    assert page.find("nav", class_="pagination").find_next("a", href="?page=2")


def test_geo_area_detail_measures_view_sorting_commodity(valid_user_client):
    """Test that measures listed on `GeoAreaDetailMeasures` view can be sorted
    by commodity code in ascending or descending order."""
    geo_area = factories.GeographicalAreaFactory.create()
    measures = factories.MeasureFactory.create_batch(
        3,
        geographical_area=geo_area,
    )
    commodity_codes = [measure.goods_nomenclature.item_id for measure in measures]

    url = reverse(
        "geo_area-ui-detail-measures",
        kwargs={
            "sid": geo_area.sid,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    assert table_commodity_codes == commodity_codes

    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    commodity_codes.reverse()
    assert table_commodity_codes == commodity_codes


def test_geo_area_detail_measures_view_sorting_start_date(
    date_ranges,
    valid_user_client,
):
    """Test that measures listed on `GeoAreaDetailMeasures` view can be sorted
    by start date in ascending or descending order."""
    geo_area = factories.GeographicalAreaFactory.create()
    measure1 = factories.MeasureFactory.create(
        geographical_area=geo_area,
        valid_between=date_ranges.earlier,
    )
    measure2 = factories.MeasureFactory.create(
        geographical_area=geo_area,
        valid_between=date_ranges.normal,
    )
    measure3 = factories.MeasureFactory.create(
        geographical_area=geo_area,
        valid_between=date_ranges.later,
    )

    url = reverse(
        "geo_area-ui-detail-measures",
        kwargs={
            "sid": geo_area.sid,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measure1.sid, measure2.sid, measure3.sid]

    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measure3.sid, measure2.sid, measure1.sid]


def test_geo_area_detail_version_control_view(valid_user_client):
    """Test that `GeoAreaDetailVersionControl` view returns 200 and renders
    table content and other tabs."""
    geo_area = factories.GeographicalAreaFactory.create()
    geo_area.new_version(geo_area.transaction.workbasket)

    url_kwargs = {
        "sid": geo_area.sid,
    }

    details_tab_url = reverse("geo_area-ui-detail", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "geo_area-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("geo_area-ui-detail-measures", kwargs=url_kwargs)
    descriptions_tab_url = reverse("geo_area-ui-detail-descriptions", kwargs=url_kwargs)
    memberships_tab_url = reverse("geo_area-ui-detail-memberships", kwargs=url_kwargs)
    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Memberships": memberships_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }

    response = valid_user_client.get(version_control_tab_url)
    assert response.status_code == 200
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    table_rows = page.select("table > tbody > tr")
    assert len(table_rows) == 2

    update_types = {
        update.text for update in page.select("table > tbody > tr > td:first-child")
    }
    assert update_types == {"Create", "Update"}
