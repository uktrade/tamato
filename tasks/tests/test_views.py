import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskFactory
from tasks.models import ProgressState
from tasks.models import TaskLog

pytestmark = pytest.mark.django_db


def test_task_update_view_update_progress_state(valid_user_client):
    """Tests that `TaskUpdateView` updates `Task.progress_state` and that a
    related `TaskLog` entry is also created."""
    instance = TaskFactory.create(progress_state__name=ProgressState.State.TO_DO)
    new_progress_state = ProgressStateFactory.create(
        name=ProgressState.State.IN_PROGRESS,
    )
    form_data = {
        "progress_state": new_progress_state.pk,
        "title": instance.title,
        "description": instance.description,
    }
    url = reverse(
        "workflow:task-ui-update",
        kwargs={"pk": instance.pk},
    )
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    instance.refresh_from_db()

    assert instance.progress_state == new_progress_state
    assert TaskLog.objects.get(
        task=instance,
        action=TaskLog.AuditActionType.PROGRESS_STATE_UPDATED,
        instigator=response.wsgi_request.user,
    )


@pytest.mark.parametrize(
    ("object_type", "success_url"),
    [
        ("Task", "workflow:task-ui-confirm-create"),
        ("Subtask", "workflow:subtask-ui-confirm-create"),
    ],
    ids=("task test", "subtask test"),
)
def test_confirmcreate_template_shows_task_or_subtask(
    valid_user_client,
    object_type,
    success_url,
):
    """Test the confirm create template distinguishes between subtask or task
    creation."""

    parent_task_instance = TaskFactory.create(
        progress_state__name=ProgressState.State.TO_DO,
    )

    url = reverse(
        success_url,
        kwargs={
            "pk": parent_task_instance.pk,
        },
    )
    response = valid_user_client.get(url)

    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    expected_h1_text = f"{object_type}: {parent_task_instance.title}"

    assert expected_h1_text in page.find("h1").text


def test_create_subtask_button_only_shows_for_tasks_without_parents(
    superuser_client,
):
    """Test that 'create subtask' button is only visible on details page for
    task without parent task."""

    parent_task_instance = TaskFactory.create(
        progress_state__name=ProgressState.State.TO_DO,
    )
    SubTaskFactory.create()

    url = reverse(
        "workflow:task-ui-detail",
        kwargs={
            "pk": parent_task_instance.pk,
        },
    )
    response = superuser_client.get(url)

    assert response.status_code == 200

    subtask_create_url = url(
        "workflow:subtask-ui-create",
        kwargs={"pk": parent_task_instance.pk},
    )
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    assert page.find("a", href=subtask_create_url)
