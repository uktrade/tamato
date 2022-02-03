import pytest

from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from geo_areas.models import GeographicalArea
from geo_areas.views import GeoAreaList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "geographical-areas/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_geographical_area_detail_views(view, url_pattern, valid_user_client):
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
