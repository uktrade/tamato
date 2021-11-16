import pytest

from certificates.models import Certificate
from common.tests.util import assert_model_view
from common.tests.util import get_detail_class_based_view_urls_matching_url
from common.tests.util import view_urlpattern_ids


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_detail_class_based_view_urls_matching_url("certificates/"),
    ids=view_urlpattern_ids,
)
def test_certificate_detail_views(view, url_pattern, valid_user_client):
    """Verify that certificate detail views are under the url certificates/ and
    don't return an error."""
    model_overrides = {"certificates.views.CertificateCreateDescription": Certificate}

    assert_model_view(view, url_pattern, valid_user_client, model_overrides)
