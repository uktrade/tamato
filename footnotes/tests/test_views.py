import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import valid_between_start_delta
from common.tests.util import validity_start_delta
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from footnotes.models import Footnote
from footnotes.views import FootnoteList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda f: {}, True),
        (valid_between_start_delta(days=+1), True),
        (valid_between_start_delta(days=-1), False),
        (valid_between_start_delta(months=1), True),
        (valid_between_start_delta(years=1), True),
    ),
)
def test_footnote_update(new_data, expected_valid, use_update_form):
    with raises_if(ValidationError, not expected_valid):
        use_update_form(factories.FootnoteFactory(), new_data)


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
    with raises_if(ValidationError, not workbasket_valid):
        description.transaction.workbasket.clean()


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "footnotes/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_footnote_detail_views(view, url_pattern, valid_user_client):
    """Verify that measure detail views are under the url footnotes/ and don't
    return an error."""
    model_overrides = {"footnotes.views.FootnoteCreateDescription": Footnote}

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
