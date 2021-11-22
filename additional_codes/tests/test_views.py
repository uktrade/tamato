import pytest

from additional_codes.models import AdditionalCode
from additional_codes.views import AdditionalCodeList
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "additional_codes/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_additional_codes_detail_views(view, url_pattern, valid_user_client):
    """Verify that additional code detail views are under the url
    additional_codes/ and don't return an error."""
    model_overrides = {
        "additional_codes.views.AdditionalCodeCreateDescription": AdditionalCode,
    }

    assert_model_view_renders(view, url_pattern, valid_user_client, model_overrides)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "additional_codes/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[AdditionalCodeList],
    ),
    ids=view_urlpattern_ids,
)
def test_additional_codes_list_view(view, url_pattern, valid_user_client):
    """Verify that additional code list view is under the url additional_codes/
    and doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)
