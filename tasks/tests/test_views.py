import factory
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests.factories import ProgressStateFactory
from common.tests.factories import TaskFactory
from tasks.models import ProgressState
from tasks.models import TaskLog
from tasks.models import TaskWorkflowTemplate
from tasks.tests.factories import TaskItemTemplateFactory


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
    ("action", "item_position", "expected_item_order"),
    [
        ("promote", 1, [1, 2, 3]),
        ("promote", 2, [2, 1, 3]),
        ("demote", 2, [1, 3, 2]),
        ("demote", 3, [1, 2, 3]),
        ("promote_to_first", 3, [3, 1, 2]),
        ("demote_to_last", 1, [2, 3, 1]),
    ],
)
def test_workflow_template_detail_view_reorder_items(
    action,
    item_position,
    expected_item_order,
    valid_user_client,
    task_workflow_template_three_task_template_items,
):
    """Tests that `TaskWorkflowTemplateDetailView` handles POST requests to
    promote or demote task templates."""

    def convert_to_index(position: int) -> int:
        """Converts a 1-based item position to a 0-based index for items array
        access."""
        return position - 1

    items = list(task_workflow_template_three_task_template_items.get_items())
    item_to_move = items[convert_to_index(item_position)]

    url = reverse(
        "workflow:task-workflow-template-ui-detail",
        kwargs={"pk": task_workflow_template_three_task_template_items.pk},
    )
    form_data = {
        action: item_to_move.id,
    }

    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    reordered_items = task_workflow_template_three_task_template_items.get_items()
    for i, reordered_item in enumerate(reordered_items):
        expected_position = convert_to_index(expected_item_order[i])
        expected_item = items[expected_position]
        assert reordered_item.id == expected_item.id


def test_workflow_template_create_view(valid_user_client):
    """Tests that a new workflow template can be created and that the
    corresponding confirmation view returns a HTTP 200 response."""

    assert not TaskWorkflowTemplate.objects.exists()

    create_url = reverse("workflow:task-workflow-template-ui-create")
    form_data = {
        "title": "Test workflow template",
        "description": "Test description",
    }
    create_response = valid_user_client.post(create_url, form_data)

    created_workflow_template = TaskWorkflowTemplate.objects.get(
        title=form_data["title"],
        description=form_data["description"],
    )
    confirmation_url = reverse(
        "workflow:task-workflow-template-ui-confirm-create",
        kwargs={"pk": created_workflow_template.pk},
    )
    assert create_response.status_code == 302
    assert create_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")

    assert confirmation_response.status_code == 200
    assert (
        created_workflow_template.title in soup.select("h1.govuk-panel__title")[0].text
    )


def test_create_task_template_view(valid_user_client, task_workflow_template):
    """Test the view for creating new TaskTemplates and the confirmation view
    that a successful creation redirects to."""

    assert task_workflow_template.get_task_templates().count() == 0

    create_url = reverse(
        "workflow:task-template-ui-create",
        kwargs={"workflow_template_pk": task_workflow_template.pk},
    )
    form_data = {
        "title": factory.Faker("sentence"),
        "description": factory.Faker("sentence"),
    }
    create_response = valid_user_client.post(create_url, form_data)
    created_task_template = task_workflow_template.get_task_templates().get()
    confirmation_url = reverse(
        "workflow:task-template-ui-confirm-create",
        kwargs={"pk": created_task_template.pk},
    )

    assert create_response.status_code == 302
    assert task_workflow_template.get_task_templates().count() == 1
    assert create_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")

    assert confirmation_response.status_code == 200
    assert created_task_template.title in soup.select("h1.govuk-panel__title")[0].text


def test_task_template_detail_view(
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    task_template = (
        task_workflow_template_single_task_template_item.get_task_templates().get()
    )
    url = reverse("workflow:task-template-ui-detail", kwargs={"pk": task_template.pk})
    response = valid_user_client.get(url)

    soup = BeautifulSoup(str(response.content), "html.parser")

    assert response.status_code == 200
    assert (
        task_template.title
        in soup.select("div.govuk-summary-list__row:nth-child(2) > dd:nth-child(2)")[
            0
        ].text
    )


def test_update_task_template_view(
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    """Test the view for updating TaskTemplates and the confirmation view that a
    successful update redirects to."""

    assert (
        task_workflow_template_single_task_template_item.get_task_templates().count()
        == 1
    )

    task_template = (
        task_workflow_template_single_task_template_item.get_task_templates().get()
    )
    update_url = reverse(
        "workflow:task-template-ui-update",
        kwargs={"pk": task_template.pk},
    )
    appended_text = "updated"
    form_data = {
        "title": f"{task_template.title} {appended_text}",
        "description": f"{task_template.description} {appended_text}",
    }
    update_response = valid_user_client.post(update_url, form_data)
    updated_task_template = (
        task_workflow_template_single_task_template_item.get_task_templates().get()
    )
    confirmation_url = reverse(
        "workflow:task-template-ui-confirm-update",
        kwargs={"pk": updated_task_template.pk},
    )

    assert update_response.status_code == 302
    assert update_response.url == confirmation_url
    assert (
        task_workflow_template_single_task_template_item.get_task_templates().count()
        == 1
    )
    assert updated_task_template.title.endswith(appended_text)
    assert updated_task_template.description.endswith(appended_text)

    confirmation_response = valid_user_client.get(confirmation_url)

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")

    assert confirmation_response.status_code == 200
    assert updated_task_template.title in soup.select("h1.govuk-panel__title")[0].text
