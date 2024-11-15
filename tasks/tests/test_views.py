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


@pytest.mark.parametrize(
    ("object_type", "success_url"),
    [
        ("Task", "workflow:task-ui-confirm-create"),
        ("Subtask", "workflow:subtask-ui-confirm-create"),
    ],
    ids=("task test", "subtask test"),
)
def test_confirm_create_template_shows_task_or_subtask(
    valid_user_client,
    object_type,
    success_url,
):
    """Test the confirm create template distinguishes between subtask or task's
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


@pytest.mark.parametrize(
    ("task_factory", "expected_result"),
    [
        (TaskFactory, True),
        (SubTaskFactory, False),
    ],
    ids=("task test", "subtask test"),
)
def test_create_subtask_button_shows_only_for_non_parent_tasks(
    superuser_client,
    task_factory,
    expected_result,
):
    task = task_factory.create()

    url = reverse(
        "workflow:task-ui-detail",
        kwargs={
            "pk": task.pk,
        },
    )
    response = superuser_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    if expected_result:
        assert page.find("a", href=f"/tasks/{task.pk}/subtasks/create")
    else:
        assert not page.find("a", href=f"/tasks/{task.pk}/subtasks/create")


def test_create_subtask_form_errors_when_parent_is_subtask(valid_user_client):
    """Tests that the SubtaskCreateForm errors when a form is submitted that has
    a subtask as a parent."""

    subtask_parent = SubTaskFactory.create()
    progress_state = ProgressStateFactory.create()

    subtask_form_data = {
        "progress_state": progress_state.pk,
        "title": "subtask test title",
        "description": "subtask test description",
    }

    url = reverse(
        "workflow:subtask-ui-create",
        kwargs={
            "pk": subtask_parent.pk,
        },
    )

    response = valid_user_client.post(url, subtask_form_data)

    assert response.status_code == 200
    assert not response.context_data["form"].is_valid()
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert (
        "You cannot make a subtask from a subtask."
        in soup.find("div", class_="govuk-error-summary").text
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
