import datetime

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.urls import reverse

from common.models import Transaction
from common.models.utils import override_current_transaction
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
from footnotes.models import FootnoteDescription
from footnotes.views import FootnoteDetailMeasures
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


def test_footnote_description_create(valid_user_client_workbasket):
    """Tests that `FootnoteDescriptionCreate` view returns 200 and creates a
    description for the current version of an footnote."""
    footnote = factories.FootnoteFactory.create(description=None)
    new_version = footnote.new_version(workbasket=footnote.transaction.workbasket)
    assert not FootnoteDescription.objects.exists()

    url = reverse(
        "footnote-ui-description-create",
        kwargs={
            "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
            "footnote_id": footnote.footnote_id,
        },
    )
    data = {
        "description": "new test description",
        "described_footnote": new_version.pk,
        "validity_start_0": 1,
        "validity_start_1": 1,
        "validity_start_2": 2023,
    }

    with override_current_transaction(Transaction.objects.last()):
        get_response = valid_user_client_workbasket.get(url)
        assert get_response.status_code == 200

        post_response = valid_user_client_workbasket.post(url, data)
        assert post_response.status_code == 302

    assert FootnoteDescription.objects.filter(described_footnote=new_version).exists()


def test_footnote_detail_measures_view(valid_user_client):
    """Test that `FootnoteDetailMeasures` view returns 200 and renders actions
    link and other tabs."""
    footnote = factories.FootnoteFactory.create()
    url_kwargs = {
        "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
        "footnote_id": footnote.footnote_id,
    }
    details_tab_url = reverse("footnote-ui-detail", kwargs=url_kwargs)
    descriptions_tab_url = reverse("footnote-ui-detail-descriptions", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "footnote-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("footnote-ui-detail-measures", kwargs=url_kwargs)

    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }
    response = valid_user_client.get(measures_tab_url)
    assert response.status_code == 200

    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    actions = page.find("h2", text="Actions").find_next("a")
    assert actions.text == "View in find and edit measures"
    assert (
        actions.attrs["href"] == f"{reverse('measure-ui-list')}?footnote={footnote.id}"
    )


def test_footnote_detail_measures_view_lists_measures(valid_user_client):
    """Test that `FootnoteDetailMeasures` view displays a paginated list of
    measures for a footnote."""
    footnote = factories.FootnoteFactory.create()
    measures = []
    for measure_with_footnote in range(21):
        measure = factories.MeasureFactory.create()
        factories.FootnoteAssociationMeasureFactory.create(
            footnoted_measure=measure,
            associated_footnote=footnote,
        )
        measures.append(measure)
    url = reverse(
        "footnote-ui-detail-measures",
        kwargs={
            "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
            "footnote_id": footnote.footnote_id,
        },
    )
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    table_rows = page.select(".govuk-table tbody tr")
    assert len(table_rows) == FootnoteDetailMeasures.paginate_by

    table_measure_sids = {
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    }
    assert table_measure_sids.issubset({m.sid for m in measures})

    assert page.find("nav", class_="pagination").find_next("a", href="?page=2")


def test_footnote_detail_measures_view_sorting_commodity(valid_user_client):
    """Test that measures listed on `FootnoteDetailMeasures` view can be sorted
    by commodity code in ascending or descending order."""
    footnote = factories.FootnoteFactory.create()
    measures = []
    for measure_with_footnote in range(3):
        measure = factories.MeasureFactory.create()
        factories.FootnoteAssociationMeasureFactory.create(
            footnoted_measure=measure,
            associated_footnote=footnote,
        )
        measures.append(measure)
    commodity_codes = [measure.goods_nomenclature.item_id for measure in measures]
    url = reverse(
        "footnote-ui-detail-measures",
        kwargs={
            "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
            "footnote_id": footnote.footnote_id,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    assert table_commodity_codes == commodity_codes

    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    commodity_codes.reverse()
    print(table_commodity_codes)
    print(commodity_codes)
    assert table_commodity_codes == commodity_codes


def test_footnote_detail_measures_view_sorting_start_date(
    date_ranges,
    valid_user_client,
):
    """Test that measures listed on `FootnoteDetailMeasures` view can be sorted
    by start date in ascending or descending order."""
    footnote = factories.FootnoteFactory.create()
    measures = [
        factories.MeasureFactory.create(
            valid_between=date_ranges.earlier,
        ),
        factories.MeasureFactory.create(
            valid_between=date_ranges.normal,
        ),
        factories.MeasureFactory.create(
            valid_between=date_ranges.later,
        ),
    ]
    for measure in measures:
        factories.FootnoteAssociationMeasureFactory.create(
            footnoted_measure=measure,
            associated_footnote=footnote,
        )
    url = reverse(
        "footnote-ui-detail-measures",
        kwargs={
            "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
            "footnote_id": footnote.footnote_id,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measures[0].sid, measures[1].sid, measures[2].sid]

    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measures[2].sid, measures[1].sid, measures[0].sid]


def test_footnote_detail_version_control_view(valid_user_client):
    """Test that `FootnoteDetailVersionControl` view returns 200 and renders
    table content and other tabs."""
    footnote = factories.FootnoteFactory.create()
    footnote.new_version(footnote.transaction.workbasket)

    url_kwargs = {
        "footnote_type__footnote_type_id": footnote.footnote_type.footnote_type_id,
        "footnote_id": footnote.footnote_id,
    }
    details_tab_url = reverse("footnote-ui-detail", kwargs=url_kwargs)
    descriptions_tab_url = reverse("footnote-ui-detail-descriptions", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "footnote-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("footnote-ui-detail-measures", kwargs=url_kwargs)

    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }

    response = valid_user_client.get(version_control_tab_url)
    assert response.status_code == 200
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    table_rows = page.select("table > tbody > tr")
    assert len(table_rows) == 2

    update_types = {
        update.text for update in page.select("table > tbody > tr > td:first-child")
    }
    assert update_types == {"Create", "Update"}
