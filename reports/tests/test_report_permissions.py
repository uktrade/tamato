from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_can_only_view_report_with_relevant_permission(client, valid_user):
    client.force_login(valid_user)
    response = client.get(reverse("reports:index"))
    assert response.status_code == 302

    group = Group.objects.first()
    for app_label, codename in [
        ("reports", "view_report"),
        ("reports", "view_report_index"),
    ]:
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            ),
        )

    valid_response = client.get(reverse("reports:index"))
    assert valid_response.status_code == 200
