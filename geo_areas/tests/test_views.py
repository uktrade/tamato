import pytest

from common.tests.util import assert_model_view
from common.tests.util import get_detail_class_based_view_urls_matching_url
from common.tests.util import view_urlpattern_ids
from geo_areas.models import GeographicalArea

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_detail_class_based_view_urls_matching_url("geographical-areas/"),
    ids=view_urlpattern_ids,
)
def test_geographical_area_detail_views(view, url_pattern, valid_user_client):
    """Verify that geographical detail views are under the url geographical-
    areas and don't return an error."""
    model_overrides = {
        "geo_areas.views.GeographicalAreaCreateDescription": GeographicalArea,
    }

    assert_model_view(view, url_pattern, valid_user_client, model_overrides)
