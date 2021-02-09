import pytest
from django.test import Client
from django.urls import reverse

from common.tests import factories
from exporter import views


@pytest.mark.django_db
def test_activity_stream(admin_client: Client):
    certificate_type = factories.CertificateTypeFactory.create()
    factories.CertificateFactory.create_batch(50, certificate_type=certificate_type)
    response = admin_client.get(reverse("activity-stream"))

    assert response.status_code == 200
    data = response.json()
    assert data["@context"] == [
        "https://www.w3.org/ns/activitystreams",
        {"dit": "https://www.trade.gov.uk/ns/activitystreams/v1"},
    ]
    assert data["type"] == "Collection"
    certificate_data = data["orderedItems"]
    assert len(certificate_data) == 50
    object_data = certificate_data[0]["object"]
    assert "dit:TaMaTo:Certificate:sid" in object_data
    # Make sure we replace relations with activity stream IDs
    assert object_data[
        "dit:TaMaTo:Certificate:certificate_type"
    ] == views.get_activity_stream_item_id(certificate_type)

    # Test the next page as well
    next = data["next"]
    next_response = admin_client.get(next)
    assert next_response.status_code == 200
    next_data = next_response.json()
    assert (
        len(next_data["orderedItems"]) == 1
    )  # Should just be the CertificateType as that is the 51st item.
    assert "next" not in next_data
