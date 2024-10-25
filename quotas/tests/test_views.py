from typing import OrderedDict
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.serializers import serialize_date
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
from quotas.forms import QuotaSuspensionType
from quotas.views import DuplicateDefinitionsWizard
from quotas.views import QuotaList
from quotas.wizard import QuotaDefinitionDuplicatorSessionStorage

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
    client_with_current_workbasket,
    mock_quota_api_no_data,
):
    """Verify that quota detail views are under the url quotas and don't return
    an error."""
    assert_model_view_renders(
        view,
        url_pattern,
        client_with_current_workbasket,
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


def test_quota_definitions_list_200(client_with_current_workbasket, quota_order_number):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(url)

    assert response.status_code == 200


def test_quota_definitions_list_no_quota_data(
    client_with_current_workbasket,
    quota_order_number,
):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = (
        reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})
        + "?quota_type=sub_quotas"
    )

    with mock.patch(
        "common.tariffs_api.get_quota_definitions_data",
    ) as mock_get_quotas:
        response = client_with_current_workbasket.get(url)
        mock_get_quotas.assert_not_called()

    assert response.status_code == 200


def test_quota_definitions_list_sids(
    client_with_current_workbasket,
    quota_order_number,
):
    definitions = factories.QuotaDefinitionFactory.create_batch(
        5,
        order_number=quota_order_number,
    )

    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    sids = {
        int(element.text)
        for element in soup.select(
            "table > tr > td:first-child > details > summary > span",
        )
    }
    object_sids = {d.sid for d in definitions}
    assert not sids.difference(object_sids)


def test_quota_definitions_list_title(
    client_with_current_workbasket,
    quota_order_number,
):
    factories.QuotaDefinitionFactory.create_batch(5, order_number=quota_order_number)

    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(url)

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    title = soup.select("h1")[0].text
    assert title == f"Quota ID: {quota_order_number.order_number} - Data"


def test_quota_definitions_list_current_versions(
    client_with_current_workbasket,
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

    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(url)

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
    client_with_current_workbasket,
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

    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(url)

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
    client_with_current_workbasket,
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
    url = reverse("quota_definition-ui-list", kwargs={"sid": quota_order_number.sid})

    response = client_with_current_workbasket.get(
        f"{url}?sort_by=valid_between&ordered=asc",
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    definition_sids = [
        int(row.text)
        for row in page.select(".govuk-table tbody tr td:first-child details summary")
    ]
    assert definition_sids == [definition1.sid, definition2.sid]

    response = client_with_current_workbasket.get(
        f"{url}?sort_by=valid_between&ordered=desc",
    )
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
    session_request_with_workbasket,
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
    client_with_current_workbasket,
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
    url = reverse("quota_definition-ui-list", kwargs={"sid": current_version.sid})
    response = client_with_current_workbasket.get(url)

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
    client_with_current_workbasket,
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

    response = client_with_current_workbasket.post(
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
    client_with_current_workbasket,
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

    response = client_with_current_workbasket.post(
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


def test_update_quota_definition_page_200(client_with_current_workbasket):
    quota_definition = factories.QuotaDefinitionFactory.create()
    url = reverse("quota_definition-ui-edit", kwargs={"sid": quota_definition.sid})
    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200


def test_update_quota_definition(client_with_current_workbasket, date_ranges):
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

    response = client_with_current_workbasket.post(url, data)
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


def test_delete_quota_definition_page_200(client_with_current_workbasket):
    quota_definition = factories.QuotaDefinitionFactory.create()
    url = reverse("quota_definition-ui-delete", kwargs={"sid": quota_definition.sid})
    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200


def test_delete_quota_definition(client_with_current_workbasket, date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    url = reverse("quota_definition-ui-delete", kwargs={"sid": quota_definition.sid})

    response = client_with_current_workbasket.post(url, {"submit": "Delete"})
    assert response.status_code == 302
    assert response.url == reverse(
        "quota_definition-ui-confirm-delete",
        kwargs={"sid": quota_definition.order_number.sid},
    )

    tx = Transaction.objects.last()

    assert tx.workbasket.tracked_models.first().update_type == UpdateType.DELETE

    confirm_response = client_with_current_workbasket.get(response.url)

    soup = BeautifulSoup(
        confirm_response.content.decode(response.charset),
        "html.parser",
    )
    h1 = soup.select("h1")[0]

    assert (
        h1.text.strip()
        == f"Quota definition period {quota_definition.sid} has been deleted"
    )


def test_delete_quota_definition_deletes_associations(
    client_with_current_workbasket,
    date_ranges,
):
    """Test that when a quota definition is deleted that all linked associations
    are deleted too."""
    main_quota = factories.QuotaDefinitionFactory.create(
        sid=1,
        valid_between=date_ranges.future,
        measurement_unit=factories.MeasurementUnitFactory(),
    )
    for i in range(2, 6):
        factories.QuotaAssociationFactory.create(
            sub_quota=factories.QuotaDefinitionFactory.create(
                sid=i,
                valid_between=date_ranges.future,
            ),
            main_quota=main_quota,
        )

    # Delete a sub-quota and verify the related association gets deleted too
    sub_quota_2 = models.QuotaDefinition.objects.all().get(sid=2)
    url = reverse("quota_definition-ui-delete", kwargs={"sid": sub_quota_2.sid})
    client_with_current_workbasket.post(url, {"submit": "Delete"})

    sub_quota_2_new_version = models.QuotaDefinition.objects.all().filter(sid=2).last()
    association_2_new_version = (
        models.QuotaAssociation.objects.all().filter(sub_quota__sid=2).last()
    )
    assert sub_quota_2_new_version.update_type == UpdateType.DELETE
    assert association_2_new_version.update_type == UpdateType.DELETE

    # Delete the main_quota and verify that all remaining associations get deleted too
    url = reverse("quota_definition-ui-delete", kwargs={"sid": main_quota.sid})
    client_with_current_workbasket.post(url, {"submit": "Delete"})

    main_quota_new_version = models.QuotaDefinition.objects.all().filter(sid=1).last()
    association_new_versions = [
        models.QuotaAssociation.objects.all().filter(sub_quota__sid=i).last()
        for i in range(3, 6)
    ]

    deleted_associations = models.QuotaAssociation.objects.all().filter(
        update_type=UpdateType.DELETE,
    )
    assert main_quota_new_version.update_type == UpdateType.DELETE
    for association in association_new_versions:
        assert association in deleted_associations


def test_quota_create_with_origins(
    client_with_current_workbasket,
    date_ranges,
):
    # make a geo group with 3 member countries
    country1 = factories.CountryFactory.create()
    country2 = factories.CountryFactory.create()
    country3 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )
    membership2 = factories.GeographicalMembershipFactory.create(
        member=country2,
        geo_group=geo_group,
    )
    membership3 = factories.GeographicalMembershipFactory.create(
        member=country3,
        geo_group=geo_group,
    )

    data = {
        "order_number": "054000",
        "mechanism": validators.AdministrationMechanism.LICENSED.value,
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "origins-0-pk": "",
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        "origins-0-exclusions-0-pk": "",
        "origins-0-exclusions-0-geographical_area": membership1.member.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-create")
    response = client_with_current_workbasket.post(url, data)

    tx = Transaction.objects.last()
    new_quota = models.QuotaOrderNumber.objects.approved_up_to_transaction(tx).last()

    assert response.status_code == 302
    assert response.url == reverse(
        "quota-ui-confirm-create",
        kwargs={"sid": new_quota.sid},
    )

    assert new_quota.origins.approved_up_to_transaction(tx).count() == 1
    new_origin = new_quota.quotaordernumberorigin_set.approved_up_to_transaction(
        tx,
    ).first()
    assert {
        e.excluded_geographical_area.sid
        for e in new_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        )
    } == {
        membership1.member.sid,
    }


def test_quota_create_origin(
    client_with_current_workbasket,
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

    response = client_with_current_workbasket.post(
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
    client_with_current_workbasket,
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

    response = client_with_current_workbasket.post(
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
    client_with_current_workbasket,
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

    response = client_with_current_workbasket.post(
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
    client_with_current_workbasket,
    date_ranges,
    approved_transaction,
    geo_group1,
    geo_group2,
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

    response = client_with_current_workbasket.post(
        reverse("quota_order_number_origin-ui-edit-create", kwargs={"sid": origin.sid}),
        form_data,
    )

    assert response.status_code == 302

    response = client_with_current_workbasket.get(
        reverse("quota-ui-edit-create", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_quota_order_number_update_view(
    client_with_current_workbasket,
    date_ranges,
    approved_transaction,
    geo_group1,
    geo_group2,
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

    response = client_with_current_workbasket.get(
        reverse("quota-ui-edit-update", kwargs={"sid": quota.sid}),
        form_data,
    )

    assert response.status_code == 200


def test_create_new_quota_definition(
    client_with_current_workbasket,
    approved_transaction,
    date_ranges,
    mock_quota_api_no_data,
):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    measurement_unit = factories.MeasurementUnitFactory.create()

    form_data = {
        "start_date_0": date_ranges.later.lower.day,
        "start_date_1": date_ranges.later.lower.month,
        "start_date_2": date_ranges.later.lower.year,
        "description": "Lorem ipsum",
        "volume": "1000000",
        "initial_volume": "1000000",
        "quota_critical_threshold": "90",
        "quota_critical": "False",
        "order_number": quota.pk,
        "maximum_precision": "3",
        "measurement_unit": measurement_unit.pk,
    }

    # sanity check
    assert not models.QuotaDefinition.objects.all()

    url = reverse("quota_definition-ui-create", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, form_data)
    assert response.status_code == 302

    created_definition = models.QuotaDefinition.objects.last()
    assert response.url == reverse(
        "quota_definition-ui-confirm-create",
        kwargs={"sid": created_definition.sid},
    )

    # check definition is listed on quota order number's definition tab
    url = reverse("quota-ui-detail", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.get(url)
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    definitions_tab = soup.find(id="definition-details")
    details = [
        dd.text.strip() for dd in definitions_tab.select(".govuk-summary-list dd")
    ]
    assert f"{created_definition.sid}" in details
    assert created_definition.description in details
    assert created_definition.valid_between.lower.strftime("%d %b %Y") in details
    assert intcomma(created_definition.initial_volume) in details
    assert intcomma(created_definition.volume) in details
    # critical state
    assert "No" in details
    assert f"{created_definition.quota_critical_threshold}%" in details
    assert created_definition.measurement_unit.abbreviation.capitalize() in details


def test_create_new_quota_definition_business_rule_violation(
    client_with_current_workbasket,
    approved_transaction,
    date_ranges,
):
    quota = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.no_end,
        transaction=approved_transaction,
    )

    measurement_unit = factories.MeasurementUnitFactory.create()

    form_data = {
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
        "description": "Lorem ipsum",
        "volume": "1000000",
        "initial_volume": "1000000",
        "quota_critical_threshold": "90",
        "quota_critical": "False",
        "order_number": quota.pk,
        "maximum_precision": "3",
        "measurement_unit": measurement_unit.pk,
    }

    url = reverse("quota_definition-ui-create", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, form_data)

    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    assert soup.select(".govuk-error-summary")
    errors = [el.text.strip() for el in soup.select(".govuk-error-summary__list li")]
    assert (
        "The validity period of the quota definition must be spanned by one of the validity periods of the referenced quota order number."
        in errors
    )


@pytest.mark.django_db
def test_get_200_quota_order_number_create(
    client_with_current_workbasket,
    geo_group1,
    geo_group2,
):
    response = client_with_current_workbasket.get(reverse("quota-ui-create"))
    assert response.status_code == 200


def test_get_200_quota_edit(client_with_current_workbasket):
    quota = factories.QuotaOrderNumberFactory.create()
    response = client_with_current_workbasket.get(
        reverse("quota-ui-edit", kwargs={"sid": quota.sid}),
    )
    assert response.status_code == 200


def test_get_200_quota_origins_edit(client_with_current_workbasket):
    quota = factories.QuotaOrderNumberFactory.create()
    origin = quota.quotaordernumberorigin_set.approved_up_to_transaction(
        quota.transaction,
    ).first()
    response = client_with_current_workbasket.get(
        reverse("quota_order_number_origin-ui-edit", kwargs={"sid": origin.sid}),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_quota_order_number_create_errors_required(
    client_with_current_workbasket,
    geo_group1,
    geo_group2,
):
    form_data = {
        "submit": "Save",
    }
    response = client_with_current_workbasket.post(
        reverse("quota-ui-create"),
        form_data,
    )

    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    errors = {e.text for e in soup.select(".govuk-error-summary__list li a")}

    assert {
        "Enter the order number",
        "Choose the category",
        "Choose the mechanism",
        "Enter the day, month and year",
    } == errors


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_number,category,mechanism,exp_error",
    [
        (
            "050000",
            validators.QuotaCategory.SAFEGUARD.value,
            validators.AdministrationMechanism.LICENSED.value,
            "Mechanism cannot be set to licensed for safeguard quotas",
        ),
        (
            "050000",
            validators.QuotaCategory.WTO.value,
            validators.AdministrationMechanism.LICENSED.value,
            "The order number for licensed quotas must begin with 054",
        ),
        (
            "050000",
            validators.QuotaCategory.SAFEGUARD.value,
            validators.AdministrationMechanism.FCFS.value,
            "The order number for safeguard quotas must begin with 058",
        ),
    ],
)
def test_quota_order_number_create_validation(
    order_number,
    mechanism,
    category,
    exp_error,
    client_with_current_workbasket,
    date_ranges,
    geo_group1,
    geo_group2,
):
    form_data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "order_number": order_number,
        "mechanism": mechanism,
        "category": category,
        "submit": "Save",
    }
    response = client_with_current_workbasket.post(
        reverse("quota-ui-create"),
        form_data,
    )

    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    errors = {e.text for e in soup.select(".govuk-error-summary__list li a")}

    assert exp_error in errors


@pytest.mark.django_db
def test_quota_order_number_create_success(
    client_with_current_workbasket,
    date_ranges,
    geo_group1,
    geo_group2,
):
    form_data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "order_number": "054000",
        "mechanism": validators.AdministrationMechanism.LICENSED.value,
        "category": validators.QuotaCategory.WTO.value,
        "submit": "Save",
    }
    response = client_with_current_workbasket.post(
        reverse("quota-ui-create"),
        form_data,
    )

    assert response.status_code == 302

    quota = models.QuotaOrderNumber.objects.last()

    assert response.url == reverse("quota-ui-confirm-create", kwargs={"sid": quota.sid})

    response2 = client_with_current_workbasket.get(response.url)

    soup = BeautifulSoup(response2.content.decode(response2.charset), "html.parser")

    assert soup.find("h1").text.strip() == f"Quota: {quota.order_number}"


def test_quota_update_existing_origins_no_submitted_origins(
    client_with_current_workbasket,
    date_ranges,
):
    quota = factories.QuotaOrderNumberFactory.create(
        category=0,
        valid_between=date_ranges.big_no_end,
    )
    factories.QuotaOrderNumberOriginFactory.create(order_number=quota)
    new_origin = factories.QuotaOrderNumberOriginFactory.create(order_number=quota)
    tx = new_origin.transaction
    (
        origin1,
        origin2,
        origin3,
    ) = quota.quotaordernumberorigin_set.approved_up_to_transaction(tx)

    # sanity check
    assert quota.quotaordernumberorigin_set.count() == 3

    data = {
        "start_date_0": quota.valid_between.lower.day,
        "start_date_1": quota.valid_between.lower.month,
        "start_date_2": quota.valid_between.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": "1",  # update category
        "submit": "Save",
    }
    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    tx = Transaction.objects.last()
    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        .filter(sid=quota.sid)
        .first()
    )
    assert updated_quota.category == 1
    assert updated_quota.valid_between == quota.valid_between

    assert updated_quota.origins.approved_up_to_transaction(tx).count() == 3
    assert {o.sid for o in updated_quota.origins.approved_up_to_transaction(tx)} == {
        origin1.geographical_area.sid,
        origin2.geographical_area.sid,
        origin3.geographical_area.sid,
    }


def test_quota_update_existing_origins(client_with_current_workbasket, date_ranges):
    quota = factories.QuotaOrderNumberFactory.create(
        category=0,
        valid_between=date_ranges.big_no_end,
    )
    factories.QuotaOrderNumberOriginFactory.create(order_number=quota)
    factories.QuotaOrderNumberOriginFactory.create(order_number=quota)
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    tx = geo_area2.transaction
    (
        origin1,
        origin2,
        origin3,
    ) = quota.quotaordernumberorigin_set.approved_up_to_transaction(tx)

    # sanity check
    assert quota.quotaordernumberorigin_set.count() == 3

    data = {
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": "1",  # update category
        # keep first origin data the same
        "origins-0-pk": origin1.pk,
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": origin1.geographical_area.pk,
        # omit subform for origin2 to delete it
        # change origin3 geo area
        "origins-1-pk": origin3.pk,
        "origins-1-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-1-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-1-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-1-end_date_0": "",
        "origins-1-end_date_1": "",
        "origins-1-end_date_2": "",
        "origins-1-geographical_area": geo_area1.pk,
        # add a new origin
        "origins-2-pk": "",
        "origins-2-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-2-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-2-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-2-end_date_0": "",
        "origins-2-end_date_1": "",
        "origins-2-end_date_2": "",
        "origins-2-geographical_area": geo_area2.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    tx = Transaction.objects.last()
    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        .filter(sid=quota.sid)
        .first()
    )
    assert updated_quota.category == 1
    assert updated_quota.valid_between == date_ranges.big_no_end

    assert updated_quota.origins.approved_up_to_transaction(tx).count() == 3
    assert {o.sid for o in updated_quota.origins.approved_up_to_transaction(tx)} == {
        geo_area1.sid,
        geo_area2.sid,
        origin1.geographical_area.sid,
    }


def test_quota_update_existing_origin_exclusion_new_version(
    client_with_current_workbasket,
    date_ranges,
):
    # make a geo group with a member country
    country1 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )

    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(
        excluded_geographical_area=membership1.member,
    )
    origin = exclusion.origin
    quota = origin.order_number

    # sanity check
    assert quota.quotaordernumberorigin_set.count() == 1

    data = {
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": "1",  # update category
        # leave origin and exclusion data the same
        "origins-0-pk": origin.pk,
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        "origins-0-exclusions-0-pk": exclusion.pk,
        "origins-0-exclusions-0-geographical_area": membership1.member.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    tx = Transaction.objects.last()

    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        .filter(sid=quota.sid)
        .first()
    )

    assert updated_quota.origins.approved_up_to_transaction(tx).count() == 1
    updated_origin = (
        updated_quota.quotaordernumberorigin_set.approved_up_to_transaction(tx).first()
    )
    assert {
        e.excluded_geographical_area.sid
        for e in updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        )
    } == {
        membership1.member.sid,
    }


def test_quota_update_existing_origin_exclusions(
    client_with_current_workbasket,
    date_ranges,
):
    # make a geo group with 3 member countries
    country1 = factories.CountryFactory.create()
    country2 = factories.CountryFactory.create()
    country3 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )
    membership2 = factories.GeographicalMembershipFactory.create(
        member=country2,
        geo_group=geo_group,
    )
    membership3 = factories.GeographicalMembershipFactory.create(
        member=country3,
        geo_group=geo_group,
    )

    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(
        excluded_geographical_area=membership1.member,
    )
    origin = exclusion.origin
    quota = origin.order_number

    # sanity check
    assert quota.quotaordernumberorigin_set.count() == 1

    data = {
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": "1",  # update category
        "origins-0-pk": origin.pk,
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        # update existing
        "origins-0-exclusions-0-pk": exclusion.pk,
        "origins-0-exclusions-0-geographical_area": membership2.member.pk,
        # add new
        "origins-0-exclusions-1-pk": "",
        "origins-0-exclusions-1-geographical_area": membership3.member.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    tx = Transaction.objects.last()

    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        .filter(sid=quota.sid)
        .first()
    )

    assert updated_quota.origins.approved_up_to_transaction(tx).count() == 1
    updated_origin = (
        updated_quota.quotaordernumberorigin_set.approved_up_to_transaction(tx).first()
    )
    assert {
        e.excluded_geographical_area.sid
        for e in updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        )
    } == {
        membership2.member.sid,
        membership3.member.sid,
    }


def test_quota_update_existing_origin_exclusion_remove(
    client_with_current_workbasket,
    date_ranges,
):
    country1 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )

    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(
        excluded_geographical_area=membership1.member,
    )
    origin1 = exclusion.origin
    quota = origin1.order_number
    origin2 = factories.QuotaOrderNumberOriginFactory.create(order_number=quota)

    # sanity check
    tx = Transaction.objects.last()
    assert quota.quotaordernumberorigin_set.approved_up_to_transaction(tx).count() == 2
    assert (
        origin1.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 1
    )
    assert (
        origin2.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 0
    )

    data = {
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": quota.category,
        "origins-0-pk": origin1.pk,
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        # remove the first origin's exclusion
        # remove the second origin
        "submit": "Save",
    }

    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    last_tx = Transaction.objects.last()

    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(last_tx)
        .filter(sid=quota.sid)
        .first()
    )

    assert updated_quota.origins.approved_up_to_transaction(last_tx).count() == 1
    updated_origin = (
        updated_quota.quotaordernumberorigin_set.approved_up_to_transaction(
            last_tx,
        ).first()
    )
    assert (
        updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            last_tx,
        ).count()
        == 0
    )
    # update quota
    # update quota origin 1
    # delete quota origin 1 exclusion
    # delete quota origin 2
    assert updated_origin.transaction.workbasket.tracked_models.count() == 4
    assert sorted(
        [
            item.get_update_type_display()
            for item in updated_origin.transaction.workbasket.tracked_models.all()
        ],
    ) == ["Delete", "Delete", "Update", "Update"]


@pytest.mark.parametrize(
    "data, expected_model",
    [
        (
            {"suspension_type": QuotaSuspensionType.SUSPENSION},
            models.QuotaSuspension,
        ),
        (
            {
                "suspension_type": QuotaSuspensionType.BLOCKING,
                "blocking_period_type": validators.BlockingPeriodType.END_USER_DECISION,
            },
            models.QuotaBlocking,
        ),
    ],
)
def test_quota_suspension_or_blocking_create_view(
    data,
    expected_model,
    client_with_current_workbasket,
):
    """Tests that `QuotaSuspensionOrBlockingCreate` view creates a suspension or
    blocking period after POSTing valid form data."""
    quota_definition = factories.QuotaDefinitionFactory.create()
    quota_order_number = quota_definition.order_number
    data.update(
        {
            "quota_definition": quota_definition.pk,
            "description": "Test description",
            "start_date_0": quota_definition.valid_between.lower.day,
            "start_date_1": quota_definition.valid_between.lower.month,
            "start_date_2": quota_definition.valid_between.lower.year,
        },
    )
    url = reverse(
        "quota_suspension_or_blocking-ui-create",
        kwargs={"sid": quota_order_number.sid},
    )

    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200
    assert not expected_model.objects.exists()

    response = client_with_current_workbasket.post(url, data)
    assert response.status_code == 302
    assert expected_model.objects.count() == 1


def test_quota_suspension_confirm_create_view(valid_user_client):
    """Tests that `QuotaSuspensionConfirmCreate` view returns HTTP 200
    response."""
    suspension = factories.QuotaSuspensionFactory.create()
    url = reverse("quota_suspension-ui-confirm-create", kwargs={"sid": suspension.sid})
    response = valid_user_client.get(url)
    assert response.status_code == 200
    assert f"Suspension period SID {suspension.sid} has been created" in str(
        response.content,
    )


def test_quota_blocking_confirm_create_view(valid_user_client):
    """Tests that `QuotaBlockingConfirmCreate` view returns HTTP 200
    response."""
    blocking = factories.QuotaBlockingFactory.create()
    url = reverse("quota_blocking-ui-confirm-create", kwargs={"sid": blocking.sid})
    response = valid_user_client.get(url)
    assert response.status_code == 200
    assert f"Blocking period SID {blocking.sid} has been created" in str(
        response.content,
    )


def test_quota_definition_view(client_with_current_workbasket):
    """Test all 4 of the quota definition tabs load and display the correct
    objects."""
    main_quota_definition = factories.QuotaDefinitionFactory.create(sid=123)
    sub_quota_definition = factories.QuotaDefinitionFactory.create(sid=234)
    main_quota = main_quota_definition.order_number
    association = factories.QuotaAssociationFactory.create(
        main_quota=main_quota_definition,
        sub_quota=sub_quota_definition,
    )
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition=main_quota_definition,
        description="Blocking period description",
    )
    suspension = factories.QuotaSuspensionFactory.create(
        quota_definition=main_quota_definition,
        description="Suspension period description",
    )

    # Definition period tab
    response = client_with_current_workbasket.get(
        reverse("quota_definition-ui-list", kwargs={"sid": main_quota.sid}),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    sid_cell_text = soup.select(
        "tbody tr:first-child td:first-child details summary span",
    )[0].text.strip()
    assert int(sid_cell_text) == main_quota_definition.sid

    # Sub-quotas tab
    response = client_with_current_workbasket.get(
        reverse(
            "quota_definition-ui-list-filter",
            kwargs={"sid": main_quota.sid, "quota_type": "quota_associations"},
        ),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    sid_cell_text = soup.select("tbody tr:first-child td:first-child a")[0].text.strip()
    assert int(sid_cell_text) == sub_quota_definition.sid

    # Blocking periods tab
    response = client_with_current_workbasket.get(
        reverse(
            "quota_definition-ui-list-filter",
            kwargs={"sid": main_quota.sid, "quota_type": "blocking_periods"},
        ),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    description_cell_text = soup.select("tbody tr:first-child td")[-2].text
    assert description_cell_text == blocking.description

    # Suspension period tab
    response = client_with_current_workbasket.get(
        reverse(
            "quota_definition-ui-list-filter",
            kwargs={"sid": main_quota.sid, "quota_type": "suspension_periods"},
        ),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    description_cell_text = soup.select("tbody tr:first-child td")[-2].text
    assert description_cell_text == suspension.description


def test_definition_duplicator_form_wizard_start(client_with_current_workbasket):
    url = reverse("sub_quota_definitions-ui-create", kwargs={"step": "start"})
    response = client_with_current_workbasket.get(url)
    assert response.status_code == 200


@pytest.fixture
def main_quota_order_number() -> models.QuotaOrderNumber:
    """Provides a main quota order number for use across the fixtures and
    following tests."""
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def sub_quota_order_number() -> models.QuotaOrderNumber:
    """Provides a sub-quota order number for use across the fixtures and
    following tests."""
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def quota_definition_1(main_quota_order_number, date_ranges) -> models.QuotaDefinition:
    """Provides a definition, linked to the main_quota_order_number to be used
    across the following tests."""
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.normal,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )


@pytest.fixture
def quota_definition_2(main_quota_order_number, date_ranges) -> models.QuotaDefinition:
    """Provides a definition, linked to the main_quota_order_number to be used
    across the following tests."""
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.normal,
    )


@pytest.fixture
def quota_definition_3(main_quota_order_number, date_ranges) -> models.QuotaDefinition:
    """Provides a definition, linked to the main_quota_order_number to be used
    across the following tests."""
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.normal,
    )


@pytest.fixture
def wizard(requests_mock, session_request):
    """Provides an instance of the form wizard for use across the following
    tests."""
    storage = QuotaDefinitionDuplicatorSessionStorage(
        request=session_request,
        prefix="",
    )
    return DuplicateDefinitionsWizard(
        request=requests_mock,
        storage=storage,
    )


def test_duplicate_definition_wizard_get_cleaned_data_for_step(
    session_request,
    main_quota_order_number,
    sub_quota_order_number,
):

    order_number_data = {
        "duplicate_definitions_wizard-current_step": "quota_order_numbers",
        "quota_order_numbers-main_quota_order_number": [main_quota_order_number.pk],
        "quota_order_numbers-sub_quota_order_number": [sub_quota_order_number.pk],
    }
    storage = QuotaDefinitionDuplicatorSessionStorage(
        request=session_request,
        prefix="",
    )

    storage.set_step_data("quota_order_numbers", order_number_data)
    storage._set_current_step("quota_order_numbers")
    wizard = DuplicateDefinitionsWizard(
        request=session_request,
        storage=storage,
        initial_dict={"quota_order_numbers": {}},
        instance_dict={"quota_order_numbers": None},
    )
    wizard.form_list = OrderedDict(wizard.form_list)
    cleaned_data = wizard.get_cleaned_data_for_step("quota_order_numbers")

    assert cleaned_data["main_quota_order_number"] == main_quota_order_number
    assert cleaned_data["sub_quota_order_number"] == sub_quota_order_number


@pytest.mark.parametrize(
    "step",
    ["quota_order_numbers", "select_definition_periods", "selected_definition_periods"],
)
def test_duplicate_definition_wizard_get_form_kwargs(
    quota_definition_1,
    quota_definition_2,
    quota_definition_3,
    session_request,
    main_quota_order_number,
    sub_quota_order_number,
    step,
):

    quota_order_numbers_data = {
        "duplicate_definitions_wizard-current_step": "quota_order_numbers",
        "quota_order_numbers-main_quota_order_number": [main_quota_order_number.pk],
        "quota_order_numbers-sub_quota_order_number": [sub_quota_order_number.pk],
    }
    select_definitions_data = {
        "duplicate_definitions_wizard-current_step": "select_definition_periods",
        f"select_definition_periods-selectableobject_{quota_definition_1.pk}": ["on"],
        f"select_definition_periods-selectableobject_{quota_definition_2.pk}": ["on"],
        f"select_definition_periods-selectableobject_{quota_definition_3.pk}": [],
    }

    storage = QuotaDefinitionDuplicatorSessionStorage(
        request=session_request,
        prefix="",
    )

    storage.set_step_data("quota_order_numbers", quota_order_numbers_data)
    storage.set_step_data("select_definition_periods", select_definitions_data)
    storage._set_current_step(step)

    wizard = DuplicateDefinitionsWizard(
        request=session_request,
        storage=storage,
        initial_dict={"selected_definitions": {}},
        instance_dict={"selected_definitions": None},
    )
    wizard.form_list = OrderedDict(wizard.form_list)

    with override_current_transaction(Transaction.objects.last()):
        kwargs = wizard.get_form_kwargs(step)
        if step == "select_definition_periods":
            definitions = models.QuotaDefinition.objects.filter(
                sid__in=[
                    quota_definition_1.sid,
                    quota_definition_2.sid,
                    quota_definition_3.sid,
                ],
            )
            assert set(kwargs["objects"]) == set(definitions)
        if step == "selected_definition_periods":
            assert kwargs["request"].session


def test_definition_duplicator_creates_definition_and_association(
    quota_definition_1,
    main_quota_order_number,
    sub_quota_order_number,
    session_request_with_workbasket,
):
    """Pass data to the Duplicator Wizard and verify that the created definition
    contains the expected data."""

    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": {
                "initial_volume": str(quota_definition_1.initial_volume),
                "volume": str(quota_definition_1.volume),
                "measurement_unit_code": quota_definition_1.measurement_unit.code,
                "start_date": serialize_date(quota_definition_1.valid_between.lower),
                "end_date": serialize_date(quota_definition_1.valid_between.upper),
                "status": True,
                "coefficient": 1,
                "relationship_type": "NM",
            },
        },
    ]
    session_request_with_workbasket.session["staged_definition_data"] = (
        staged_definition_data
    )
    order_number_data = {
        "duplicate_definitions_wizard-current_step": "quota_order_numbers",
        "quota_order_numbers-main_quota_order_number": [main_quota_order_number.pk],
        "quota_order_numbers-sub_quota_order_number": [sub_quota_order_number.pk],
    }
    storage = QuotaDefinitionDuplicatorSessionStorage(
        request=session_request_with_workbasket,
        prefix="",
    )

    storage.set_step_data("quota_order_numbers", order_number_data)
    storage._set_current_step("quota_order_numbers")
    wizard = DuplicateDefinitionsWizard(
        request=session_request_with_workbasket,
        storage=storage,
        initial_dict={"quota_order_numbers": {}},
        instance_dict={"quota_order_numbers": None},
    )
    wizard.form_list = OrderedDict(wizard.form_list)

    association_table_before = models.QuotaAssociation.objects.all()
    # assert 0
    assert len(association_table_before) == 0
    for definition in session_request_with_workbasket.session["staged_definition_data"]:
        wizard.create_definition(definition)

    definition_objects = models.QuotaDefinition.objects.all()

    # assert that the values of the definitions match
    assert definition_objects[0].volume == definition_objects[1].volume
    assert (
        definition_objects[0].measurement_unit == definition_objects[1].measurement_unit
    )
    assert definition_objects[0].valid_between == definition_objects[1].valid_between

    assert len(definition_objects) == 2
    # assert that the association is created
    association_table_after = models.QuotaAssociation.objects.all()
    assert association_table_after[0].main_quota == quota_definition_1
    assert association_table_after[0].sub_quota in definition_objects


def test_status_tag_generator(quota_definition_1, quota_definition_2, wizard):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": {
                "initial_volume": str(quota_definition_1.initial_volume),
                "volume": str(quota_definition_1.volume),
                "measurement_unit_code": quota_definition_1.measurement_unit.code,
                "start_date": serialize_date(quota_definition_1.valid_between.lower),
                "end_date": serialize_date(quota_definition_1.valid_between.upper),
                "status": False,
                "coefficient": 1,
                "relationship_type": "NM",
            },
        },
        {
            "main_definition": quota_definition_2.pk,
            "sub_definition_staged_data": {
                "initial_volume": str(quota_definition_2.initial_volume),
                "volume": str(quota_definition_2.volume),
                "measurement_unit_code": quota_definition_2.measurement_unit.code,
                "start_date": serialize_date(quota_definition_2.valid_between.lower),
                "end_date": serialize_date(quota_definition_2.valid_between.upper),
                "status": True,
                "coefficient": 1,
                "relationship_type": "NM",
            },
        },
    ]
    for definition in staged_definition_data:
        status = wizard.status_tag_generator(definition["sub_definition_staged_data"])
        if definition["main_definition"] == quota_definition_1.pk:
            assert status["text"] == "Unedited"
        elif definition["main_definition"] == quota_definition_2.pk:
            assert status["text"] == "Edited"


def test_format_date(wizard):
    date_str = "2021-01-01"
    formatted_date = wizard.format_date(date_str)
    assert formatted_date == "01 Jan 2021"


@pytest.fixture
def sub_quota_association(date_ranges):
    sub_quota = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.future,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )
    main_quota = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.future,
        volume=9999,
        initial_volume=9999,
        measurement_unit=sub_quota.measurement_unit,
    )
    association = factories.QuotaAssociationFactory.create(
        sub_quota=sub_quota,
        main_quota=main_quota,
        sub_quota_relation_type="EQ",
        coefficient=1.5,
    )
    return association


def test_sub_quota_update(sub_quota_association, client_with_current_workbasket):
    """Test that SubQuotaDefinitionAssociationUpdate returns 200 and creates an
    update object for sub-quota definition and association."""
    sub_quota = sub_quota_association.sub_quota
    response = client_with_current_workbasket.get(
        reverse("sub_quota_definition-edit", kwargs={"sid": sub_quota.sid}),
    )
    assert response.status_code == 200

    form_data = {
        "coefficient": 1.2,
        "start_date_0": sub_quota.valid_between.lower.day,
        "start_date_1": sub_quota.valid_between.lower.month,
        "start_date_2": sub_quota.valid_between.lower.year,
        "measurement_unit": sub_quota.measurement_unit.pk,
        "relationship_type": "EQ",
        "end_date_0": sub_quota.valid_between.lower.day,
        "end_date_1": sub_quota.valid_between.lower.month,
        "end_date_2": sub_quota.valid_between.lower.year,
        "volume": 100,
        "initial_volume": 100,
    }
    response = client_with_current_workbasket.post(
        reverse("sub_quota_definition-edit", kwargs={"sid": sub_quota.sid}),
        form_data,
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "sub_quota_definition-confirm-update",
        kwargs={"sid": sub_quota.sid},
    )
    tx = Transaction.objects.last()
    sub_quota_association = models.QuotaAssociation.objects.approved_up_to_transaction(
        tx,
    ).get(sub_quota__sid=sub_quota.sid)
    assert str(sub_quota_association.coefficient) == "1.20000"
    assert sub_quota_association.sub_quota.volume == 100
    assert sub_quota_association.update_type == UpdateType.UPDATE
    assert sub_quota_association.sub_quota.update_type == UpdateType.UPDATE


def test_sub_quota_edit_update(sub_quota_association, client_with_current_workbasket):
    """Test that SubQuotaDefinitionAssociationEditUpdate returns 200 and
    overwrites the update objects for the sub-quota definition and
    association."""
    # Call the previous test first to create the objects and some update instances of them
    test_sub_quota_update(sub_quota_association, client_with_current_workbasket)
    sub_quota = sub_quota_association.sub_quota
    response = client_with_current_workbasket.get(
        reverse("sub_quota_definition-edit-update", kwargs={"sid": sub_quota.sid}),
    )
    assert response.status_code == 200

    form_data = {
        "coefficient": 1,
        "start_date_0": sub_quota.valid_between.lower.day,
        "start_date_1": sub_quota.valid_between.lower.month,
        "start_date_2": sub_quota.valid_between.lower.year,
        "measurement_unit": sub_quota.measurement_unit.pk,
        "relationship_type": "NM",
        "end_date_0": sub_quota.valid_between.lower.day,
        "end_date_1": sub_quota.valid_between.lower.month,
        "end_date_2": sub_quota.valid_between.lower.year,
        "volume": 200,
        "initial_volume": 200,
    }
    response = client_with_current_workbasket.post(
        reverse("sub_quota_definition-edit-update", kwargs={"sid": sub_quota.sid}),
        form_data,
    )
    assert response.status_code == 302
    # Assert that the update instances have been edited rather than creating another 2 update instances
    tx = Transaction.objects.last()
    sub_quota_association = models.QuotaAssociation.objects.approved_up_to_transaction(
        tx,
    ).get(sub_quota__sid=sub_quota.sid)
    assert str(sub_quota_association.coefficient) == "1.00000"
    assert sub_quota_association.sub_quota.volume == 200
    sub_quota_definitions = models.QuotaDefinition.objects.all().filter(
        sid=sub_quota.sid,
    )
    sub_quota_associations = models.QuotaAssociation.objects.all().filter(
        sub_quota__sid=sub_quota.sid,
    )
    assert len(sub_quota_definitions) == 2
    assert len(sub_quota_associations) == 2
    assert sub_quota_definitions[1].update_type == UpdateType.UPDATE
    assert sub_quota_associations[1].update_type == UpdateType.UPDATE


def test_sub_quota_confirm_update_page(
    client_with_current_workbasket,
    sub_quota_association,
):
    sub_quota = sub_quota_association.sub_quota
    response = client_with_current_workbasket.get(
        reverse(
            "sub_quota_definition-confirm-update",
            kwargs={"sid": sub_quota.sid},
        ),
    )
    workbasket = response.context_data["view"].workbasket
    assert (
        f"Sub-quota definition: {sub_quota.sid} and association have been updated in workbasket {workbasket.pk}"
        in str(response.content)
    )


def test_delete_quota_association(client_with_current_workbasket):
    main_quota = factories.QuotaDefinitionFactory.create()
    sub_quota = factories.QuotaDefinitionFactory.create()
    quota_association = factories.QuotaAssociationFactory.create(
        main_quota=main_quota,
        sub_quota=sub_quota,
    )

    url = reverse(
        "quota_association-ui-delete",
        kwargs={"pk": quota_association.pk},
    )

    response = client_with_current_workbasket.post(url, {"submit": "Delete"})
    assert response.status_code == 302
    assert response.url == reverse(
        "quota_association-ui-confirm-delete",
        kwargs={"sid": sub_quota.sid},
    )

    tx = Transaction.objects.last()

    assert tx.workbasket.tracked_models.first().update_type == UpdateType.DELETE
    confirm_response = client_with_current_workbasket.get(response.url)

    soup = BeautifulSoup(
        confirm_response.content.decode(response.charset),
        "html.parser",
    )
    h1 = soup.select("h1")[0]

    assert (
        h1.text.strip()
        == f"Quota association between {main_quota.sid} and {sub_quota.sid} has been deleted"
    )


def test_quota_suspension_edit(client_with_current_workbasket):
    """Test the QuotaSuspensionUpdate view including the
    QuotaSuspensionUpdateMixin."""
    suspension = factories.QuotaSuspensionFactory.create()
    current_validity = suspension.valid_between
    data = {
        "start_date_0": current_validity.lower.day,
        "start_date_1": current_validity.lower.month,
        "start_date_2": current_validity.lower.year,
        "end_date_0": current_validity.upper.day,
        "end_date_1": current_validity.upper.month,
        "end_date_2": current_validity.upper.year,
        "description": "New description",
    }

    url = reverse("quota_suspension-ui-edit", kwargs={"sid": suspension.sid})

    response = client_with_current_workbasket.post(url, data=data)
    assert response.status_code == 302
    assert response.url == reverse(
        "quota_suspension-ui-confirm-update",
        kwargs={"sid": suspension.sid},
    )

    updated_suspension = models.QuotaSuspension.objects.approved_up_to_transaction(
        Transaction.objects.last(),
    ).get(sid=suspension.sid)
    assert updated_suspension.description == "New description"
    assert updated_suspension.update_type == UpdateType.UPDATE

    confirm_response = client_with_current_workbasket.get(response.url)

    soup = BeautifulSoup(
        confirm_response.content.decode(response.charset),
        "html.parser",
    )
    div = soup.select("div .govuk-panel__body")[0]

    assert f"Quota suspension: {suspension.sid} has been updated" in div.text.strip()


def test_quota_suspension_edit_update(client_with_current_workbasket):
    """Test that posting the edit update form edits the existing quota
    suspension update object rather than creating a new one."""
    suspension = factories.QuotaSuspensionFactory.create()
    data = {
        "start_date_0": suspension.valid_between.lower.day,
        "start_date_1": suspension.valid_between.lower.month,
        "start_date_2": suspension.valid_between.lower.year,
        "end_date_0": suspension.valid_between.upper.day,
        "end_date_1": suspension.valid_between.upper.month,
        "end_date_2": suspension.valid_between.upper.year,
        "description": "New description",
    }

    edit_url = reverse("quota_suspension-ui-edit", kwargs={"sid": suspension.sid})
    client_with_current_workbasket.post(edit_url, data=data)
    edit_update_url = reverse(
        "quota_suspension-ui-edit-update",
        kwargs={"sid": suspension.sid},
    )
    response = client_with_current_workbasket.post(edit_update_url, data=data)
    assert response.status_code == 302
    versions = models.QuotaSuspension.objects.all().filter(sid=suspension.sid)
    assert len(versions) == 2
    assert versions.first().update_type == UpdateType.CREATE
    assert versions.last().update_type == UpdateType.UPDATE


@pytest.mark.parametrize(
    "factory",
    (factories.QuotaSuspensionFactory,),
)
def test_quota_suspension_delete_form(factory, use_delete_form):
    use_delete_form(factory())
