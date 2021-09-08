from unittest import mock

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_upload_returns_302_for_valid_staff_user(staff_user, client):
    client.force_login(staff_user)
    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ):
        response = client.post(reverse("admin:upload"))

        assert response.status_code == 302
        assert response.url == reverse("admin:workbaskets_workbasket_changelist")


def test_upload_redirects_non_staff_to_login(client, valid_user):
    client.force_login(valid_user)
    response = client.post(reverse("admin:upload"))

    assert response.status_code == 302
    assert response.url == f"{reverse('admin:login')}?next={reverse('admin:upload')}"


def test_upload_doesnt_call_task_for_non_staff(client, valid_user):
    client.force_login(valid_user)
    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ) as mock_task:
        client.post(reverse("admin:upload"))

        mock_task.assert_not_called()


def test_upload_calls_task(staff_user, client):
    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ) as mock_task:
        client.force_login(staff_user)
        client.post(reverse("admin:upload"))

        mock_task.assert_called_once()
