import pytest
from django.urls import reverse

from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_index_creates_workbasket_if_needed(valid_user_client, approved_workbasket):
    assert WorkBasket.objects.is_not_approved().count() == 0
    response = valid_user_client.get(reverse("index"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


def test_index_doesnt_creates_workbasket_if_not_needed(
    valid_user_client,
    new_workbasket,
):
    assert WorkBasket.objects.is_not_approved().count() == 1
    response = valid_user_client.get(reverse("index"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1
