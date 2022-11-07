import datetime

import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import valid_between_start_delta
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
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


@pytest.mark.parametrize(
    ("data_changes", "expected_valid"),
    (
        ({**date_post_data("start_date", datetime.date.today())}, True),
        (
            {
                "start_date_0": "",
                "start_date_1": "",
                "start_date_2": "",
            },
            False,
        ),
    ),
)
@pytest.mark.parametrize(
    "update_type",
    (
        UpdateType.CREATE,
        UpdateType.UPDATE,
    ),
)
def test_regulation_edit_views(
    data_changes,
    expected_valid,
    update_type,
    use_edit_view,
    workbasket,
):
    """Tests that regulation edit views (for update types CREATE and UPDATE)
    allows saving a valid form from an existing instance and that an invalid
    form fails validation as expected."""

    regulation = factories.UIRegulationFactory.create(
        update_type=update_type,
        transaction=workbasket.new_transaction(),
    )
    with raises_if(ValidationError, not expected_valid):
        use_edit_view(regulation, data_changes)
