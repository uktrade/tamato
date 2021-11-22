import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from regulations.views import RegulationList

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
    get_class_based_view_urls_matching_url(
        "regulations/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_regulation_detail_views(view, url_pattern, valid_user_client):
    """Verify that regulation detail views are under the url regulations/ and
    don't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "regulations/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[RegulationList],
    ),
    ids=view_urlpattern_ids,
)
def test_regulation_list_view(view, url_pattern, valid_user_client):
    """Verify that regulation list view is under the url regulations/ and
    doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)
