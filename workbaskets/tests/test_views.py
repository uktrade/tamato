import pytest
from django.urls import reverse

from common.tests import factories
from common.tests.util import validity_period_post_data
from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_submit_workbasket(unapproved_transaction, valid_user, client):
    workbasket = unapproved_transaction.workbasket

    url = reverse(
        "workbaskets:workbasket-ui-submit",
        kwargs={"pk": workbasket.pk},
    )

    client.force_login(valid_user)
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("index")

    workbasket = WorkBasket.objects.get(pk=workbasket.pk)
    assert workbasket.status == WorkflowStatus.SENT
    assert workbasket.approver is not None

    assert client.session["workbasket"]["status"] == WorkflowStatus.SENT


def test_edit_after_submit(valid_user, client, date_ranges):
    client.force_login(valid_user)

    # submit a workbasket containing a newly created footnote
    workbasket = factories.WorkBasketFactory.create()
    with workbasket.new_transaction():
        footnote = factories.FootnoteFactory.create(
            update_type=UpdateType.CREATE,
        )

    response = client.get(
        reverse(
            "workbaskets:workbasket-ui-submit",
            kwargs={"pk": workbasket.pk},
        ),
    )
    assert response.status_code == 302

    # edit the footnote
    response = client.post(
        footnote.get_url("edit"),
        validity_period_post_data(
            date_ranges.later.lower,
            date_ranges.later.upper,
        ),
    )
    assert response.status_code == 302

    # check that the session workbasket has been replaced by a new one
    session_workbasket = WorkBasket.load_from_session(client.session)
    assert session_workbasket.id != workbasket.id

    # check that the footnote edit is in the new session workbasket
    assert session_workbasket.transactions.count() == 1
    tx = session_workbasket.transactions.first()
    assert tx.tracked_models.count() == 1
    new_footnote_version = tx.tracked_models.first()
    assert new_footnote_version.pk != footnote.pk
