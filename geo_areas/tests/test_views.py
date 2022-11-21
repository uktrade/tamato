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
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from geo_areas.models import GeographicalArea
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
