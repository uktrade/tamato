import pytest
from django.urls import reverse

from workbaskets.validators import WorkflowStatus


@pytest.mark.django_db
def test_submit_workbasket(unapproved_transaction, valid_user_client):
    workbasket = unapproved_transaction.workbasket

    url = reverse(
        "workbaskets:submit_workbasket",
        kwargs={"workbasket_pk": workbasket.pk},
    )

    response = valid_user_client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("index")
    assert workbasket.status == WorkflowStatus.NEW_IN_PROGRESS
    workbasket.refresh_from_db()
    assert workbasket.status == WorkflowStatus.SENT_TO_CDS
    assert workbasket.approver is not None
