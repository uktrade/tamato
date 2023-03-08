import datetime

import factory
import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from additional_codes.models import AdditionalCode
from additional_codes.views import AdditionalCodeList
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import validity_period_post_data
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda data: {}, False),
        (
            lambda data: {
                "description": "Test description",
                "code": "002",
                "valid_between": validity_period_post_data(
                    datetime.date.today(),
                    datetime.date.today() + relativedelta(months=+1),
                ),
                **date_post_data("start_date", datetime.date.today()),
                **factory.build(
                    dict,
                    type=factories.AdditionalCodeTypeFactory.create().pk,
                    FACTORY_CLASS=factories.AdditionalCodeFactory,
                ),
            },
            True,
        ),
    ),
)
def test_additional_code_create_form(use_create_form, new_data, expected_valid):
    with raises_if(ValidationError, not expected_valid):
        use_create_form(AdditionalCode, new_data)


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
def test_additional_code_edit_views(
    data_changes,
    expected_valid,
    update_type,
    use_edit_view,
    workbasket,
    published_additional_code_type,
):
    """Tests that additional code edit views (for update types CREATE and
    UPDATE) allows saving a valid form from an existing instance and that an
    invalid form fails validation as expected."""

    additional_code = factories.AdditionalCodeFactory.create(
        update_type=update_type,
        type=published_additional_code_type,
        transaction=workbasket.new_transaction(),
    )
    with raises_if(ValidationError, not expected_valid):
        use_edit_view(additional_code, data_changes)


@pytest.mark.parametrize(
    "factory",
    (factories.AdditionalCodeFactory, factories.AdditionalCodeDescriptionFactory),
)
def test_additional_code_delete_form(factory, use_delete_form):
    use_delete_form(factory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "additional_codes/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_additional_codes_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that additional code detail views are under the url
    additional_codes/ and don't return an error."""
    model_overrides = {
        "additional_codes.views.AdditionalCodeDescriptionCreate": AdditionalCode,
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


def test_additional_codes_api_list_view(valid_user_client, date_ranges):
    selected_type = factories.AdditionalCodeTypeFactory.create()
    expected_results = [
        factories.AdditionalCodeFactory.create(
            valid_between=date_ranges.normal,
            type=selected_type,
        ),
        factories.AdditionalCodeFactory.create(
            valid_between=date_ranges.earlier,
            type=selected_type,
        ),
    ]
    assert_read_only_model_view_returns_list(
        "additionalcode",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_additional_code_type_api_list_view(valid_user_client):
    expected_results = [
        factories.AdditionalCodeTypeFactory.create(),
    ]
    assert_read_only_model_view_returns_list(
        "additionalcodetype",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )
