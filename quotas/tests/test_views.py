from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tariffs_api import Endpoints
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from geo_areas.validators import AreaCode
from quotas import models
from quotas import validators
from quotas.views import QuotaList

pytestmark = pytest.mark.django_db


@pytest.fixture
def country1(date_ranges):
    return factories.GeographicalAreaFactory.create(
        area_code=AreaCode.COUNTRY,
        valid_between=date_ranges.no_end,
    )


@pytest.fixture
def country2(date_ranges):
    return factories.GeographicalAreaFactory.create(
        area_code=AreaCode.COUNTRY,
        valid_between=date_ranges.no_end,
    )


@pytest.fixture
def country3(date_ranges):
    return factories.GeographicalAreaFactory.create(
        area_code=AreaCode.COUNTRY,
        valid_between=date_ranges.no_end,
    )


@pytest.fixture
def geo_group1(country1, country2, country3, date_ranges):
    geo_group1 = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=geo_group1,
        member=country1,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=geo_group1,
        member=country2,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=geo_group1,
        member=country3,
        valid_between=date_ranges.no_end,
    )
    return geo_group1


@pytest.fixture
def geo_group2(date_ranges, country1, country2):
    geo_group2 = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=geo_group2,
        member=country1,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=geo_group2,
        member=country2,
        valid_between=date_ranges.no_end,
    )
    return geo_group2


@pytest.mark.parametrize(
    "factory",
    (factories.QuotaOrderNumberFactory,),
)
def test_quota_delete_form(factory, use_delete_form):
    use_delete_form(factory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_quota_detail_views(
    view,
    url_pattern,
    valid_user_client,
    mock_quota_api_no_data,
):
    """Verify that quota detail views are under the url quotas and don't return
    an error."""
    assert_model_view_renders(
        view,
        url_pattern,
        valid_user_client,
        override_models={"quotas.views.QuotaDefinitionCreate": models.QuotaOrderNumber},
    )


def test_quota_detail(valid_user_client, date_ranges, mock_quota_api_no_data):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
    )
    response = valid_user_client.get(
        reverse("quota-ui-detail", kwargs={"sid": quota.sid}),
    )
    assert response.status_code == 200


def test_quota_detail_api_response_no_results(
    valid_user_client,
    date_ranges,
    requests_mock,
):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
    )

    response_json = {"meta": {"pagination": {"total_count": 0}}}

    response = requests_mock.get(url=Endpoints.QUOTAS.value, json=response_json)

    response = valid_user_client.get(
        reverse("quota-ui-detail", kwargs={"sid": quota.sid}),
    )
    assert response.status_code == 200


def test_quota_detail_api_response_has_results(
    valid_user_client,
    date_ranges,
    requests_mock,
    quotas_json,
):
    quota_order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
    )
    quota_definition = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.future,
    )

    response = requests_mock.get(url=Endpoints.QUOTAS.value, json=quotas_json)

    response = valid_user_client.get(
        reverse("quota-ui-detail", kwargs={"sid": quota_order_number.sid}),
    )
    assert response.status_code == 200

    soup = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    rows_content = [
        el.text.strip()
        for el in soup.select(".quota__definition-details dl > div > dd")
    ]

    data = quotas_json["data"][0]

    assert len(rows_content) == 12
    assert rows_content[0] == str(quota_definition.sid)
    assert rows_content[1] == quota_definition.description
    assert rows_content[2] == data["attributes"]["status"]
    assert rows_content[3] == f"{quota_definition.valid_between.lower:%d %b %Y}"
    assert rows_content[4] == f"{quota_definition.valid_between.upper:%d %b %Y}"
    assert rows_content[5] == intcomma(quota_definition.initial_volume)
    assert rows_content[6] == intcomma(quota_definition.volume)
    assert rows_content[7] == intcomma(float(data["attributes"]["balance"]))
    assert rows_content[8] == (quota_definition.measurement_unit.abbreviation).title()
    assert rows_content[9] == f"{quota_definition.quota_critical_threshold}%"
    assert rows_content[10] == "Yes" if quota_definition.quota_critical else "No"
    assert rows_content[11] == str(quota_definition.maximum_precision)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[QuotaList],
    ),
    ids=view_urlpattern_ids,
)
def test_quota_list_view(view, url_pattern, valid_user_client):
    """Verify that quota list view is under the url quotas/ and doesn't return
    an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("search_filter", "checkbox", "valid"),
    [
        ("active_state", "active", True),
        ("active_state", "terminated", True),
        ("active_state", "invalid", False),
    ],
)
def test_quota_list_view_active_state_filter(
    valid_user_client,
    date_ranges,
    search_filter,
    checkbox,
    valid,
):
    active_quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
    )
    inactive_quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.earlier,
    )

    list_url = reverse("quota-ui-list")
    url = f"{list_url}?{search_filter}={checkbox}"

    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")
    search_results = soup.select("tbody .govuk-table__row")
    if valid:
        assert len(search_results) == 1
    else:
        assert len(search_results) == 0


def test_quota_ordernumber_api_list_view(valid_user_client, date_ranges):
    expected_results = [
        factories.QuotaOrderNumberFactory.create(
            valid_between=date_ranges.normal,
        ),
        factories.QuotaOrderNumberFactory.create(
            valid_between=date_ranges.earlier,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumber",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_quota_ordernumberorigin_api_list_view(valid_user_client, date_ranges):
    order_number = factories.QuotaOrderNumberFactory.create()
    expected_results = [
        factories.QuotaOrderNumberOriginFactory.create(
            valid_between=date_ranges.normal,
            order_number=order_number,
        ),
        factories.QuotaOrderNumberOriginFactory.create(
            valid_between=date_ranges.earlier,
            order_number=order_number,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumberorigin",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_ordernumberoriginexclusion_api_list_view(valid_user_client):
    order_number_origin = factories.QuotaOrderNumberOriginFactory.create()
    expected_results = [
        factories.QuotaOrderNumberOriginExclusionFactory.create(
            origin=order_number_origin,
        ),
        factories.QuotaOrderNumberOriginExclusionFactory.create(
            origin=order_number_origin,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumberoriginexclusion",
        "origin.sid",
        "origin.sid",
        expected_results,
        valid_user_client,
    )


def test_quota_definition_api_list_view(valid_user_client):
    expected_results = [factories.QuotaDefinitionFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotadefinition",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_association_api_list_view(valid_user_client):
    main_quota = factories.QuotaDefinitionFactory.create()

    expected_results = [
        factories.QuotaAssociationFactory.create(
            main_quota=main_quota,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaassociation",
        "main_quota.sid",
        "main_quota.sid",
        expected_results,
        valid_user_client,
    )


def test_quota_suspension_api_list_view(valid_user_client):
    expected_results = [factories.QuotaSuspensionFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotasuspension",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_blocking_api_list_view(valid_user_client):
    expected_results = [factories.QuotaBlockingFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotablocking",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_event_api_list_view(valid_user_client):
    quota_definition = factories.QuotaDefinitionFactory.create()
    expected_results = [
        factories.QuotaEventFactory.create(
            quota_definition=quota_definition,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaevent",
        "quota_definition.sid",
        "quota_definition.sid",
        expected_results,
        valid_user_client,
    )


def test_quota_definitions_list_200(valid_user_client, quota_order_number):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    assert response.status_code == 200


def test_quota_definitions_list_no_quota_data(valid_user_client, quota_order_number):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = (
        reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})
        + "?quota_type=sub_quotas"
    )

    with mock.patch(
        "common.tariffs_api.get_quota_definitions_data",
    ) as mock_get_quotas:
        response = valid_user_client.get(url)
        mock_get_quotas.assert_not_called()

    assert response.status_code == 200


def test_quota_definitions_list_sids(valid_user_client, quota_order_number):
    definitions = factories.QuotaDefinitionFactory.create_batch(
        5,
        order_number=quota_order_number,
    )

    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    sids = {
        int(element.text)
        for element in soup.select(
            "table > tr > td:first-child > details > summary > span",
        )
    }
    object_sids = {d.sid for d in definitions}
    assert not sids.difference(object_sids)


def test_quota_definitions_list_title(valid_user_client, quota_order_number):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    title = soup.select("h1")[0].text
    assert title == f"Quota ID: {quota_order_number.order_number} - Data"


def test_quota_definitions_list_current_versions(
    valid_user_client,
    approved_transaction,
):
    quota_order_number = factories.QuotaOrderNumberFactory()
    old_quota_definition = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        transaction=approved_transaction,
    )
    old_quota_definition2 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        transaction=approved_transaction,
    )

    with override_current_transaction(approved_transaction):
        assert quota_order_number.definitions.current().count() == 2

    new_version = old_quota_definition.new_version(
        update_type=UpdateType.DELETE,
        transaction=approved_transaction,
        workbasket=approved_transaction.workbasket,
    )

    with override_current_transaction(approved_transaction):
        assert quota_order_number.definitions.current().count() == 1

    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    num_definitions = len(
        soup.select("table tr > td:first-child > details > summary > span"),
    )
    assert num_definitions == 1


def test_quota_definitions_list_current_measures(
    valid_user_client,
    date_ranges,
    mock_quota_api_no_data,
):
    quota_order_number = factories.QuotaOrderNumberFactory()
    old_measures = factories.MeasureFactory.create_batch(
        5,
        valid_between=date_ranges.adjacent_earlier_big,
        order_number=quota_order_number,
    )
    current_measures = factories.MeasureFactory.create_batch(
        4,
        valid_between=date_ranges.normal,
        order_number=quota_order_number,
    )

    url = reverse("quota-ui-detail", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    num_measures = len(
        soup.select("#measures table tbody > tr > td:first-child"),
    )
    assert num_measures == 4


def test_quota_definitions_list_edit_delete(
    valid_user_client,
    date_ranges,
    mock_quota_api_no_data,
):
    quota_order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    definition1 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.earlier,
    )
    definition2 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.normal,
    )
    definition3 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.later,
    )

    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    actions = [item.text for item in soup.select("table tbody tr td:last-child")]
    sids = {
        item.text.strip()
        for item in soup.select("table tbody tr td:nth-child(1) summary span")
    }
    start_dates = {item.text for item in soup.select("table tbody tr td:nth-child(3)")}
    definitions = {definition1, definition2, definition3}

    assert start_dates == {f"{d.valid_between.lower:%d %b %Y}" for d in definitions}
    assert sids == {str(d.sid) for d in definitions}
    assert "Edit" in actions[0]
    assert "Edit" in actions[1]
    assert "Edit" in actions[2]
    assert "Delete" in actions[2]


def test_quota_definitions_list_sort_by_start_date(
    valid_user_client,
    date_ranges,
):
    """Test that quota definitions list can be sorted by start date in ascending
    or descending order."""
    quota_order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    definition1 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.normal,
    )
    definition2 = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.later,
    )
    url = reverse("quota-definitions", kwargs={"sid": quota_order_number.sid})

    response = valid_user_client.get(f"{url}?sort_by=valid_between&ordered=asc")
    assert response.status_code == 200
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    definition_sids = [
        int(row.text)
        for row in page.select(".govuk-table tbody tr td:first-child details summary")
    ]
    assert definition_sids == [definition1.sid, definition2.sid]

    response = valid_user_client.get(f"{url}?sort_by=valid_between&ordered=desc")
    assert response.status_code == 200
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    definition_sids = [
        int(row.text)
        for row in page.select(".govuk-table tbody tr td:first-child details summary")
    ]
    assert definition_sids == [definition2.sid, definition1.sid]


def test_quota_detail_blocking_periods_tab(
    valid_user_client,
    date_ranges,
    mock_quota_api_no_data,
):
    quota_order_number = factories.QuotaOrderNumberFactory()
    current_definition = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.normal,
    )
    blocking_period = factories.QuotaBlockingFactory.create(
        quota_definition=current_definition,
        description="Test description",
        valid_between=date_ranges.normal,
    )

    expected_data = {
        "Quota blocking period SID": str(blocking_period.sid),
        "Blocking start date": f"{blocking_period.valid_between.lower:%d %b %Y}",
        "Blocking end date": f"{blocking_period.valid_between.upper:%d %b %Y}",
        "Blocking period type": str(blocking_period.blocking_period_type),
        "Description": blocking_period.description,
    }

    url = reverse("quota-ui-detail", args=[quota_order_number.sid])
    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    rows = soup.select(".quota__blocking-periods__content > dl > div > dd")
    assert len(rows) == 5

    for i, value in enumerate(expected_data.values()):
        assert value in rows[i].text


def test_quota_detail_suspension_periods_tab(
    valid_user_client,
    date_ranges,
    mock_quota_api_no_data,
):
    quota_order_number = factories.QuotaOrderNumberFactory()
    current_definition = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.normal,
    )
    suspension_period = factories.QuotaSuspensionFactory.create(
        quota_definition=current_definition,
        description="Test description",
        valid_between=date_ranges.normal,
    )

    expected_data = {
        "Quota Suspension period SID": str(suspension_period.sid),
        "Suspension start date": f"{suspension_period.valid_between.lower:%d %b %Y}",
        "Suspension end date": f"{suspension_period.valid_between.upper:%d %b %Y}",
        "Description": suspension_period.description,
    }

    url = reverse("quota-ui-detail", args=[quota_order_number.sid])
    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    rows = soup.select(".quota__suspension-periods__content > dl > div > dd")
    assert len(rows) == 4

    for i, value in enumerate(expected_data.values()):
        assert value in rows[i].text


def test_quota_detail_sub_quota_tab(
    valid_user_client,
    date_ranges,
    mock_quota_api_no_data,
):
    quota_order_number = factories.QuotaOrderNumberFactory()
    current_definition = factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=date_ranges.normal,
    )
    quota_associations = factories.QuotaAssociationFactory.create_batch(
        2,
        main_quota=current_definition,
    )

    url = reverse("quota-ui-detail", args=[quota_order_number.sid])
    response = valid_user_client.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    order_numbers = {
        int(element.text)
        for element in soup.select(
            ".quota__sub-quotas__content > table > tbody > tr > td:first-child",
        )
    }
    expected_order_numbers = {
        int(qa.sub_quota.order_number.order_number) for qa in quota_associations
    }
    assert not order_numbers.difference(expected_order_numbers)


def test_current_quota_order_number_returned(
    workbasket,
    valid_user_client,
    mock_quota_api_no_data,
    date_ranges,
):
    old_version = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.starts_1_month_ago_no_end,
    )
    current_version = old_version.new_version(
        workbasket,
        valid_between=date_ranges.starts_1_month_ago_to_1_month_ahead,
    )
    factories.QuotaDefinitionFactory.create(
        order_number=current_version,
        valid_between=date_ranges.normal,
    )
    url = reverse("quota-definitions", kwargs={"sid": current_version.sid})
    response = valid_user_client.get(url)

    assert response.status_code == 200


def test_quota_edit_origin_new_versions(valid_user_client):
    quota = factories.QuotaOrderNumberFactory.create()
    form_data = {
        "category": validators.QuotaCategory.AUTONOMOUS.value,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
    }
    valid_user_client.post(
        reverse("quota-ui-edit", kwargs={"sid": quota.sid}),
        form_data,
    )

    tx = Transaction.objects.last()

    quota = models.QuotaOrderNumber.objects.approved_up_to_transaction(tx).get(
        sid=quota.sid,
    )
    origins = models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(
        tx,
    ).filter(
        order_number=quota,
    )

    assert origins.exists()
    assert origins.count() == 1
    assert origins.first().version_group != quota.version_group


def test_quota_edit_origin_exclusions(
    valid_user_client,
    approved_transaction,
    geo_group1,
    geo_group2,
    country1,
    country2,
    country3,
    date_ranges,
):
    """Checks that members of geo groups are added individually as
    exclusions."""
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    origin = models.QuotaOrderNumberOrigin.objects.last()

    form_data = {
        "start_date_0": origin.valid_between.lower.day,
        "start_date_1": origin.valid_between.lower.month,
        "start_date_2": origin.valid_between.lower.year,
        "geographical_area": geo_group1.id,
        "quota-origin-exclusions-formset-__prefix__-exclusion": geo_group2.id,
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-edit", kwargs={"sid": origin.sid}),
        form_data,
    )

    assert response.status_code == 302

    tx = Transaction.objects.last()

    origin = models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(tx).get(
        sid=origin.sid,
    )

    # geo_group1 contains country1, country2, country3
    # geo_group2 contains country1, country2

    # we're excluding geo_group2 from geo_group1
    # geo_group2 has 2 members
    # so we should have 2 exclusions
    assert origin.excluded_areas.all().count() == 2

    # if we exclude geo_group2
    # we exclude country1 and country2
    assert country1 in origin.excluded_areas.all()
    assert country2 in origin.excluded_areas.all()
    assert country3 not in origin.excluded_areas.all()


def test_quota_edit_origin_exclusions_remove(
    valid_user_client,
    approved_transaction,
    geo_group1,
    country1,
    date_ranges,
):
    """Checks that exclusions are removed from a quota origin."""

    origin = factories.QuotaOrderNumberOriginFactory.create(
        transaction=approved_transaction,
        geographical_area=geo_group1,
        valid_between=date_ranges.normal,
    )
    factories.QuotaOrderNumberOriginExclusionFactory.create(
        transaction=approved_transaction,
        excluded_geographical_area=country1,
        origin=origin,
    )
    quota = models.QuotaOrderNumber.objects.last()

    form_data = {
        "start_date_0": origin.valid_between.lower.day,
        "start_date_1": origin.valid_between.lower.month,
        "start_date_2": origin.valid_between.lower.year,
        "geographical_area": geo_group1.id,
        "quota-origin-exclusions-formset-__prefix__-exclusion": "",
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-edit", kwargs={"sid": origin.sid}),
        form_data,
    )

    assert response.status_code == 302

    tx = Transaction.objects.last()

    updated_quota = models.QuotaOrderNumber.objects.approved_up_to_transaction(tx).get(
        sid=quota.sid,
    )
    updated_origin = (
        updated_quota.quotaordernumberorigin_set.approved_up_to_transaction(tx)
    ).first()

    assert (
        updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 0
    )

    assert (
        country1
        not in updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        )
    )


def test_update_quota_definition_page_200(valid_user_client):
    quota_definition = factories.QuotaDefinitionFactory.create()
    url = reverse("quota_definition-ui-edit", kwargs={"sid": quota_definition.sid})
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_update_quota_definition(valid_user_client, date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    url = reverse("quota_definition-ui-edit", kwargs={"sid": quota_definition.sid})
    measurement_unit = factories.MeasurementUnitFactory()

    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Lorem ipsum.",
        "volume": "80601000.000",
        "initial_volume": "80601000.000",
        "measurement_unit": measurement_unit.pk,
        "measurement_unit_qualifier": "",
        "quota_critical_threshold": "90",
        "quota_critical": "False",
    }

    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    assert response.url == reverse(
        "quota_definition-ui-confirm-update",
        kwargs={"sid": quota_definition.sid},
    )

    tx = Transaction.objects.last()

    updated_definition = models.QuotaDefinition.objects.approved_up_to_transaction(
        tx,
    ).get(
        sid=quota_definition.sid,
    )

    assert updated_definition.valid_between == date_ranges.normal
    assert updated_definition.description == "Lorem ipsum."
    assert updated_definition.volume == 80601000.000
    assert updated_definition.initial_volume == 80601000.000
    assert updated_definition.measurement_unit == measurement_unit
    assert updated_definition.quota_critical_threshold == 90
    assert updated_definition.quota_critical == False


def test_delete_quota_definition_page_200(valid_user_client):
    quota_definition = factories.QuotaDefinitionFactory.create()
    url = reverse("quota_definition-ui-delete", kwargs={"sid": quota_definition.sid})
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_delete_quota_definition(valid_user_client, date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    url = reverse("quota_definition-ui-delete", kwargs={"sid": quota_definition.sid})

    response = valid_user_client.post(url, {"submit": "Delete"})
    assert response.status_code == 302
    assert response.url == reverse(
        "quota_definition-ui-confirm-delete",
        kwargs={"sid": quota_definition.order_number.sid},
    )

    tx = Transaction.objects.last()

    assert tx.workbasket.tracked_models.first().update_type == UpdateType.DELETE

    confirm_response = valid_user_client.get(response.url)

    soup = BeautifulSoup(
        confirm_response.content.decode(response.charset),
        "html.parser",
    )
    h1 = soup.select("h1")[0]

    assert (
        h1.text.strip()
        == f"Quota definition period {quota_definition.sid} has been deleted"
    )


def test_quota_create_origin(
    valid_user_client,
    approved_transaction,
    geo_group1,
    date_ranges,
):
    """Checks that a quota origin is created for a geo area."""
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    form_data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "geographical_area": geo_group1.id,
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-create", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 302

    tx = Transaction.objects.last()
    origin = models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(tx).get(
        sid=response.url.split("/")[2],
    )

    assert origin.geographical_area == geo_group1


def test_quota_create_origin_outwith_quota_period(
    valid_user_client,
    approved_transaction,
    geo_group1,
    date_ranges,
):
    """Checks that for a quota that you cannot create a quota origin that lies
    outside the quota order numbers validity period."""
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    form_data = {
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
        "geographical_area": geo_group1.id,
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-create", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "lxml")

    a_tags = soup.select("ul.govuk-list.govuk-error-summary__list a")

    assert a_tags[0].text == (
        "The validity period of the geographical area must span the validity "
        "period of the quota order number origin."
    )


def test_quota_create_origin_no_overlapping_origins(
    valid_user_client,
    approved_transaction,
    geo_group1,
    date_ranges,
):
    """Checks that for a quota and geo area, that you cannot create a quota
    origin that overlaps in time with the same geo area."""
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=geo_group1,
        valid_between=date_ranges.no_end,
        order_number=quota,
    )

    form_data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "geographical_area": geo_group1.id,
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-create", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "lxml")

    a_tags = soup.select("ul.govuk-list.govuk-error-summary__list a")

    assert a_tags[0].text == (
        "There may be no overlap in time of two quota order number origins with "
        "the same quota order number SID and geographical area id."
    )


@pytest.mark.django_db
def test_quota_order_number_and_origin_edit_create_view(
    valid_user_client, date_ranges, approved_transaction, geo_group1, geo_group2
):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    origin = models.QuotaOrderNumberOrigin.objects.last()

    form_data = {
        "start_date_0": origin.valid_between.lower.day,
        "start_date_1": origin.valid_between.lower.month,
        "start_date_2": origin.valid_between.lower.year,
        "geographical_area": geo_group1.id,
        "quota-origin-exclusions-formset-__prefix__-exclusion": geo_group2.id,
        "submit": "Save",
    }

    response = valid_user_client.post(
        reverse("quota_order_number_origin-ui-edit-create", kwargs={"sid": origin.sid}),
        form_data,
    )

    assert response.status_code == 302

    response = valid_user_client.get(
        reverse("quota-ui-edit-create", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_quota_order_number_update_view(
    valid_user_client, date_ranges, approved_transaction, geo_group1, geo_group2
):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    origin = models.QuotaOrderNumberOrigin.objects.last()

    form_data = {
        "start_date_0": origin.valid_between.lower.day,
        "start_date_1": origin.valid_between.lower.month,
        "start_date_2": origin.valid_between.lower.year,
        "geographical_area": geo_group1.id,
        "quota-origin-exclusions-formset-__prefix__-exclusion": geo_group2.id,
        "submit": "Save",
    }

    response = valid_user_client.get(
        reverse("quota-ui-edit-update", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200
