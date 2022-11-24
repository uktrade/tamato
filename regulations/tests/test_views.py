import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import valid_between_start_delta
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from regulations.views import RegulationList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda r: {}, True),
        (valid_between_start_delta(days=+1), True),
        (valid_between_start_delta(days=-1), False),
        (valid_between_start_delta(months=1), True),
        (valid_between_start_delta(years=1), True),
    ),
)
def test_regulation_update(new_data, expected_valid, use_update_form):
    with raises_if(ValidationError, not expected_valid):
        use_update_form(factories.UIRegulationFactory(), new_data)


@pytest.mark.parametrize(
    "factory",
    (factories.UIRegulationFactory,),
)
def test_regulation_delete(factory, use_delete_form):
    use_delete_form(factory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "regulations/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_regulation_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
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
def test_regulation_list_view(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that regulation list view is under the url regulations/ and
    doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


def test_regulation_api_list_view(valid_user_client, date_ranges):
    selected_group = factories.RegulationGroupFactory.create()
    expected_results = [
        factories.RegulationFactory.create(
            valid_between=date_ranges.normal,
            regulation_group=selected_group,
        ),
        factories.RegulationFactory.create(
            valid_between=date_ranges.earlier,
            regulation_group=selected_group,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "regulation",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )
