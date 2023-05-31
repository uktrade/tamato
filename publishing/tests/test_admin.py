import pytest
from django.urls import reverse

from publishing.models import CrownDependenciesEnvelope

pytestmark = pytest.mark.django_db


def test_api_envelope_terminate_publishing_task(
    successful_envelope_factory,
    superuser_client,
):
    """Test that an envelope's publishing task can be terminated."""
    successful_envelope_factory()
    envelope = CrownDependenciesEnvelope.objects.first()
    envelope.publishing_task_id = "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p"

    change_url = reverse(
        "admin:publishing_crowndependenciesenvelope_change",
        args=[envelope.id],
    )
    response = superuser_client.post(
        change_url,
        data={
            "terminate_publishing_task": "on",
        },
    )

    assert response.status_code == 302
    envelope.refresh_from_db()
    assert not envelope.publishing_task_id
