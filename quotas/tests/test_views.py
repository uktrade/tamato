import pytest

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from quotas.views import QuotaList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    (factories.QuotaOrderNumberFactory,),
)
def test_quota_delete_form(factory, use_delete_form):
    use_delete_form(factory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_quota_detail_views(view, url_pattern, valid_user_client):
    """Verify that quota detail views are under the url quotas and don't return
    an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[QuotaList],
    ),
    ids=view_urlpattern_ids,
)
def test_quota_list_view(view, url_pattern, valid_user_client):
    """Verify that quota list view is under the url quotas/ and doesn't return
    an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)
