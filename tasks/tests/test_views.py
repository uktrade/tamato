import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskFactory
from tasks.models import ProgressState
from tasks.models import TaskLog
from tasks.tests.test_workflow_models import TaskItemTemplateFactory

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


def test_workflow_template_detail_view_displays_task_templates(valid_user_client):
    task_item_template = TaskItemTemplateFactory.create()
    task_template = task_item_template.task_template
    workflow_template = task_item_template.queue

    url = reverse(
        "workflow:task-workflow-template-ui-detail",
        kwargs={"pk": workflow_template.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    assert page.find("h1", text=workflow_template.title)
    assert page.find("a", text=task_template.title)


@pytest.mark.parametrize(
    ("client_type", "expected_status_code_get", "expected_status_code_post"),
    [
        ("valid_user_client", 200, 302),
        ("client_with_current_workbasket_no_permissions", 403, 403),
    ],
)
def test_delete_subtask_missing_user_permissions(
    client_type,
    expected_status_code_get,
    expected_status_code_post,
    request,
):
    """Tests that attempting to delete a subtask fails for users without the
    necessary permissions."""
    client_type = request.getfixturevalue(client_type)

    # Creating an instance of a subtask that will be deleted
    subtask_instance = SubTaskFactory.create(
        progress_state__name=ProgressState.State.TO_DO,
    )

    # The DeleteSubTask view and URL
    url = reverse(
        "workflow:subtask-ui-delete",
        kwargs={"pk": subtask_instance.pk},
    )

    # Test DeleteSubtask form view
    get_response = client_type.get(url)
    assert get_response.status_code == expected_status_code_get

    # POST the delete subtask form
    response = client_type.post(url)
    assert response.status_code == expected_status_code_post
