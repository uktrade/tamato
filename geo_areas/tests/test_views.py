import pytest
from bs4 import BeautifulSoup
from rest_framework.reverse import reverse

from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from geo_areas.forms import GeoMembershipAction
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode
from geo_areas.views import GeoAreaList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    (factories.GeographicalAreaFactory, factories.GeographicalAreaDescriptionFactory),
)
def test_geo_area_delete(factory, use_delete_form):
    use_delete_form(factory())


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


def test_geo_area_update_view_200(valid_user_client):
    geo_area = factories.GeographicalAreaFactory.create()
    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": geo_area.sid},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_geo_area_edit_update_view_200(valid_user_client):
    geo_area = factories.GeographicalAreaFactory.create()
    url = reverse(
        "geo_area-ui-edit-update",
        kwargs={"sid": geo_area.sid},
    )
    response = valid_user_client.get(url)
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


def test_geo_area_update_view_edit_end_date_invalid_date(
    valid_user_client,
    session_workbasket,
    date_ranges,
):
    """Tests that HTML contains a form validation error after posting to geo
    area update endpoint with an invalid end date as checked against indirect
    business rule ON6."""

    geo_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )
    order_origin_number = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=geo_area,
        valid_between=date_ranges.no_end,
    )

    form_data = {
        "end_date_0": date_ranges.later.upper.day,
        "end_date_1": date_ranges.later.upper.month,
        "end_date_2": date_ranges.later.upper.year,
    }

    url = reverse(
        "geo_area-ui-edit",
        kwargs={"sid": geo_area.sid},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    a_tags = page.select("ul.govuk-list.govuk-error-summary__list a")
    assert (
        a_tags[0].text
        == "The validity period of the geographical area must span the validity period of the quota order number origin."
    )


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
