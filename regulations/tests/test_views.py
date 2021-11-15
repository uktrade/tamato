import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view
from common.tests.util import get_detail_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_urlpattern_ids

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        ({}, True),
        ({"start_date_0": lambda d: d + 1}, True),
        ({"start_date_0": lambda d: d - 1}, False),
        ({"start_date_1": lambda m: m + 1}, True),
        ({"start_date_2": lambda y: y + 1}, True),
    ),
)
def test_regulation_update(new_data, expected_valid, use_update_form):
    with raises_if(ValidationError, not expected_valid):
        use_update_form(factories.UIRegulationFactory(), new_data)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_detail_class_based_view_urls_matching_url("regulations/"),
    ids=view_urlpattern_ids,
)
def test_regulation_detail_views(view, url_pattern, valid_user_client):
    """Verify that regulation detail views are under the url regulations/ and
    don't return an error."""
    assert_model_view(view, url_pattern, valid_user_client)
