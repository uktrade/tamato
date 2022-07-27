from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.test import override_settings
from django.urls import reverse

from common.tests import factories
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.util import validity_period_post_data
from common.validators import UpdateType
from exporter.tasks import upload_workbaskets
from workbaskets import models
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.tests.util import assert_workbasket_valid
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_workbasket_create_form_creates_workbasket_object(
    valid_user_api_client,
):

    # Post a form
    create_url = reverse("workbaskets:workbasket-ui-create")

    form_data = {
        "title": "My new workbasket",
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


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPOGATES=True)
@patch("exporter.tasks.upload_workbaskets")
def test_submit_workbasket(
    mock_upload,
    approved_transaction,
    unapproved_transaction,
    valid_user,
    client,
):
    workbasket = unapproved_transaction.workbasket
    assert_workbasket_valid(workbasket)

    url = reverse(
        "workbaskets:workbasket-ui-submit",
        kwargs={"pk": workbasket.pk},
    )

    client.force_login(valid_user)
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("home")

    workbasket.refresh_from_db()

    assert workbasket.approver is not None
    assert "workbasket" not in client.session
    mock_upload.delay.assert_called_once_with()


@pytest.mark.parametrize(
    ("other_statuses", "should_reuse"),
    (
        ({}, False),
        ({WorkflowStatus.PROPOSED, WorkflowStatus.ARCHIVED}, False),
        ({WorkflowStatus.EDITING}, True),
    ),
    ids=(
        "will create basket if none exists",
        "will not reuse unapproved baskets",
        "will reuse basket in EDITING state",
    ),
)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPOGATES=True)
@patch("exporter.tasks.upload_workbaskets")
def test_edit_after_submit(
    upload,
    valid_user_client,
    date_ranges,
    other_statuses,
    should_reuse,
):
    # submit a workbasket containing a newly created footnote
    workbasket = factories.WorkBasketFactory.create()
    with workbasket.new_transaction():
        footnote = factories.FootnoteFactory.create(
            update_type=UpdateType.CREATE,
        )
    assert footnote.transaction.workbasket == workbasket

    assert_workbasket_valid(workbasket)

    # create workbaskets in different unapproved states
    # to check that the system doesn't select these
    other_baskets = [
        factories.WorkBasketFactory.create(status=other_status)
        for other_status in other_statuses
    ]

    response = valid_user_client.get(
        reverse(
            "workbaskets:workbasket-ui-submit",
            kwargs={"pk": workbasket.pk},
        ),
    )
    assert response.status_code == 302

    # edit the footnote description start date, to avoid FO4 violation
    description = footnote.descriptions.first()
    description.validity_start = date_ranges.later.lower
    description.save(force_write=True)

    # edit the footnote
    response = valid_user_client.post(
        footnote.get_url("edit"),
        validity_period_post_data(
            date_ranges.later.lower,
            date_ranges.later.upper,
        ),
    )
    assert response.status_code == 302

    # check that the session workbasket has been replaced by a new one
    session_workbasket = WorkBasket.load_from_session(valid_user_client.session)
    assert session_workbasket.id != workbasket.id
    assert session_workbasket.status == WorkflowStatus.EDITING
    assert (session_workbasket in other_baskets) == should_reuse

    # check that the footnote edit is in the new session workbasket
    assert session_workbasket.transactions.count() == 1
    tx = session_workbasket.transactions.first()
    assert tx.tracked_models.count() == 1
    new_footnote_version = tx.tracked_models.first()
    assert new_footnote_version.pk != footnote.pk
    assert new_footnote_version.version_group == footnote.version_group


def test_download(
    approved_workbasket,
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
        GoodsNomenclatureFactory.create()

    response = valid_user_client.get(
        reverse("workbaskets:review-workbasket", kwargs={"pk": session_workbasket.id}),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    for obj in session_workbasket.tracked_models.all():
        field_name = SelectableObjectsForm.field_name_for_object(obj)
        assert page.find("input", {"name": field_name})


def test_edit_workbasket_page_sets_workbasket(valid_user_client, session_workbasket):
    response = valid_user_client.get(
        reverse("workbaskets:edit-workbasket", kwargs={"pk": session_workbasket.pk}),
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert session_workbasket.title in soup.select(".govuk-heading-xl")[0].text
    assert str(session_workbasket.pk) in soup.select(".govuk-heading-xl")[0].text


@pytest.mark.parametrize(
    "url_name",
    [
        ("workbaskets:edit-workbasket"),
        ("workbaskets:review-workbasket"),
        ("workbaskets:workbasket-ui-detail"),
    ],
)
def test_edit_workbasket_page_displays_breadcrumb(
    url_name,
    valid_user_client,
    session_workbasket,
):
    url = reverse(url_name, kwargs={"pk": session_workbasket.pk})
    response = valid_user_client.get(
        f"{url}?edit=1",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    breadcrumb_links = [
        element.text for element in soup.select(".govuk-breadcrumbs__link")
    ]
    assert "Edit an existing workbasket" in breadcrumb_links


def test_workbasket_detail_page_url_params(
    valid_user_client,
    session_workbasket,
):
    url = reverse(
        "workbaskets:workbasket-ui-detail",
        kwargs={"pk": session_workbasket.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    buttons = soup.select(".govuk-button.govuk-button--primary")
    for button in buttons:
        # test that accidental spacing in template hasn't mangled the url
        assert " " not in button.get("href")
        assert "%20" not in button.get("href")


def test_edit_workbasket_page_hides_breadcrumb(valid_user_client, session_workbasket):
    url = reverse("workbaskets:edit-workbasket", kwargs={"pk": session_workbasket.pk})
    response = valid_user_client.get(
        f"{url}?edit=",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    breadcrumb_links = [
        element.text for element in soup.select(".govuk-breadcrumbs__link")
    ]
    assert "Edit an existing workbasket" not in breadcrumb_links


def test_select_workbasket_page_200(valid_user_client):
    """
    Checks the page returns 200.

    Then checks that only workbaskets with certain statuses are displayed i.e.
    we don't want users to be able to edit workbaskets that are archived, sent,
    or published.
    """
    factories.WorkBasketFactory.create(status=WorkflowStatus.ARCHIVED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.SENT)
    factories.WorkBasketFactory.create(status=WorkflowStatus.PUBLISHED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    factories.WorkBasketFactory.create(status=WorkflowStatus.APPROVED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.PROPOSED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.ERRORED)
    valid_statuses = {
        WorkflowStatus.EDITING,
        WorkflowStatus.APPROVED,
        WorkflowStatus.PROPOSED,
        WorkflowStatus.ERRORED,
    }
    response = valid_user_client.get(reverse("workbaskets:workbasket-ui-list"))
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    statuses = [
        element.text for element in soup.select(".govuk-table__row .status-badge")
    ]
    assert len(statuses) == 4
    assert not set(statuses).difference(valid_statuses)


@pytest.mark.parametrize(
    "form_action, url_name",
    [
        ("publish-all", "workbaskets:workbasket-ui-submit"),
        ("remove-selected", "workbaskets:workbasket-ui-delete-changes"),
        ("page-prev", "workbaskets:review-workbasket"),
        ("page-next", "workbaskets:review-workbasket"),
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
        factories.FootnoteTypeFactory.create_batch(30, transaction=tx)
    url = reverse("workbaskets:review-workbasket", kwargs={"pk": workbasket.pk})
    data = {"form-action": form_action}
    response = valid_user_client.post(f"{url}?page=2", data)
    assert response.status_code == 302
    assert reverse(url_name, kwargs={"pk": workbasket.pk}) in response.url

    if form_action == "page-prev":
        assert "?page=1" in response.url

    elif form_action == "page-next":
        assert "?page=3" in response.url


def test_delete_changes_confirm_200(valid_user_client, session_workbasket):
    url = reverse(
        "workbaskets:workbasket-ui-delete-changes-done",
        kwargs={"pk": session_workbasket.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200
