import pytest

from additional_codes.models import AdditionalCode
from common.tests.util import assert_model_view
from common.tests.util import get_detail_class_based_view_urls_matching_url
from common.tests.util import view_urlpattern_ids

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_detail_class_based_view_urls_matching_url("additional_codes/"),
    ids=view_urlpattern_ids,
)
def test_additional_codes_detail_views(view, url_pattern, valid_user_client):
    """Verify that additional code detail views are under the url
    additional_codes/ and don't return an error."""
    model_overrides = {
        "additional_codes.views.AdditionalCodeCreateDescription": AdditionalCode,
    }

    assert_model_view(view, url_pattern, valid_user_client, model_overrides)
