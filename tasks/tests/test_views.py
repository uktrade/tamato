import factory
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskFactory
from tasks.forms import TaskWorkflowCreateForm
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskItem
from tasks.models import TaskItemTemplate
from tasks.models import TaskLog
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from tasks.tests.factories import TaskItemTemplateFactory

pytestmark = pytest.mark.django_db

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
    ("task_factory", "update_url"),
    [
        (TaskFactory, "workflow:task-ui-update"),
        (SubTaskFactory, "workflow:subtask-ui-update"),
    ],
    ids=("task test", "subtask test"),
)
def test_update_link_changes_for_task_and_subtask(
    superuser_client,
    task_factory,
    update_url,
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

    update_link = reverse(
        update_url,
        kwargs={
            "pk": task.pk,
        },
    )
    assert page.find("a", href=update_link)


@pytest.mark.parametrize(
    ("task_factory"),
    [TaskFactory, SubTaskFactory],
    ids=("task test", "subtask test"),
)
def test_create_subtask_button_shows_only_for_non_parent_tasks(
    superuser_client,
    task_factory,
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

    create_subtask_url = reverse(
        "workflow:subtask-ui-create",
        kwargs={"parent_task_pk": task.pk},
    )

    assert bool(page.find("a", href=create_subtask_url)) != task.is_subtask


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
            "parent_task_pk": subtask_parent.pk,
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
    subtask_instance = SubTaskFactory.create(
        progress_state__name=ProgressState.State.TO_DO,
    )

    url = reverse(
        "workflow:subtask-ui-delete",
        kwargs={"pk": subtask_instance.pk},
    )

    get_response = client_type.get(url)
    assert get_response.status_code == expected_status_code_get

    response = client_type.post(url)
    assert response.status_code == expected_status_code_post


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
    assert page.find("h1", text=f"Workflow template: {workflow_template.title}")
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

    items = list(task_workflow_template_three_task_template_items.get_task_templates())
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

    reordered_items = (
        task_workflow_template_three_task_template_items.get_task_templates()
    )
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


def test_workflow_template_update_view(
    valid_user_client,
    task_workflow_template,
):
    """Tests that a workflow template can be updated and that the corresponding
    confirmation view returns a HTTP 200 response."""

    update_url = reverse(
        "workflow:task-workflow-template-ui-update",
        kwargs={"pk": task_workflow_template.pk},
    )
    form_data = {
        "title": "Updated test title",
        "description": "Updated test title",
    }

    update_response = valid_user_client.post(update_url, form_data)
    assert update_response.status_code == 302

    task_workflow_template.refresh_from_db()
    assert task_workflow_template.title == form_data["title"]
    assert task_workflow_template.description == form_data["description"]

    confirmation_url = reverse(
        "workflow:task-workflow-template-ui-confirm-update",
        kwargs={"pk": task_workflow_template.pk},
    )
    assert update_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert task_workflow_template.title in soup.select("h1.govuk-panel__title")[0].text


def test_workflow_template_delete_view(
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    """Tests that a workflow template can be deleted (along with related
    TaskItemTemplate and TaskTemplate objects) and that the corresponding
    confirmation view returns a HTTP 200 response."""

    task_workflow_template_pk = task_workflow_template_single_task_template_item.pk
    task_template_pk = (
        task_workflow_template_single_task_template_item.get_task_templates().get().pk
    )

    delete_url = task_workflow_template_single_task_template_item.get_url("delete")
    delete_response = valid_user_client.post(delete_url)
    assert delete_response.status_code == 302

    assert not TaskWorkflowTemplate.objects.filter(
        pk=task_workflow_template_pk,
    ).exists()
    assert not TaskItemTemplate.objects.filter(
        queue_id=task_workflow_template_pk,
    ).exists()
    assert not TaskTemplate.objects.filter(pk=task_template_pk).exists()

    confirmation_url = reverse(
        "workflow:task-workflow-template-ui-confirm-delete",
        kwargs={"pk": task_workflow_template_pk},
    )
    assert delete_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert (
        f"Workflow template ID: {task_workflow_template_pk}"
        in soup.select(".govuk-panel__title")[0].text
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


def test_delete_task_template_view(
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    """Test the view for deleting TaskTemplates and the confirmation view that a
    successful deletion redirects to."""

    assert (
        task_workflow_template_single_task_template_item.get_task_templates().count()
        == 1
    )
    assert task_workflow_template_single_task_template_item.get_items().count() == 1

    task_template_pk = (
        task_workflow_template_single_task_template_item.get_task_templates().get().pk
    )
    task_item_template_pk = (
        task_workflow_template_single_task_template_item.get_items().get().pk
    )
    delete_url = reverse(
        "workflow:task-template-ui-delete",
        kwargs={
            "workflow_template_pk": task_workflow_template_single_task_template_item.pk,
            "pk": task_template_pk,
        },
    )

    delete_response = valid_user_client.post(delete_url)
    task_workflow_template_after = TaskWorkflowTemplate.objects.get(
        pk=task_workflow_template_single_task_template_item.pk,
    )

    confirmation_url = reverse(
        "workflow:task-template-ui-confirm-delete",
        kwargs={
            "workflow_template_pk": task_workflow_template_single_task_template_item.pk,
            "pk": task_template_pk,
        },
    )

    assert delete_response.status_code == 302
    assert delete_response.url == confirmation_url
    assert task_workflow_template_after.get_task_templates().count() == 0
    assert not TaskTemplate.objects.filter(pk=task_template_pk)
    assert not TaskItemTemplate.objects.filter(pk=task_item_template_pk)

    confirmation_response = valid_user_client.get(confirmation_url)

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")

    assert confirmation_response.status_code == 200
    assert (
        f"Task template ID: {task_template_pk}"
        in soup.select(".govuk-panel__title")[0].text
    )


def test_workflow_detail_view_displays_tasks(
    valid_user_client,
    task_workflow_single_task_item,
):
    workflow = task_workflow_single_task_item
    task = task_workflow_single_task_item.get_tasks().get()

    url = reverse(
        "workflow:task-workflow-ui-detail",
        kwargs={"pk": workflow.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    assert page.find("h1", text=f"Workflow: {workflow.title}")
    assert page.find("a", text=task.title)


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
def test_workflow_detail_view_reorder_items(
    action,
    item_position,
    expected_item_order,
    valid_user_client,
    task_workflow_three_task_items,
):
    """Tests that `TaskWorkflowDetailView` handles POST requests to promote or
    demote tasks."""

    def convert_to_index(position: int) -> int:
        """Converts a 1-based item position to a 0-based index for items array
        access."""
        return position - 1

    items = list(task_workflow_three_task_items.get_tasks())
    item_to_move = items[convert_to_index(item_position)]

    url = reverse(
        "workflow:task-workflow-ui-detail",
        kwargs={"pk": task_workflow_three_task_items.pk},
    )
    form_data = {
        action: item_to_move.id,
    }

    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    reordered_items = task_workflow_three_task_items.get_tasks()
    for i, reordered_item in enumerate(reordered_items):
        expected_position = convert_to_index(expected_item_order[i])
        expected_item = items[expected_position]
        assert reordered_item.id == expected_item.id


@pytest.mark.parametrize(
    "form_data",
    [
        {
            "title": "Test workflow 1",
            "description": "Workflow created without using template",
            "create_type": TaskWorkflowCreateForm.CreateType.WITHOUT_TEMPLATE,
        },
        {
            "title": "Test workflow 2",
            "description": "Workflow created using template",
            "create_type": TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE,
        },
    ],
    ids=(
        "without_template",
        "with_template",
    ),
)
def test_workflow_create_view(
    form_data,
    valid_user,
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    """Tests that a new workflow can be created (with or without workflow
    template) and that the corresponding confirmation view returns a HTTP 200
    response."""

    with_template = (
        form_data["create_type"] == TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE
    )

    if with_template:
        form_data["workflow_template"] = (
            task_workflow_template_single_task_template_item.pk
        )

    assert not TaskWorkflow.objects.exists()

    create_url = reverse("workflow:task-workflow-ui-create")
    create_response = valid_user_client.post(create_url, form_data)
    assert create_response.status_code == 302

    created_workflow = TaskWorkflow.objects.get(
        summary_task__title=form_data["title"],
        summary_task__description=form_data["description"],
        summary_task__creator=valid_user,
    )

    if with_template:
        assert (
            created_workflow.get_tasks().count()
            == task_workflow_template_single_task_template_item.get_task_templates().count()
        )
    else:
        assert created_workflow.get_tasks().count() == 0

    confirmation_url = reverse(
        "workflow:task-workflow-ui-confirm-create",
        kwargs={"pk": created_workflow.pk},
    )
    assert create_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert str(created_workflow) in soup.select("h1.govuk-panel__title")[0].text


def test_workflow_delete_view(
    valid_user_client,
    task_workflow_single_task_item,
):
    """Tests that a workflow can be deleted (along with related TaskItem and
    Task objects) and that the corresponding confirmation view returns a HTTP
    200 response."""

    workflow_pk = task_workflow_single_task_item.pk
    summary_task_pk = task_workflow_single_task_item.summary_task.pk
    task_pk = task_workflow_single_task_item.get_tasks().get().pk

    delete_url = task_workflow_single_task_item.get_url("delete")
    delete_response = valid_user_client.post(delete_url)
    assert delete_response.status_code == 302

    assert not TaskWorkflow.objects.filter(
        pk=workflow_pk,
    ).exists()
    assert not TaskItem.objects.filter(
        queue_id=workflow_pk,
    ).exists()
    assert not Task.objects.filter(pk__in=[summary_task_pk, task_pk]).exists()

    confirmation_url = reverse(
        "workflow:task-workflow-ui-confirm-delete",
        kwargs={"pk": workflow_pk},
    )
    assert delete_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert f"Workflow ID: {workflow_pk}" in soup.select(".govuk-panel__title")[0].text
