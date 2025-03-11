from datetime import date

import factory
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

import settings
from common.tests.factories import CommentFactory
from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskFactory
from common.util import format_date
from tasks.forms import TaskWorkflowCreateForm
from tasks.models import Comment
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskItem
from tasks.models import TaskItemTemplate
from tasks.models import TaskLog
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from tasks.tests.factories import TaskItemFactory
from tasks.tests.factories import TaskItemTemplateFactory
from tasks.tests.factories import TaskWorkflowFactory
from tasks.tests.factories import TaskWorkflowTemplateFactory

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
    workflow_template = task_item_template.workflow_template

    url = reverse(
        "workflow:task-workflow-template-ui-detail",
        kwargs={"pk": workflow_template.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    assert f"Ticket template {workflow_template.id}" in page.find("h1").text
    assert page.find("p", text=workflow_template.description)
    assert page.find("dd", text=workflow_template.creator.get_displayname())
    assert page.find("dd", text=format_date(workflow_template.created_at))

    template_rows = page.select(".govuk-table__body > .govuk-table__row")
    assert len(template_rows) == workflow_template.get_task_templates().count()


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
    assert (
        str(task_workflow_template.id) in soup.select("h1.govuk-panel__title")[0].text
    )


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
        workflow_template_id=task_workflow_template_pk,
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


def test_workflow_template_list_view(valid_user_client, valid_user):
    """Test that valid user receives a 200 on GET for TaskWorkflowList view and
    values display in table."""

    template_instance = TaskWorkflowTemplateFactory.create(creator=valid_user)
    response = valid_user_client.get(reverse("workflow:task-workflow-template-ui-list"))

    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")
    row_text = [td.text for td in soup.select("table tr:nth-child(1) > td")]

    assert str(template_instance.id) in row_text
    assert template_instance.title in row_text
    assert template_instance.description in row_text
    assert template_instance.creator.get_displayname() in row_text
    assert (
        f"{template_instance.updated_at.strftime(settings.DATETIME_FORMAT)}" in row_text
    )
    assert (
        f"{template_instance.created_at.strftime(settings.DATETIME_FORMAT)}" in row_text
    )


def test_workflow_detail_view_displays_tasks(
    valid_user_client,
    task_workflow_single_task_item,
):
    workflow = task_workflow_single_task_item
    workflow.policy_contact = "Policy contact"
    workflow.eif_date = date.today()
    workflow.save()
    workbasket = workflow.summary_task.workbasket

    url = reverse(
        "workflow:task-workflow-ui-detail",
        kwargs={"pk": workflow.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")

    assert f"Ticket {workflow.id}" in page.find("h1").text
    assert page.find("p", text=workflow.description)
    assert page.find("a", text=f"{workbasket.pk} - {workbasket.status}")
    assert page.find("dd", text=format_date(workflow.summary_task.created_at))
    assert page.find("dd", text=format_date(workflow.eif_date))
    assert page.find("dd", text=workflow.policy_contact)

    step_rows = page.select(".govuk-table__body > .govuk-table__row")
    assert len(step_rows) == workflow.get_tasks().count()


def test_workflow_create_view(
    valid_user,
    valid_user_client,
    task_workflow_template_single_task_template_item,
):
    """Tests that a new workflow can be created and that the corresponding
    confirmation view returns a HTTP 200 response."""

    assert not TaskWorkflow.objects.exists()

    form_data = {
        "ticket_name": "Test workflow 1",
        "description": "Workflow created",
        "work_type": task_workflow_template_single_task_template_item.pk,
        "assignment": TaskWorkflowCreateForm.AssignType.SELF,
    }

    create_url = reverse("workflow:task-workflow-ui-create")
    create_response = valid_user_client.post(create_url, form_data)
    assert create_response.status_code == 302

    created_workflow = TaskWorkflow.objects.get(
        summary_task__title=form_data["ticket_name"],
        summary_task__description=form_data["description"],
        summary_task__creator=valid_user,
    )

    assert created_workflow.summary_task.assignees.get().user == valid_user

    assert (
        created_workflow.get_tasks().count()
        == task_workflow_template_single_task_template_item.get_task_templates().count()
    )

    confirmation_url = reverse(
        "workflow:task-workflow-ui-detail",
        kwargs={"pk": created_workflow.pk},
    )
    assert create_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert str(created_workflow) in soup.select("h1")[0].text


def test_workflow_create_view_assigns_tasks(
    valid_user,
    valid_user_client,
    task_workflow_template_three_task_template_items,
):
    """Tests that when a new workflow is created with an assignee, all
    associated tasks are assigned to the user."""

    form_data = {
        "ticket_name": "Test workflow 1",
        "work_type": task_workflow_template_three_task_template_items.pk,
        "assignment": TaskWorkflowCreateForm.AssignType.OTHER_USER,
        "assignee": valid_user.pk,
    }

    url = reverse("workflow:task-workflow-ui-create")
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    workflow = TaskWorkflow.objects.get()
    assert workflow.summary_task.assignees.get().user == valid_user

    for task in workflow.get_tasks():
        assert task.assignees.get().user == valid_user


def test_workflow_update_view(
    valid_user,
    valid_user_client,
    task_workflow,
):
    """Tests that a workflow can be updated and that the corresponding
    confirmation view returns a HTTP 200 response."""

    form_data = {
        "title": "Updated title",
        "description": "Updated description",
        "assignee": valid_user.pk,
    }
    update_url = task_workflow.get_url("edit")

    update_response = valid_user_client.post(update_url, form_data)
    assert update_response.status_code == 302

    task_workflow.refresh_from_db()
    assert task_workflow.summary_task.title == form_data["title"]
    assert task_workflow.summary_task.description == form_data["description"]

    confirmation_url = reverse(
        "workflow:task-workflow-ui-confirm-update",
        kwargs={"pk": task_workflow.pk},
    )
    assert update_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert str(task_workflow.id) in soup.select("h1.govuk-panel__title")[0].text


def test_workflow_update_view_reassigns_tasks(
    valid_user,
    valid_user_client,
    assigned_task_workflow,
):
    """Tests that when a workflow is updated with a new assignee, all associated
    tasks are assigned to that user except for those marked as done."""

    TaskItemFactory.create_batch(
        2,
        workflow=assigned_task_workflow,
        task__progress_state=ProgressStateFactory.create(
            name=ProgressState.State.TO_DO,
        ),
    )

    done_task = TaskItemFactory.create(
        workflow=assigned_task_workflow,
        task__progress_state=ProgressStateFactory.create(name=ProgressState.State.DONE),
    ).task

    form_data = {
        "title": "Updated workflow",
        "assignee": valid_user.pk,
    }

    url = assigned_task_workflow.get_url("edit")
    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302

    assert (
        assigned_task_workflow.summary_task.assignees.assigned().get().user
        == valid_user
    )

    incomplete_tasks = assigned_task_workflow.get_tasks().incomplete()
    assert incomplete_tasks

    for task in incomplete_tasks:
        assert (
            task.assignees.get().user == valid_user
        ), "Task should be assigned to the new user"

    assert (
        not TaskAssignee.objects.filter(task=done_task, user=valid_user)
        .assigned()
        .exists()
    ), "Done task should not be assigned to the new user"


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
        workflow_id=workflow_pk,
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
    assert f"Ticket ID: {workflow_pk}" in soup.select(".govuk-panel__title")[0].text


def test_ticket_list_view(valid_user_client, task_workflow):
    """Test that the ticket list view returns 200 and renders correctly."""
    response = valid_user_client.get(reverse("workflow:task-workflow-ui-list"))

    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    table = page.select("table")[0]

    assert len(table.select("tbody tr")) == 1
    assert table.select("tr:nth-child(1) > td:nth-child(1) > a:nth-child(1)")[
        0
    ].text == str(task_workflow.pk)


def test_workflow_list_view_eif_date(
    valid_user_client,
):
    """Tests that workflows listed on `TaskWorkflowList` view can be sorted by
    entry into force (eif) date in ascending or descending order."""

    workflow_instance_1 = TaskWorkflowFactory.create(eif_date=date(2022, 1, 1))
    workflow_instance_2 = TaskWorkflowFactory.create(eif_date=date(2022, 2, 2))

    url = reverse(
        "workflow:task-workflow-ui-list",
    )
    response = valid_user_client.get(
        f"{url}?sort_by=taskworkflow__eif_date&ordered=asc",
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    ticket_ids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert ticket_ids == [workflow_instance_1.id, workflow_instance_2.id]

    response = valid_user_client.get(
        f"{url}?sort_by=taskworkflow__eif_date&ordered=desc",
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    ticket_ids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert ticket_ids == [workflow_instance_2.id, workflow_instance_1.id]


def test_task_and_workflow_list_view(valid_user_client, task, task_workflow):
    response = valid_user_client.get(reverse("workflow:task-and-workflow-ui-list"))

    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    table = page.select("table")[0]

    assert len(table.select("tbody tr")) == 2
    assert table.select("tr:nth-child(1) > td:nth-child(1) > a:nth-child(1)")[
        0
    ].text == str(task.pk)
    assert table.select("tr:nth-child(2) > td:nth-child(1) > a:nth-child(1)")[
        0
    ].text == str(task_workflow.summary_task.pk)


def test_create_workflow_task_view(valid_user_client, task_workflow):
    """Test the view for creating new Tasks for an existing workflow and the
    confirmation view that a successful creation redirects to."""

    assert task_workflow.get_tasks().count() == 0

    progress_state = ProgressStateFactory.create()

    create_url = reverse(
        "workflow:task-workflow-task-ui-create",
        kwargs={"task_workflow_pk": task_workflow.pk},
    )

    form_data = {
        "title": factory.Faker("sentence"),
        "description": factory.Faker("sentence"),
        "progress_state": progress_state.pk,
    }
    create_response = valid_user_client.post(create_url, form_data)

    assert task_workflow.get_tasks().count() == 1
    assert create_response.status_code == 302

    created_workflow_task = task_workflow.get_tasks().get()
    confirmation_url = reverse(
        "workflow:task-workflow-task-ui-confirm-create",
        kwargs={"pk": created_workflow_task.pk},
    )
    assert create_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(
        confirmation_response.content.decode(confirmation_response.charset),
        "html.parser",
    )
    assert created_workflow_task.title in soup.select("h1.govuk-panel__title")[0].text


def test_workflow_delete_view_deletes_related_tasks(
    valid_user_client,
    task_workflow_single_task_item,
):
    """Tests that a workflow can be deleted (along with related Task and
    TaskItem objects) and that the corresponding confirmation view returns a
    HTTP 200 response."""

    task_workflow_pk = task_workflow_single_task_item.pk
    task_pk = task_workflow_single_task_item.get_tasks().get().pk

    delete_url = task_workflow_single_task_item.get_url("delete")
    delete_response = valid_user_client.post(delete_url)
    assert delete_response.status_code == 302

    assert not TaskWorkflow.objects.filter(
        pk=task_workflow_pk,
    ).exists()
    assert not TaskItem.objects.filter(
        workflow_id=task_workflow_pk,
    ).exists()
    assert not Task.objects.filter(pk=task_pk).exists()

    confirmation_url = reverse(
        "workflow:task-workflow-ui-confirm-delete",
        kwargs={"pk": task_workflow_pk},
    )
    assert delete_response.url == confirmation_url

    confirmation_response = valid_user_client.get(confirmation_url)
    assert confirmation_response.status_code == 200

    soup = BeautifulSoup(str(confirmation_response.content), "html.parser")
    assert (
        f"Ticket ID: {task_workflow_pk}" in soup.select(".govuk-panel__title")[0].text
    )


def test_ticket_comments_render(valid_user_client):
    """Test that comments on a ticket appear and order from last to first."""
    ticket = TaskWorkflowFactory.create()
    CommentFactory.create(
        task=ticket.summary_task,
        content="This is an initial comment which should be on the second page.",
    )
    CommentFactory.create_batch(12, task=ticket.summary_task)
    url = reverse("workflow:task-workflow-ui-detail", kwargs={"pk": ticket.id})
    response = valid_user_client.get(url)

    page_1 = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    comments = page_1.find_all("article")
    assert len(comments) == 10

    url = (
        reverse("workflow:task-workflow-ui-detail", kwargs={"pk": ticket.id})
        + "?page=2"
    )
    response = valid_user_client.get(url)

    page_2 = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    comments = page_2.find_all("article")
    assert len(comments) == 3
    assert (
        "This is an initial comment which should be on the second page."
        in comments[2].text
    )


def test_ticket_view_add_comment(valid_user_client):
    """Tests that a comment can be added to a ticket from the ticket summary
    view."""
    ticket = TaskWorkflowFactory.create()
    content = "Test comment."
    form_data = {"content": content}
    url = reverse("workflow:task-workflow-ui-detail", kwargs={"pk": ticket.id})
    assert not Comment.objects.exists()

    response = valid_user_client.post(url, form_data)
    assert response.status_code == 302
    assert response.url == url
    assert content in Comment.objects.get(task=ticket.summary_task).content
