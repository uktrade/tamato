import pytest
from django.urls import reverse

from tasks.models import StateChoices

pytestmark = pytest.mark.django_db


def test_automation_create_workbasket_view(
    create_workbasket_automation_state_is_CAN_RUN,
    valid_user_client,
):
    url = reverse(
        "workbaskets:workbasket-automation-ui-create",
        kwargs={"pk": create_workbasket_automation_state_is_CAN_RUN.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    assert (
        create_workbasket_automation_state_is_CAN_RUN.get_state()
        == StateChoices.CAN_RUN
    )
    response = valid_user_client.post(url)
    assert response.status_code == 302
    create_workbasket_automation_state_is_CAN_RUN.refresh_from_db()
    assert (
        create_workbasket_automation_state_is_CAN_RUN.get_state() == StateChoices.DONE
    )
