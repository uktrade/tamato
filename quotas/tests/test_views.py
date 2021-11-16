import pytest

from common.tests.util import assert_model_view
from common.tests.util import get_detail_class_based_view_urls_matching_url
from common.tests.util import view_urlpattern_ids

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_detail_class_based_view_urls_matching_url("quotas/"),
    ids=view_urlpattern_ids,
)
def test_quota_detail_views(view, url_pattern, valid_user_client):
    """Verify that quota detail views are under the url quotas and don't return
    an error."""
    assert_model_view(view, url_pattern, valid_user_client)
