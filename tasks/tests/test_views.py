import factory
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests.factories import ProgressStateFactory
from common.tests.factories import TaskFactory
from tasks.models import ProgressState
from tasks.models import TaskLog
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
