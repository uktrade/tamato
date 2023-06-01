import pytest
from django.urls import reverse

from common.tests.factories import CrownDependenciesPublishingTaskFactory

pytestmark = pytest.mark.django_db


def test_crown_dependencies_publishing_task_terminate_task(
    superuser_client,
):
    """Test that a CrownDependenciesPublishingTask can be terminated."""

    publishing_task = CrownDependenciesPublishingTaskFactory.create()
    publishing_task.task_id = "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p"

    change_url = reverse(
        "admin:publishing_crowndependenciespublishingtask_change",
        args=[publishing_task.id],
    )
    response = superuser_client.post(
        change_url,
        data={
            "terminate_task": "true",
        },
    )

    assert response.status_code == 302
    publishing_task.refresh_from_db()
    assert not publishing_task.task_id
