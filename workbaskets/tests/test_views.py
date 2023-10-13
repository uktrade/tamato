import os
import re
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.timezone import localtime

from checks.models import TrackedModelCheck
from checks.tests.factories import TrackedModelCheckFactory
from common.models.utils import override_current_transaction
from common.tests import factories
from common.validators import UpdateType
from exporter.tasks import upload_workbaskets
from importer.models import ImportBatch
from importer.models import ImportBatchStatus
from measures.models import Measure
from workbaskets import models
from workbaskets.forms import SelectableObjectsForm
from workbaskets.tasks import check_workbasket_sync
from workbaskets.validators import WorkflowStatus
from workbaskets.views import ui

pytestmark = pytest.mark.django_db


def test_workbasket_create_form_creates_workbasket_object(
    valid_user_api_client,
):
    # Post a form
    create_url = reverse("workbaskets:workbasket-ui-create")

    form_data = {
        "title": "1234567890",
        "reason": "Making a new workbasket",
    }

    response = valid_user_api_client.post(create_url, form_data)
    #  get the workbasket we have made, and make sure it matches title and description
    workbasket = models.WorkBasket.objects.filter(
        title=form_data["title"],
    )[0]

    assert str(workbasket.id) in response.url
    assert workbasket.title == form_data["title"]
    assert workbasket.reason == form_data["reason"]


def test_workbasket_create_user_not_logged_in_dev_sso_disabled(client, settings):
    """Tests that, when a user who hasn't logged in tries to create a workbasket
    in the dev env with SSO disabled, they are redirected to the login page."""
    settings.ENV = "dev"
    settings.SSO_ENABLED = False
    settings.LOGIN_URL = reverse("login")
    if "authbroker_client.middleware.ProtectAllViewsMiddleware" in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove(
            "authbroker_client.middleware.ProtectAllViewsMiddleware",
        )
    create_url = reverse("workbaskets:workbasket-ui-create")
    form_data = {
        "title": "1234567890",
        "reason": "Making a new workbasket",
    }
    response = client.post(create_url, form_data)

    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={create_url}"


def test_workbasket_create_without_permission(client):
    """Tests that WorkBasketCreate returns 403 to user without add_workbasket
    permission."""
    create_url = reverse("workbaskets:workbasket-ui-create")
    form_data = {
        "title": "1234567890",
        "reason": "Making a new workbasket",
    }
    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.post(create_url, form_data)

    assert response.status_code == 403


def test_workbasket_update_view_updates_workbasket_title_and_description(
    valid_user_client,
    session_workbasket,
):
    """Test that a workbasket's title and description can be updated."""

    session = valid_user_client.session
    session["workbasket"] = {"id": session_workbasket.pk}
    session.save()

    url = reverse(
        "workbaskets:workbasket-ui-update",
        kwargs={"pk": session_workbasket.pk},
    )
    new_title = "123321"
    new_description = "Newly updated test description"
    form_data = {
        "title": new_title,
        "reason": new_description,
    }
    assert not session_workbasket.title == new_title
    assert not session_workbasket.reason == new_description

    response = valid_user_client.get(url)
    assert response.status_code == 200

    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302
    assert response.url == reverse(
        "workbaskets:workbasket-ui-confirm-update",
        kwargs={"pk": session_workbasket.pk},
    )

    session_workbasket.refresh_from_db()
    assert session_workbasket.title == new_title
    assert session_workbasket.reason == new_description


def test_download(
    queued_workbasket,
    client,
    valid_user,
    hmrc_storage,
    s3_resource,
    s3_object_names,
    settings,
):
    client.force_login(valid_user)
    bucket = "hmrc"
    settings.HMRC_STORAGE_BUCKET_NAME = bucket
    s3_resource.create_bucket(Bucket="hmrc")
    with patch(
        "exporter.storages.HMRCStorage.save",
        wraps=MagicMock(side_effect=hmrc_storage.save),
    ):
        upload_workbaskets.apply()
        url = reverse("workbaskets:workbasket-download")

        response = client.get(url)

        # the url signature will always be unique, so we can only compare the first part of the url
        expected_url, _ = s3_resource.meta.client.generate_presigned_url(
            ClientMethod="get_object",
            ExpiresIn=3600,
            Params={
                "Bucket": settings.HMRC_STORAGE_BUCKET_NAME,
                "Key": s3_object_names("hmrc")[0],
            },
        ).split("?", 1)

        assert response.status_code == 302
        assert expected_url in response.url


def test_review_workbasket_displays_objects_in_current_workbasket(
    valid_user_client,
    session_workbasket,
):
    """Verify that changes in the current workbasket are displayed on the bulk
    selection form of the review workbasket page."""

    with session_workbasket.new_transaction():
        factories.GoodsNomenclatureFactory.create()

    response = valid_user_client.get(
        reverse(
            "workbaskets:current-workbasket",
        ),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    for obj in session_workbasket.tracked_models.all():
        field_name = SelectableObjectsForm.field_name_for_object(obj)
        assert page.find("input", {"name": field_name})


def test_review_workbasket_displays_rule_violation_summary(
    valid_user_client,
    session_workbasket,
):
    """Test that the review workbasket page includes an error summary box
    detailing the number of tracked model changes and business rule violations,
    dated to the most recent `TrackedModelCheck`."""
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        check = TrackedModelCheckFactory.create(
            transaction_check__transaction=transaction,
            model=good,
            successful=False,
        )

    response = valid_user_client.get(
        reverse(
            "workbaskets:current-workbasket",
        ),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )

    error_headings = page.find_all("h2", attrs={"class": "govuk-body"})
    tracked_model_count = session_workbasket.tracked_models.count()
    local_created_at = localtime(check.created_at)
    created_at = f"{local_created_at:%d %b %Y %H:%M}"

    assert f"Last Run: ({created_at})" in error_headings[0].text
    assert f"Number of changes: {tracked_model_count}" in error_headings[0].text
    assert f"Number of violations: 1" in error_headings[1].text


def test_edit_workbasket_page_sets_workbasket(valid_user_client, session_workbasket):
    response = valid_user_client.get(
        reverse("workbaskets:edit-workbasket"),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert str(session_workbasket.pk) in soup.select(".govuk-heading-xl")[0].text


def test_workbasket_detail_page_url_params(
    valid_user_client,
    session_workbasket,
):
    url = reverse(
        "workbaskets:current-workbasket",
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    buttons = soup.select(".govuk-button.govuk-button--primary")
    for button in buttons:
        # test that accidental spacing in template hasn't mangled the url
        assert " " not in button.get("href")
        assert "%20" not in button.get("href")


def test_select_workbasket_page_200(valid_user_client):
    """
    Checks the page returns 200.

    Then checks that only workbaskets with certain statuses are displayed i.e.
    we don't want users to be able to edit workbaskets that are archived, sent,
    or published.
    """
    factories.WorkBasketFactory.create(status=WorkflowStatus.ARCHIVED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.PUBLISHED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    factories.WorkBasketFactory.create(status=WorkflowStatus.QUEUED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.ERRORED)
    valid_statuses = {
        WorkflowStatus.EDITING,
        WorkflowStatus.ERRORED,
    }
    response = valid_user_client.get(reverse("workbaskets:workbasket-ui-list"))
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    statuses = [
        element.text for element in soup.select(".govuk-table__row .status-badge")
    ]
    assert len(statuses) == 2
    assert not set(statuses).difference(valid_statuses)


def test_select_workbasket_with_errored_status(valid_user_client):
    """Test that the workbasket is transitioned correctly to editing if it is
    selected for editing while in ERRORED status."""
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.ERRORED,
    )
    response = valid_user_client.post(
        reverse("workbaskets:workbasket-ui-list"),
        {"workbasket": workbasket.id},
    )
    assert response.status_code == 302
    workbasket.refresh_from_db()
    assert workbasket.status == WorkflowStatus.EDITING


@pytest.mark.parametrize(
    "workbasket_tab, expected_url, url_kwargs_required",
    [
        ("view-summary", "workbaskets:current-workbasket", False),
        ("add-edit-items", "workbaskets:edit-workbasket", False),
        ("view-violations", "workbaskets:workbasket-ui-violations", False),
        ("review-measures", "workbaskets:workbasket-ui-review-measures", True),
        ("review-goods", "workbaskets:workbasket-ui-review-goods", True),
        ("", "workbaskets:current-workbasket", False),
    ],
)
def test_select_workbasket_redirects_to_tab(
    valid_user_client,
    workbasket_tab,
    expected_url,
    url_kwargs_required,
):
    """Test that SelectWorkbasketView redirects to a specific tab on the
    selected workbasket if a tab has been provided."""
    workbasket = factories.WorkBasketFactory.create()
    response = valid_user_client.post(
        reverse("workbaskets:workbasket-ui-list"),
        {
            "workbasket": workbasket.id,
            "workbasket-tab": workbasket_tab,
        },
    )
    assert response.status_code == 302
    if url_kwargs_required:
        assert response.url == reverse(expected_url, kwargs={"pk": workbasket.pk})
    else:
        assert response.url == reverse(expected_url)


@pytest.mark.parametrize(
    "form_action, url_name",
    [
        ("page-prev", "workbaskets:current-workbasket"),
        ("page-next", "workbaskets:current-workbasket"),
    ],
)
def test_review_workbasket_redirects(
    form_action,
    url_name,
    valid_user_client,
):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with workbasket.new_transaction() as tx:
        factories.FootnoteTypeFactory.create_batch(150, transaction=tx)
    url = reverse("workbaskets:current-workbasket")
    data = {"form-action": form_action}
    response = valid_user_client.post(f"{url}?page=2", data)
    assert response.status_code == 302
    assert reverse(url_name) in response.url

    if form_action == "page-prev":
        assert "?page=1" in response.url

    elif form_action == "page-next":
        assert "?page=3" in response.url


@pytest.mark.parametrize(
    "url_name,",
    (
        "workbaskets:workbasket-ui-list",
        "workbaskets:workbasket-ui-list-all",
        "workbaskets:edit-workbasket",
    ),
)
def test_workbasket_views_without_permission(url_name, client, session_workbasket):
    """Tests that select, list-all, delete, and edit workbasket view endpoints
    return 403 to users without change_workbasket permission."""
    url = reverse(
        url_name,
    )
    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.get(url)

    assert response.status_code == 403


def test_workbasket_list_view_get_queryset():
    """Test that WorkBasketList.get_queryset() returns a queryset with the
    expected number of baskets ordered by updated_at."""
    wb_1 = factories.WorkBasketFactory.create()
    wb_2 = factories.WorkBasketFactory.create()
    wb_1.title = "most recently updated"
    wb_1.save()
    view = ui.WorkBasketList()
    qs = view.get_queryset()

    assert qs.count() == 2
    assert qs.first() == wb_1
    assert qs.last() == wb_2


def test_workbasket_list_all_view(valid_user_client):
    """Test that valid user receives a 200 on GET for WorkBasketList view and wb
    values display in html table."""
    wb = factories.WorkBasketFactory.create()
    url = reverse("workbaskets:workbasket-ui-list-all")
    response = valid_user_client.get(url)

    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")
    table = soup.select("table")[0]
    row_text = [row.text for row in table.findChildren("td")]

    assert wb.title in row_text
    assert str(wb.id) in row_text
    assert wb.get_status_display() in row_text
    assert wb.updated_at.strftime("%d %b %y") in row_text
    assert wb.created_at.strftime("%d %b %y") in row_text
    assert str(wb.tracked_models.count()) in row_text
    assert wb.reason in row_text


@pytest.mark.parametrize(
    ("status", "search_term"),
    [
        (WorkflowStatus.ARCHIVED, "ARCHIVED"),
        (WorkflowStatus.EDITING, "EDITING"),
        (WorkflowStatus.QUEUED, "QUEUED"),
        (WorkflowStatus.PUBLISHED, "PUBLISHED"),
        (WorkflowStatus.ERRORED, "ERRORED"),
    ],
)
def test_workbasket_list_all_view_search_filters(
    valid_user_client,
    status,
    search_term,
):
    wb = factories.WorkBasketFactory.create(status=status)

    list_url = reverse("workbaskets:workbasket-ui-list-all")
    url = f"{list_url}?search=&status={search_term}"

    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")

    rows = soup.select("table > tbody > tr")
    row_text = [td.text for td in rows[0]]
    assert len(rows) == 1
    assert wb.get_status_display() in row_text


@pytest.mark.parametrize(
    "url",
    (
        "workbaskets:workbasket-ui-review-additional-codes",
        "workbaskets:workbasket-ui-review-certificates",
        "workbaskets:workbasket-ui-review-goods",
        "workbaskets:workbasket-ui-review-footnotes",
        "workbaskets:workbasket-ui-review-geo-areas",
        "workbaskets:workbasket-ui-review-measures",
        "workbaskets:workbasket-ui-review-quotas",
        "workbaskets:workbasket-ui-review-regulations",
    ),
)
def test_workbasket_review_tabs_without_permission(url, client):
    """Tests that workbasket review tabs return 403 to users without
    view_workbasket permission."""
    workbasket = factories.WorkBasketFactory.create()
    user = factories.UserFactory.create()
    client.force_login(user)
    url = reverse(url, kwargs={"pk": workbasket.pk})
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("url", "object_factory", "num_columns"),
    [
        (
            "workbaskets:workbasket-ui-review-additional-codes",
            lambda: factories.AdditionalCodeFactory(),
            6,
        ),
        (
            "workbaskets:workbasket-ui-review-certificates",
            lambda: factories.CertificateFactory.create(),
            6,
        ),
        (
            "workbaskets:workbasket-ui-review-footnotes",
            lambda: factories.FootnoteFactory.create(),
            6,
        ),
        (
            "workbaskets:workbasket-ui-review-geo-areas",
            lambda: factories.GeographicalAreaFactory.create(),
            6,
        ),
        (
            "workbaskets:workbasket-ui-review-measures",
            lambda: factories.MeasureFactory.create(),
            11,
        ),
        (
            "workbaskets:workbasket-ui-review-quotas",
            lambda: factories.QuotaOrderNumberFactory.create(),
            6,
        ),
        (
            "workbaskets:workbasket-ui-review-regulations",
            lambda: factories.RegulationFactory.create(),
            6,
        ),
    ],
)
def test_workbasket_review_tabs(
    url,
    object_factory,
    num_columns,
    valid_user_client,
    session_workbasket,
):
    """Tests that workbasket review tabs return 200 and display objects in
    table."""
    with session_workbasket.new_transaction():
        object_factory()
    url = reverse(url, kwargs={"pk": session_workbasket.pk})
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    columns = page.select(".govuk-table__header")
    rows = page.select("tbody > tr")
    assert len(columns) == num_columns
    assert len(rows) == 1


def test_workbasket_review_measures(valid_user_client):
    """Tests that `WorkBasketReviewMeasuresView` returns 200 and displays
    measures in table."""
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    non_workbasket_measures = factories.MeasureFactory.create_batch(5)

    with workbasket.new_transaction() as tx:
        factories.MeasureFactory.create_batch(30, transaction=tx)

    url = reverse(
        "workbaskets:workbasket-ui-review-measures",
        kwargs={"pk": workbasket.pk},
    )
    response = valid_user_client.get(url)

    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")

    non_workbasket_measures_sids = {str(m.sid) for m in non_workbasket_measures}
    measure_sids = [e.text for e in soup.select("table tr td:first-child")]
    workbasket_measures = Measure.objects.filter(
        trackedmodel_ptr__transaction__workbasket_id=workbasket.id,
    ).order_by("sid")
    table_measure_sids = [str(m.sid) for m in workbasket_measures]
    assert table_measure_sids == measure_sids
    assert set(measure_sids).difference(non_workbasket_measures_sids)

    # 3rd column is commodity
    table_commodity_links = {e.a for e in soup.select("table tr td:nth-child(3)")}
    for link in table_commodity_links:
        assert link["class"][0] == "govuk-link" and "/commodities/" in link["href"]

    # 5th column is start date
    table_start_dates = {e.text for e in soup.select("table tr td:nth-child(5)")}
    measure_start_dates = {
        f"{m.valid_between.lower:%d %b %Y}" for m in workbasket_measures
    }
    assert not measure_start_dates.difference(table_start_dates)

    # 6th column is end date
    table_end_dates = {e.text for e in soup.select("table tr td:nth-child(6)")}
    measure_end_dates = {
        f"{m.effective_end_date:%d %b %Y}"
        for m in workbasket_measures
        if m.effective_end_date
    }
    assert not measure_end_dates.difference(table_end_dates)


@pytest.mark.parametrize(
    ("update_type", "expected_measure_count"),
    [
        ("", 4),
        (UpdateType.CREATE, 2),
        (UpdateType.UPDATE, 1),
        (UpdateType.DELETE, 1),
    ],
)
def test_workbasket_review_measures_filters_update_type(
    update_type,
    expected_measure_count,
    valid_user_client,
    session_workbasket,
):
    """Tests that `WorkBasketReviewMeasuresView` filters measures by
    `update_type`."""
    with session_workbasket.new_transaction():
        created_measures = factories.MeasureFactory.create_batch(2)
    updated_measure = created_measures[0].new_version(workbasket=session_workbasket)
    deleted_measure = created_measures[1].new_version(
        update_type=UpdateType.DELETE,
        workbasket=session_workbasket,
    )

    url = reverse(
        "workbaskets:workbasket-ui-review-measures",
        kwargs={"pk": session_workbasket.pk},
    )
    search_filter = f"?update_type={update_type}"
    response = valid_user_client.get(url + search_filter)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    rows = page.select("tbody > tr")
    assert len(rows) == expected_measure_count


def test_workbasket_review_measures_pagination(
    valid_user_client,
    unapproved_transaction,
):
    """Tests that `WorkBasketReviewMeasuresView` paginates when there are more
    than 30 measures in the workbasket."""

    with override_current_transaction(unapproved_transaction):
        workbasket = factories.WorkBasketFactory.create(
            status=WorkflowStatus.EDITING,
        )
        factories.MeasureFactory.create_batch(40, transaction=unapproved_transaction)

    url = reverse(
        "workbaskets:workbasket-ui-review-measures",
        kwargs={"pk": workbasket.pk},
    )
    response = valid_user_client.get(url)

    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")

    measure_sids = {e.text for e in soup.select("table tr td:first-child")}
    workbasket_measures = Measure.objects.filter(
        trackedmodel_ptr__transaction__workbasket_id=workbasket.id,
    )
    assert measure_sids.issubset({str(m.sid) for m in workbasket_measures})


def test_workbasket_review_measures_conditions(valid_user_client):
    """Tests that `WorkBasketReviewMeasuresView` displays the conditions on a
    measure."""
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    factories.MeasureFactory.create_batch(5)
    certificate = factories.CertificateFactory.create()
    tx = workbasket.new_transaction()
    measure = factories.MeasureFactory.create(transaction=tx)
    condition = factories.MeasureConditionFactory.create(
        dependent_measure=measure,
        condition_code__code="B",
        required_certificate=certificate,
        action__code="27",
    )
    url = reverse(
        "workbaskets:workbasket-ui-review-measures",
        kwargs={"pk": workbasket.pk},
    )
    response = valid_user_client.get(url)
    soup = BeautifulSoup(str(response.content), "html.parser")
    # 11th column is conditions. We're interested in the first (and only) row.
    condition_text = soup.select("table tr td:nth-child(11)")[0].text

    assert "B" in condition_text
    assert certificate.code in condition_text
    assert "27" in condition_text


@patch("workbaskets.tasks.call_check_workbasket_sync.apply_async")
def test_run_business_rules(check_workbasket, valid_user_client, session_workbasket):
    """Test that a GET request to the run-business-rules endpoint returns a 302,
    redirecting to the review workbasket page, runs the `check_workbasket` task,
    saves the task id on the workbasket, and deletes pre-existing
    `TrackedModelCheck` objects associated with the workbasket."""
    check_workbasket.return_value.id = 123
    assert not session_workbasket.rule_check_task_id

    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        check = TrackedModelCheckFactory.create(
            transaction_check__transaction=transaction,
            model=good,
            successful=False,
        )

    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
    }
    session.save()
    url = reverse(
        "workbaskets:current-workbasket",
    )
    response = valid_user_client.post(
        url,
        {"form-action": "run-business-rules"},
    )

    assert response.status_code == 302
    # Only compare the response URL up to the query string.
    assert response.url[: len(url)] == url

    session_workbasket.refresh_from_db()

    check_workbasket.assert_called_once_with(
        (session_workbasket.pk,),
        countdown=1,
    )
    assert session_workbasket.rule_check_task_id
    assert not session_workbasket.tracked_model_checks.exists()


def test_workbasket_business_rule_status(valid_user_client):
    """Testing that the live status of a workbasket resets after an item has
    been updated, created or deleted in the workbasket."""
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with workbasket.new_transaction() as transaction:
        footnote = factories.FootnoteFactory.create(
            transaction=transaction,
            footnote_type__transaction=transaction,
        )
        TrackedModelCheckFactory.create(
            transaction_check__transaction=transaction,
            model=footnote,
            successful=True,
        )
    workbasket.save_to_session(valid_user_client.session)

    url = reverse("workbaskets:current-workbasket")
    response = valid_user_client.get(url)
    page = BeautifulSoup(response.content.decode(response.charset))
    success_banner = page.find(
        "div",
        attrs={"class": "govuk-notification-banner--success"},
    )
    assert success_banner

    footnote2 = factories.FootnoteFactory.create(
        transaction=workbasket.new_transaction(),
    )
    response = valid_user_client.get(url)
    page = BeautifulSoup(response.content.decode(response.charset))
    assert not page.find("div", attrs={"class": "govuk-notification-banner--success"})


def test_submit_for_packaging(valid_user_client, session_workbasket):
    """Test that a GET request to the submit-for-packaging endpoint returns a
    302, redirecting to the create packaged workbasket page."""
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        measure = factories.MeasureFactory.create(transaction=transaction)
        geo_area = factories.GeographicalAreaFactory.create(transaction=transaction)
        objects = [good, measure, geo_area]
        for obj in objects:
            TrackedModelCheckFactory.create(
                transaction_check__transaction=transaction,
                model=obj,
                successful=True,
            )
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()

    url = reverse(
        "workbaskets:current-workbasket",
    )
    response = valid_user_client.post(
        url,
        {"form-action": "submit-for-packaging"},
    )

    assert response.status_code == 302
    response_url = f"/publishing/create/"
    # Only compare the response URL up to the query string.
    assert response.url[: len(response_url)] == response_url


@pytest.fixture
def successful_business_rules_setup(session_workbasket, valid_user_client):
    """Sets up data and runs business rules."""
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        measure = factories.MeasureFactory.create(transaction=transaction)
        geo_area = factories.GeographicalAreaFactory.create(transaction=transaction)
        objects = [good, measure, geo_area]
        for obj in objects:
            TrackedModelCheckFactory.create(
                transaction_check__transaction=transaction,
                model=obj,
                successful=True,
            )
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()

    # run rule checks so unchecked_or_errored_transactions is set
    check_workbasket_sync(session_workbasket)


def import_batch_with_notification():
    import_batch = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
    )

    return factories.GoodsSuccessfulImportNotificationFactory(
        notified_object_pk=import_batch.id,
    )


@pytest.mark.parametrize(
    "import_batch_factory,disabled",
    [
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
                goods_import=True,
            ),
            True,
        ),
        (
            import_batch_with_notification,
            False,
        ),
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
            ),
            False,
        ),
        (
            lambda: None,
            False,
        ),
    ],
    ids=(
        "goods_import_no_notification",
        "goods_import_with_notification",
        "master_import",
        "no_import",
    ),
)
def test_submit_for_packaging_disabled(
    successful_business_rules_setup,
    valid_user_client,
    session_workbasket,
    import_batch_factory,
    disabled,
):
    """Test that the submit-for-packaging button is disabled when a notification
    has not been sent for a commodity code import (goods)"""

    import_batch = import_batch_factory()

    if import_batch:
        import_batch.workbasket_id = session_workbasket.id
        if isinstance(import_batch, ImportBatch):
            import_batch.save()

    response = valid_user_client.get(
        reverse("workbaskets:current-workbasket"),
    )

    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")

    packaging_button = soup.find("a", href="/publishing/create/")

    if disabled:
        assert packaging_button.has_attr("disabled")
    else:
        assert not packaging_button.has_attr("disabled")


def test_terminate_rule_check(valid_user_client, session_workbasket):
    session_workbasket.rule_check_task_id = 123

    url = reverse(
        "workbaskets:current-workbasket",
    )
    response = valid_user_client.post(
        url,
        {"form-action": "terminate-rule-check"},
    )
    assert response.status_code == 302
    assert response.url[: len(url)] == url

    session_workbasket.refresh_from_db()

    assert not session_workbasket.rule_check_task_id


def test_workbasket_violations(valid_user_client, session_workbasket):
    """Test that a GET request to the violations endpoint returns a 200 and
    displays the correct column values for one unsuccessful
    `TrackedModelCheck`."""
    url = reverse(
        "workbaskets:workbasket-ui-violations",
    )
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        check = TrackedModelCheckFactory.create(
            transaction_check__transaction=transaction,
            model=good,
            successful=False,
        )
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()
    response = valid_user_client.get(url)

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    table = page.findChildren("table")[0]
    row = table.findChildren("tr")[1]
    cells = row.findChildren("td")

    assert cells[0].text == str(check.pk)
    assert cells[1].text == good._meta.verbose_name.title()
    assert cells[2].text == check.rule_code
    assert cells[3].text == check.message
    assert cells[4].text == f"{check.transaction_check.transaction.created_at:%d %b %Y}"


def test_violation_detail_page(valid_user_client, session_workbasket):
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        check = TrackedModelCheckFactory.create(
            transaction_check__transaction=transaction,
            model=good,
            successful=False,
        )
    url = reverse(
        "workbaskets:workbasket-ui-violation-detail",
        kwargs={"wb_pk": session_workbasket.pk, "pk": check.pk},
    )
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()
    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")
    paragraphs_text = [e.text for e in soup.select("p")]
    assert check.rule_code in paragraphs_text
    assert check.message in paragraphs_text
    # Attribute does not exist yet. This will fail when we eventually add it
    with pytest.raises(AttributeError):
        assert check.solution


def test_violation_detail_page_superuser_override_last_violation(
    superuser_client,
    session_workbasket,
):
    """Override the last unsuccessful TrackedModelCheck on a
    TransactionCheck."""

    model_check = TrackedModelCheckFactory.create(
        successful=False,
        transaction_check__successful=False,
    )
    model_check.transaction_check.transaction.workbasket.save_to_session(
        superuser_client.session,
    )
    superuser_client.session.save()

    url = reverse(
        "workbaskets:workbasket-ui-violation-detail",
        kwargs={"wb_pk": session_workbasket.pk, "pk": model_check.pk},
    )
    response = superuser_client.post(url, data={"action": "delete"})

    assert response.status_code == 302
    redirect_url = reverse("workbaskets:workbasket-ui-violations")
    assert redirect_url in response["Location"]

    model_check.refresh_from_db()
    assert model_check.successful
    assert model_check.transaction_check.successful


def test_violation_detail_page_superuser_override_one_of_two_violation(
    superuser_client,
    session_workbasket,
):
    """Override an unsuccessful TrackedModelCheck on a TransactionCheck that has
    more TrackedModelCheck."""

    model_check = TrackedModelCheckFactory.create(
        successful=False,
        transaction_check__successful=False,
    )
    model_check.transaction_check.transaction.workbasket.save_to_session(
        superuser_client.session,
    )
    superuser_client.session.save()

    TrackedModelCheckFactory.create(
        successful=False,
        transaction_check=model_check.transaction_check,
    )

    assert (
        TrackedModelCheck.objects.filter(
            successful=False,
            transaction_check=model_check.transaction_check,
        ).count()
        == 2
    )

    url = reverse(
        "workbaskets:workbasket-ui-violation-detail",
        kwargs={"wb_pk": session_workbasket.pk, "pk": model_check.pk},
    )
    response = superuser_client.post(url, data={"action": "delete"})

    assert response.status_code == 302
    redirect_url = reverse("workbaskets:workbasket-ui-violations")
    assert redirect_url in response["Location"]

    assert (
        TrackedModelCheck.objects.filter(
            successful=False,
            transaction_check=model_check.transaction_check,
        ).count()
        == 1
    )
    model_check.refresh_from_db()
    assert model_check.successful == True
    assert model_check.transaction_check.successful == False


def test_violation_detail_page_non_superuser_override_violation(
    valid_user_client,
    session_workbasket,
):
    """Ensure a user without superuser status is unable to override a
    TrackedModelCheck."""

    model_check = TrackedModelCheckFactory.create(
        successful=False,
        transaction_check__successful=False,
    )
    model_check.transaction_check.transaction.workbasket.save_to_session(
        valid_user_client.session,
    )
    valid_user_client.session.save()

    url = reverse(
        "workbaskets:workbasket-ui-violation-detail",
        kwargs={"wb_pk": session_workbasket.pk, "pk": model_check.pk},
    )
    response = valid_user_client.post(url, data={"action": "delete"})

    assert response.status_code == 302
    model_check.refresh_from_db()
    assert not model_check.successful
    assert not model_check.transaction_check.successful


@pytest.fixture
def setup(session_workbasket, valid_user_client):
    with session_workbasket.new_transaction() as transaction:
        good = factories.GoodsNomenclatureFactory.create(transaction=transaction)
        measure = factories.MeasureFactory.create(transaction=transaction)
        geo_area = factories.GeographicalAreaFactory.create(transaction=transaction)
        regulation = factories.RegulationFactory.create(transaction=transaction)
        additional_code = factories.AdditionalCodeFactory.create(
            transaction=transaction,
        )
        certificate = factories.CertificateFactory.create(transaction=transaction)
        footnote = factories.FootnoteFactory.create(transaction=transaction)
        objects = [
            good,
            measure,
            geo_area,
            regulation,
            additional_code,
            certificate,
            footnote,
        ]
        for obj in objects:
            TrackedModelCheckFactory.create(
                transaction_check__transaction=transaction,
                model=obj,
                successful=False,
            )
    session = valid_user_client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "error_count": session_workbasket.tracked_model_check_errors.count(),
    }
    session.save()


def test_violation_list_page_sorting_date(setup, valid_user_client, session_workbasket):
    """Tests the sorting of the queryset when GET params are set."""
    url = reverse(
        "workbaskets:workbasket-ui-violations",
    )
    response = valid_user_client.get(f"{url}?sort_by=date&order=asc")

    assert response.status_code == 200

    checks = session_workbasket.tracked_model_check_errors

    soup = BeautifulSoup(str(response.content), "html.parser")
    activity_dates = [
        element.text for element in soup.select("table tbody tr td:nth-child(5)")
    ]
    exp_dates = sorted(
        [f"{c.transaction_check.transaction.created_at:%d %b %Y}" for c in checks],
    )

    assert activity_dates == exp_dates

    response = valid_user_client.get(f"{url}?sort_by=date&order=desc")
    exp_dates.reverse()

    assert activity_dates == exp_dates


def test_violation_list_page_sorting_model_name(
    setup,
    valid_user_client,
    session_workbasket,
):
    """Tests the sorting of the queryset when GET params are set."""
    url = reverse(
        "workbaskets:workbasket-ui-violations",
    )
    response = valid_user_client.get(f"{url}?sort_by=model&order=asc")

    assert response.status_code == 200

    checks = session_workbasket.tracked_model_check_errors

    soup = BeautifulSoup(str(response.content), "html.parser")
    activity_dates = [
        element.text for element in soup.select("table tbody tr td:nth-child(5)")
    ]
    exp_dates = sorted(
        [f"{c.transaction_check.transaction.created_at:%d %b %Y}" for c in checks],
    )

    assert activity_dates == exp_dates

    response = valid_user_client.get(f"{url}?sort_by=model&order=desc")
    exp_dates.reverse()

    assert activity_dates == exp_dates


def test_violation_list_page_sorting_check_name(
    setup,
    valid_user_client,
    session_workbasket,
):
    """Tests the sorting of the queryset when GET params are set."""
    url = reverse(
        "workbaskets:workbasket-ui-violations",
    )
    response = valid_user_client.get(f"{url}?sort_by=check_name&order=asc")

    assert response.status_code == 200

    checks = session_workbasket.tracked_model_check_errors

    soup = BeautifulSoup(str(response.content), "html.parser")
    rule_codes = [
        element.text for element in soup.select("table tbody tr td:nth-child(3)")
    ]
    exp_rule_codes = sorted([c.rule_code for c in checks])

    assert rule_codes == exp_rule_codes

    response = valid_user_client.get(f"{url}?sort_by=check_name&order=desc")
    exp_rule_codes.reverse()
    assert rule_codes == exp_rule_codes


def test_violation_list_page_sorting_ignores_invalid_params(
    setup,
    valid_user_client,
    session_workbasket,
):
    """Tests that the page doesn't break if invalid params are sent."""
    url = reverse(
        "workbaskets:workbasket-ui-violations",
    )
    response = valid_user_client.get(f"{url}?sort_by=foo&order=bar")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "url_name,",
    (
        "workbaskets:workbasket-ui-detail",
        "workbaskets:workbasket-ui-changes",
    ),
)
def test_workbasket_detail_views_without_permission(url_name, client):
    """Tests that `WorkBasketDetailView` and `WorkBasketChangesView` return 403
    to users without `view_workbasket` permission."""

    workbasket = factories.WorkBasketFactory.create()
    url = reverse(url_name, kwargs={"pk": workbasket.pk})
    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.get(url)

    assert response.status_code == 403


def test_workbasket_detail_view_displays_workbasket_details(
    valid_user_client,
    session_workbasket,
):
    """Tests that `WorkBasketDetailView` returns 200 and displays workbasket
    details in table."""

    url = reverse(
        "workbaskets:workbasket-ui-detail",
        kwargs={"pk": session_workbasket.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")
    table = soup.select("table")[0]
    row_text = [row.text for row in table.findChildren("td")]

    assert session_workbasket.get_status_display().upper() in row_text[0]
    assert str(session_workbasket.id) in row_text[1]
    assert session_workbasket.title in row_text[2]
    assert session_workbasket.reason in row_text[3]
    assert str(session_workbasket.tracked_models.count()) in row_text[4]
    assert session_workbasket.created_at.strftime("%d %b %y %H:%M") in row_text[5]
    assert session_workbasket.updated_at.strftime("%d %b %y %H:%M") in row_text[6]


def test_workbasket_changes_view_without_change_permission(client, session_workbasket):
    """Tests that `WorkBasketChangesView` displays changes in a workbasket
    without the ability to remove items to users without `change_workbasket`
    permission."""

    url = reverse(
        "workbaskets:workbasket-ui-changes",
        kwargs={"pk": session_workbasket.pk},
    )
    user = factories.UserFactory.create()
    user.user_permissions.add(Permission.objects.get(codename="view_workbasket"))
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    columns = page.select(".govuk-table__header")
    rows = page.select("tbody > tr")
    checkboxes = page.select(".govuk-checkboxes__input")
    remove_button = page.find("button", value="remove-selected")

    assert len(columns) == 5
    assert len(rows) == session_workbasket.tracked_models.count()
    assert not checkboxes
    assert not remove_button


def test_workbasket_changes_view_with_change_permission(
    valid_user_client,
    session_workbasket,
):
    """Tests that `WorkBasketChangesView` displays changes in a workbasket with
    the ability to remove items to users with `change_workbasket` permission."""

    url = reverse(
        "workbaskets:workbasket-ui-changes",
        kwargs={"pk": session_workbasket.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    columns = page.select(".govuk-table__header")
    rows = page.select("tbody > tr")
    checkboxes = page.select(".govuk-checkboxes__input")
    remove_button = page.find("button", value="remove-selected")

    assert len(columns) == 6
    assert len(rows) == session_workbasket.tracked_models.count()
    assert checkboxes
    assert remove_button


@pytest.mark.parametrize(
    ("page_param", "expected_item_count", "load_more"),
    [
        ("?page=1", 1, True),
        ("?page=2", 2, True),
        ("?page=3", 3, False),
    ],
)
def test_workbasket_changes_view_pagination(
    page_param,
    expected_item_count,
    load_more,
    valid_user_client,
):
    """Tests that `WorkBasketChangesView` paginates items in workbasket,
    returning the previous pages' results plus the new page's result (according
    to `paginate_by`) upon loading more."""

    workbasket = factories.WorkBasketFactory.create()
    with workbasket.new_transaction() as transaction:
        factories.SimpleGoodsNomenclatureFactory.create_batch(
            3,
            transaction=transaction,
        )
    total_item_count = workbasket.tracked_models.count()
    assert total_item_count == 3

    with patch("workbaskets.views.ui.WorkBasketChangesView.paginate_by", 1):
        url = reverse("workbaskets:workbasket-ui-changes", kwargs={"pk": workbasket.pk})
        response = valid_user_client.get(url + page_param)
        assert response.status_code == 200

        page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
        rows = page.select("tbody > tr")
        pagination_text = page.select(".pagination > p")[0].text
        progress_bar = page.find(
            "progress",
            value=expected_item_count,
            max=total_item_count,
        )
        load_more_button = page.find("button", value="page-next")

        assert len(rows) == expected_item_count
        assert (
            f"You've viewed {expected_item_count} out of {total_item_count} items"
            in pagination_text
        )
        assert progress_bar
        if load_more:
            assert load_more_button
        else:
            assert not load_more_button


@pytest.mark.parametrize(
    ("ordering_param", "expected_ordering"),
    [
        ("?sort_by=component&ordered=asc", "polymorphic_ctype"),
        ("?sort_by=component&ordered=desc", "-polymorphic_ctype"),
        ("?sort_by=action&ordered=asc", "update_type"),
        ("?sort_by=action&ordered=desc", "-update_type"),
        ("?sort_by=activity_date&ordered=asc", "transaction__updated_up"),
        ("?sort_by=activity_date&ordered=desc", "-transaction__updated_up"),
    ],
)
def test_workbasket_changes_view_sort_by_queryset(ordering_param, expected_ordering):
    """Tests that `WorkBasketChangesView` orders queryset according to `sort_by`
    and `ordered` GET request URL params."""

    additional_code_type = factories.AdditionalCodeTypeFactory.create()
    workbasket = factories.WorkBasketFactory.create()
    additional_code = factories.AdditionalCodeFactory.create(
        type=additional_code_type,
        transaction=workbasket.new_transaction(),
    )
    additional_code_description = factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=additional_code,
        transaction=workbasket.new_transaction(),
    )
    additional_code.new_version(
        update_type=UpdateType.DELETE,
        workbasket=workbasket,
        transaction=workbasket.new_transaction(),
    )

    request = RequestFactory()
    url = reverse("workbaskets:workbasket-ui-changes", kwargs={"pk": workbasket.pk})
    get_request = request.get(url + ordering_param)
    view = ui.WorkBasketChangesView(request=get_request, kwargs={"pk": workbasket.pk})
    assert list(view.get_queryset()) == list(
        workbasket.tracked_models.order_by(expected_ordering),
    )


def test_workbasket_changes_view_remove_selected(valid_user_client):
    """Tests that items in a workbasket can be selected and removed on
    `WorkBasketChangesView`."""

    footnote_type = factories.FootnoteTypeFactory.create()
    workbasket = factories.WorkBasketFactory.create()
    footnote = factories.FootnoteFactory.create(
        footnote_type=footnote_type,
        transaction=workbasket.new_transaction(),
    )
    footnote_description = footnote.descriptions.first()
    assert workbasket.tracked_models.count() == 2

    form_data = {
        "form-action": "remove-selected",
        f"selectableobject_{footnote.pk}": True,
        f"selectableobject_{footnote_description.pk}": True,
    }
    view_url = reverse(
        "workbaskets:workbasket-ui-changes",
        kwargs={"pk": workbasket.pk},
    )
    delete_changes_url = reverse(
        "workbaskets:workbasket-ui-changes-delete",
        kwargs={"pk": workbasket.pk},
    )
    confirm_delete_url = reverse(
        "workbaskets:workbasket-ui-changes-confirm-delete",
        kwargs={"pk": workbasket.pk},
    )

    response = valid_user_client.post(view_url, form_data)
    assert response.status_code == 302
    assert response.url == delete_changes_url

    response = valid_user_client.post(delete_changes_url, {"action": "delete"})
    assert response.status_code == 302
    assert response.url == confirm_delete_url
    assert workbasket.tracked_models.count() == 0


def test_successfully_delete_workbasket(
    valid_user_client,
    valid_user,
    session_empty_workbasket,
):
    """Test that deleting an empty workbasket by a user having the necessary
    `workbasket.can_delete` permssion."""

    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_workbasket"),
    )
    workbasket_pk = session_empty_workbasket.pk
    delete_url = reverse(
        "workbaskets:workbasket-ui-delete",
        kwargs={"pk": workbasket_pk},
    )

    # GET the form view.
    response = valid_user_client.get(delete_url)
    page = BeautifulSoup(response.content, "html.parser")
    assert response.status_code == 200
    assert f"Delete workbasket {workbasket_pk}" in page.select("main h1")[0].text

    # POST the delete form.
    response = valid_user_client.post(delete_url, {})
    assert response.status_code == 302
    assert response.url == reverse(
        "workbaskets:workbasket-ui-delete-done",
        kwargs={"deleted_pk": workbasket_pk},
    )
    assert not models.WorkBasket.objects.filter(pk=workbasket_pk)

    # GET the deletion done page for the URL provided by the redirect response.
    response = valid_user_client.get(response.url)
    page = BeautifulSoup(response.content, "html.parser")
    assert response.status_code == 200
    assert (
        f"Workbasket {workbasket_pk} has been deleted"
        in page.select(".govuk-panel h1")[0].text
    )


def test_delete_workbasket_missing_user_permission(
    valid_user_client,
    session_empty_workbasket,
):
    """Test that attempts to access the delete workbasket view and delete a
    workbasket fails for a user without the necessary permissions."""

    workbasket_pk = session_empty_workbasket.pk
    url = reverse(
        "workbaskets:workbasket-ui-delete",
        kwargs={"pk": workbasket_pk},
    )

    # Get the form view.
    get_response = valid_user_client.get(url)
    assert get_response.status_code == 403
    assert models.WorkBasket.objects.filter(pk=workbasket_pk)

    # POST the delete form.
    response = valid_user_client.post(url, {})
    assert response.status_code == 403
    assert models.WorkBasket.objects.filter(pk=workbasket_pk)


def test_delete_nonempty_workbasket(
    valid_user_client,
    valid_user,
    session_workbasket,
):
    """Test that attempts to delete a non-empty workbasket fails."""

    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_workbasket"),
    )
    workbasket_pk = session_workbasket.pk
    workbasket_object_count = session_workbasket.tracked_models.count()
    delete_url = reverse(
        "workbaskets:workbasket-ui-delete",
        kwargs={"pk": workbasket_pk},
    )
    assert workbasket_object_count

    # POST the delete form.
    response = valid_user_client.post(delete_url, {})
    assert response.status_code == 200

    page = BeautifulSoup(response.content, "html.parser")
    error_list = page.select("ul.govuk-list.govuk-error-summary__list")[0]
    assert error_list.find(
        text=re.compile(
            f"Workbasket {workbasket_pk} contains {workbasket_object_count} "
            f"item\(s\), but must be empty",
        ),
    )
    assert models.WorkBasket.objects.filter(pk=workbasket_pk)


def test_application_access_after_workbasket_delete(
    valid_user_client,
    session_empty_workbasket,
):
    """
    Test that after deleting a user's 'current' workbasket, the user is still
    able to access the application via a valid view - that is, a view unrelated
    to the deleted workbasket, which would obviously fail with a not found
    error. This is to ensure the user's session is left in a valid state after
    deleting their current workbasket - i.e. this test is concerned with
    ensuring application avoids 500-series errors under the above conditions.
    """

    workbasket_pk = session_empty_workbasket.pk
    url = reverse("workbaskets:workbasket-ui-list")

    response = valid_user_client.get(url)
    page = BeautifulSoup(response.content, "html.parser")
    # A workbasket link should be available in the header nav bar before
    # session workbasket deletion.
    assert response.status_code == 200

    assert (
        f"Workbasket {workbasket_pk}"
        in page.select("header nav a.workbasket-link")[0].text
    )

    session_empty_workbasket.delete()

    response = valid_user_client.get(url)
    page = BeautifulSoup(response.content, "html.parser")
    # No workbasket link should exist in the header nav bar after session
    # workbasket deletion.
    assert response.status_code == 200
    assert not page.select("header nav a.workbasket-link")


def test_workbasket_compare_200(valid_user_client, session_workbasket):
    url = reverse("workbaskets:workbasket-ui-compare")
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_workbasket_compare_prev_uploaded(valid_user_client, session_workbasket):
    factories.GoodsNomenclatureFactory()
    factories.GoodsNomenclatureFactory()
    factories.DataUploadFactory(workbasket=session_workbasket)
    url = reverse("workbaskets:workbasket-ui-compare")
    response = valid_user_client.get(url)
    assert "Worksheet data" in response.content.decode(response.charset)


def test_workbasket_update_prev_uploaded(valid_user_client, session_workbasket):
    factories.GoodsNomenclatureFactory()
    factories.GoodsNomenclatureFactory()
    data_upload = factories.DataUploadFactory(workbasket=session_workbasket)
    url = reverse("workbaskets:workbasket-ui-compare")
    data = {
        "data": (
            "0000000001\t1.000%\t20/05/2021\t31/08/2024\n"
            "0000000002\t2.000%\t20/05/2021\t31/08/2024"
        ),
    }
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    data_upload.refresh_from_db()
    assert data_upload.raw_data == data["data"]


def test_workbasket_compare_form_submit_302(valid_user_client, session_workbasket):
    url = reverse("workbaskets:workbasket-ui-compare")
    data = {
        "data": (
            "0000000001\t1.000%\t20/05/2021\t31/08/2024\n"
            "0000000002\t2.000%\t20/05/2021\t31/08/2024\n"
        ),
    }
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    assert response.url == url


def test_workbasket_compare_found_measures(
    valid_user_client,
    session_workbasket,
    date_ranges,
    duty_sentence_parser,
    percent_or_amount,
):
    commodity = factories.GoodsNomenclatureFactory()

    with session_workbasket.new_transaction():
        measure = factories.MeasureFactory(
            valid_between=date_ranges.normal,
            goods_nomenclature=commodity,
        )
        duty_string = "4.000%"
        # create measure components equivalent to a duty sentence of "4.000%"
        factories.MeasureComponentFactory.create(
            component_measure=measure,
            duty_expression=percent_or_amount,
            duty_amount=4.0,
            monetary_unit=None,
            component_measurement=None,
        )

    url = reverse("workbaskets:workbasket-ui-compare")
    data = {
        "data": (
            # this first line should match the measure in the workbasket
            f"{commodity.item_id}\t{duty_string}\t{date_ranges.normal.lower.isoformat()}\t{date_ranges.normal.upper.isoformat()}\n"
            "0000000002\t2.000%\t20/05/2021\t31/08/2024\n"
        ),
    }
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    assert response.url == url

    # view the uploaded data
    response2 = valid_user_client.get(response.url)
    assert response2.status_code == 200
    decoded = response2.content.decode(response2.charset)
    soup = BeautifulSoup(decoded, "html.parser")
    assert "1 matching measure found" in soup.select("h2")[1].text

    # previously uploaded data
    assert len(soup.select("tbody")[0].select("tr")) == 2

    # measure found
    assert len(soup.select("tbody")[1].select("tr")) == 1


def make_goods_import_batch(importer_storage, **kwargs):
    return factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
        **kwargs,
    )


@pytest.mark.skip(reason="Unable to mock s3 file read from within ET.parse currently")
@pytest.mark.parametrize(
    "import_batch_factory,visable",
    [
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
                goods_import=True,
                taric_file="goods.xml",
            ),
            True,
        ),
        (
            import_batch_with_notification,
            False,
        ),
        (
            lambda: factories.ImportBatchFactory.create(
                status=ImportBatchStatus.SUCCEEDED,
            ),
            False,
        ),
        (
            lambda: None,
            False,
        ),
    ],
    ids=(
        "goods_import_no_notification",
        "goods_import_with_notification",
        "master_import",
        "no_import",
    ),
)
def test_review_goods_notification_button(
    successful_business_rules_setup,
    valid_user_client,
    session_workbasket,
    import_batch_factory,
    visable,
):
    """Test that the submit-for-packaging button is disabled when a notification
    has not been sent for a commodity code import (goods)"""

    import_batch = import_batch_factory()

    if import_batch:
        import_batch.workbasket_id = session_workbasket.id
        if isinstance(import_batch, ImportBatch):
            import_batch.save()

    def mock_xlsx_open(filename, mode):
        if os.path.basename(filename) == "goods.xlsx":
            return mock_open().return_value
        return open(filename, mode)

    with patch(
        "importer.goods_report.GoodsReport.xlsx_file",
        return_value="",
    ) as mocked_xlsx_file:
        # with patch(
        #     ".open",
        #     mock_xlsx_open,
        # ):
        response = valid_user_client.get(
            reverse("workbaskets:workbasket-ui-review-goods"),
        )

    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")

    # notify_button = soup.find("a", href=f"/notify-goods-report/{import_batch.id}/")
    notify_button = soup.select(".govuk-body")

    print(notify_button)
    if visable:
        assert notify_button
    else:
        assert not notify_button
