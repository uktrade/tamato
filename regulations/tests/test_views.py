import datetime

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.urls import reverse

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import valid_between_start_delta
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from regulations.models import Regulation
from regulations.validators import RegulationUsage
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
    ("regulation_factory", "search_filter", "value", "expected_results"),
    [
        (
            lambda: factories.UIRegulationFactory.create(
                regulation_group__group_id="PRF",
            ),
            "regulation_group",
            "PRF",
            1,
        ),
        (
            lambda: factories.UIDraftRegulationFactory.create(),
            "regulation_usage",
            "C",
            1,
        ),
        (lambda: factories.UIRegulationFactory.create(), "approved", True, 1),
        (
            lambda: factories.UIRegulationFactory.create(
                regulation_group__group_id="MLA",
            ),
            "regulation_group",
            "FTA",
            0,
        ),
        (
            lambda: factories.UIDraftRegulationFactory.create(),
            "regulation_usage",
            "X",
            0,
        ),
        (lambda: factories.UIRegulationFactory.create(), "approved", False, 0),
    ],
)
def test_regulations_list_view_search_filters(
    regulation_factory,
    search_filter,
    value,
    expected_results,
    valid_user_client,
):
    """Test that regulation list view filters search results according to search
    filter value."""
    regulation = regulation_factory()

    view_url = reverse("regulation-ui-list")
    url = f"{view_url}?{search_filter}={value}"

    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    search_results = page.select("table > tbody > tr")
    assert len(search_results) == expected_results
    if search_results:
        assert search_results[0].td.text == regulation.regulation_id


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


def test_regulation_update_view_new_regulation_id(date_ranges, valid_user_client):
    """Test that an update to a regulation's `regulation_id` creates a new
    regulation, updates associated measures, and deletes old one."""
    regulation = factories.UIDraftRegulationFactory.create()
    associated_measures = factories.MeasureFactory.create_batch(
        2,
        generating_regulation=regulation,
        valid_between=date_ranges.normal,
    )

    form_data = {
        "regulation_usage": RegulationUsage.DRAFT_REGULATION,
        "regulation_group": regulation.regulation_group.pk,
        "start_date_0": regulation.valid_between.lower.day,
        "start_date_1": regulation.valid_between.lower.month,
        "start_date_2": regulation.valid_between.lower.year,
        "published_at_0": regulation.published_at.day,
        "published_at_1": regulation.published_at.month,
        "published_at_2": regulation.published_at.year + 1,
        "sequence_number": "1234",
        "approved": regulation.approved,
    }
    regulation_usage = form_data["regulation_usage"][0]
    publication_year = str(form_data["published_at_2"])[-2:]
    sequence_number = f"{form_data['sequence_number']:0>4}"
    new_regulation_id = f"{regulation_usage}{publication_year}{sequence_number}0"

    url = reverse(
        "regulation-ui-edit",
        kwargs={
            "role_type": regulation.role_type,
            "regulation_id": regulation.regulation_id,
        },
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    new_regulation = Regulation.objects.get(regulation_id=new_regulation_id)
    assert new_regulation.update_type == UpdateType.CREATE

    measure_sids = [measure.sid for measure in associated_measures]
    assert new_regulation.measure_set.filter(sid__in=measure_sids).exists()
    assert new_regulation.terminated_measures.filter(sid__in=measure_sids).exists()

    assert regulation.get_versions().last().update_type == UpdateType.DELETE
