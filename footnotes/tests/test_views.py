import datetime

import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import valid_between_end_delta
from common.tests.util import validity_start_delta
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from footnotes.models import Footnote
from footnotes.views import FootnoteList
from workbaskets.tasks import check_workbasket_sync

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda f: {}, True),
        (valid_between_end_delta(days=-1), True),
        (valid_between_end_delta(days=+1), False),
        (valid_between_end_delta(months=-1), True),
        (valid_between_end_delta(years=-1), True),
    ),
)
def test_footnote_update(new_data, expected_valid, use_update_form):
    """
    Tests that footnote update view allows an empty dict and that it is possible
    to update the end date day, month, and year to an earlier date.

    We expect a later end date to fail because the validity period extends
    beyond that of the footnote type. We test end date, rather than start_date
    because it is not possible to edit the start date through the view without
    separately updating the description start date beforehand.
    """
    with raises_if(ValidationError, not expected_valid):
        use_update_form(
            factories.FootnoteFactory(
                valid_between=factories.date_ranges("big"),
                footnote_type__valid_between=factories.date_ranges("big"),
            ),
            new_data,
        )


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda f: {}, True),
        (validity_start_delta(days=+1), True),
        (validity_start_delta(days=-1), True),
        (validity_start_delta(months=1), True),
        (validity_start_delta(years=1), True),
        (lambda f: {"description": f.description + "AAA"}, True),
        (lambda f: {"description": ""}, False),
    ),
)
def test_footnote_description_update(new_data, expected_valid, use_update_form):
    with raises_if(ValidationError, not expected_valid):
        use_update_form(factories.FootnoteDescriptionFactory(), new_data)


@pytest.mark.parametrize(
    ("new_data", "workbasket_valid"),
    (
        (lambda f: {}, True),
        (lambda f: {"description": f.description + "AAA"}, True),
        (validity_start_delta(days=1), False),
    ),
)
def test_footnote_business_rule_application(
    new_data,
    workbasket_valid,
    use_update_form,
):
    description = use_update_form(factories.FootnoteDescriptionFactory(), new_data)
    check_workbasket_sync(description.transaction.workbasket)
    assert (
        description.transaction.workbasket.unchecked_or_errored_transactions.exists()
        is not workbasket_valid
    )


def test_footnote_delete_form(use_delete_form):
    use_delete_form(factories.FootnoteFactory())


def test_footnote_description_delete_form(use_delete_form):
    footnote = factories.FootnoteFactory()
    description1, description2 = factories.FootnoteDescriptionFactory.create_batch(
        2,
        described_footnote=footnote,
    )
    use_delete_form(description1)
    try:
        use_delete_form(description2)
    except ValidationError as e:
        assert (
            "This description cannot be deleted because at least one description record is mandatory."
            in e.message
        )


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "footnotes/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_footnote_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that measure detail views are under the url footnotes/ and don't
    return an error."""
    model_overrides = {"footnotes.views.FootnoteDescriptionCreate": Footnote}

    assert_model_view_renders(view, url_pattern, valid_user_client, model_overrides)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "footnotes/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[FootnoteList],
    ),
    ids=view_urlpattern_ids,
)
def test_footnote_list_view(view, url_pattern, valid_user_client):
    """Verify that footnote list view is under the url footnotes/ and doesn't
    return an error."""
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
def test_footnote_edit_views(
    data_changes,
    expected_valid,
    update_type,
    use_edit_view,
    workbasket,
    published_footnote_type,
):
    """Tests that footnote edit views (for update types CREATE and UPDATE)
    allows saving a valid form from an existing instance and that an invalid
    form fails validation as expected."""

    footnote = factories.FootnoteFactory.create(
        update_type=update_type,
        footnote_type=published_footnote_type,
        transaction=workbasket.new_transaction(),
    )
    with raises_if(ValidationError, not expected_valid):
        use_edit_view(footnote, data_changes)


def test_footnote_api_list_view(valid_user_client, date_ranges):
    selected_type = factories.FootnoteTypeFactory.create()
    expected_results = [
        factories.FootnoteFactory.create(
            valid_between=date_ranges.normal,
            footnote_type=selected_type,
        ),
        factories.FootnoteFactory.create(
            valid_between=date_ranges.earlier,
            footnote_type=selected_type,
        ),
    ]
    assert_read_only_model_view_returns_list(
        "footnote",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_footnote_type_api_list_view(valid_user_client):
    expected_results = [factories.FootnoteTypeFactory.create()]

    assert_read_only_model_view_returns_list(
        "footnotetype",
        "footnote_type_id",
        "footnote_type_id",
        expected_results,
        valid_user_client,
    )
