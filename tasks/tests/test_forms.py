from datetime import date

import pytest

from common.tests.factories import CommentFactory
from common.tests.factories import TaskFactory
from tasks import forms
from tasks.models import ProgressState
from tasks.models import TaskAssignee

pytestmark = pytest.mark.django_db


def test_task_assign_user_form_assigns_user(task, valid_user):
    """Tests that `AssignUserForm.assign_user()` creates a `TaskAssignee`
    instance associated to the task."""
    data = {
        "user": valid_user.pk,
    }
    form = forms.AssignUserForm(
        data=data,
        task=task,
    )
    assert form.is_valid()
    assert form.assign_user(task=task, user_instigator=valid_user)


def test_task_assign_user_form_prevents_multiple_assignees(task_assignee, valid_user):
    """Tests that `AssignUserForm` raises a ValidationError if the task already
    has an assignee."""
    data = {
        "user": valid_user.pk,
    }
    form = forms.AssignUserForm(
        data=data,
        task=task_assignee.task,
    )
    assert not form.is_valid()
    assert (
        "The selected user cannot be assigned because the step already has an assignee."
        in form.errors["user"]
    )


def test_task_unassign_user_form_unassigns_user(task_assignee, valid_user):
    """Tests that `UnassignUserForm.unassign_user()` unassigns the given user
    from the task."""
    task = task_assignee.task

    data = {
        "assignee": task_assignee.pk,
    }

    form = forms.UnassignUserForm(
        data=data,
        task=task,
    )
    assert form.is_valid()

    form.unassign_user(user_instigator=valid_user)
    assert TaskAssignee.objects.unassigned().get(task=task, user=task_assignee.user)


def test_task_unassign_user_form_prevents_done_unassignment(done_task):
    """Tests that `UnassignUserForm` raises a ValidationError if the task has a
    status of Done."""
    data = {
        "assignee": "",
    }
    form = forms.UnassignUserForm(
        data=data,
        task=done_task,
    )
    assert not form.is_valid()
    assert (
        "The selected user cannot be unassigned because the step has a status of Done."
        in form.errors["assignee"]
    )


def test_create_subtask_assigns_correct_parent_task(valid_user):
    """Tests that SubtaskCreateForm assigns the correct parent on form.save."""
    parent_task_instance = TaskFactory.create()

    subtask_form_data = {
        "title": "subtask test title",
        "description": "subtask test description",
    }
    form = forms.SubTaskCreateForm(data=subtask_form_data)
    new_subtask = form.save(parent_task_instance, user=valid_user)

    assert new_subtask.parent_task.pk == parent_task_instance.pk


def test_workflow_create_form_valid_data(task_workflow_template):
    """Tests that `TaskWorkflowCreateForm` returns expected cleaned_data given
    valid form data."""

    form_data = {
        "ticket_name": "Test ticket 1",
        "description": "Ticket created with all fields",
        "work_type": task_workflow_template,
        "assignment": forms.TaskWorkflowCreateForm.AssignType.SELF,
        "entry_into_force_date_0": 12,
        "entry_into_force_date_1": 12,
        "entry_into_force_date_2": 2026,
        "policy_contact": "Fake Contact Name",
    }

    form = forms.TaskWorkflowCreateForm(form_data)
    assert form.is_valid()


@pytest.mark.parametrize(
    ("form_data", "field", "error_message"),
    [
        ({"ticket_name": ""}, "ticket_name", "Enter a title for the ticket"),
        (
            {"work_type": ""},
            "work_type",
            "Choose a work type",
        ),
        (
            {
                "workflow_template": "invalidchoice",
            },
            "work_type",
            "Choose a work type",
        ),
        (
            {"assignment": ""},
            "assignment",
            "Select an assignee option",
        ),
        (
            {
                "assignment": forms.TaskWorkflowCreateForm.AssignType.OTHER_USER.value,
                "assignee": "",
            },
            "assignment",
            "Select an assignee",
        ),
    ],
    ids=(
        "missing_title",
        "missing_work_type",
        "invalid_work_type",
        "missing_assignment",
        "invalid_assignee",
    ),
)
def test_workflow_create_form_invalid_data(form_data, field, error_message):
    """Tests that `TaskWorkflowCreateForm` raises expected form errors given
    invalid form data."""

    form = forms.TaskWorkflowCreateForm(form_data)
    assert not form.is_valid()
    assert error_message in form.errors[field]


def test_workflow_update_form_save(assigned_task_workflow):
    """Tests that the details of `TaskWorkflow.summary_task` are updated when
    calling form.save()."""
    form_data = {
        "title": "Updated title",
        "description": "Updated description",
        "assignee": assigned_task_workflow.summary_task.assignees.get().user,
        "eif_date_0": date.today().day,
        "eif_date_1": date.today().month,
        "eif_date_2": date.today().year,
        "policy_contact": "Policy contact",
    }

    form = forms.TaskWorkflowUpdateForm(data=form_data, instance=assigned_task_workflow)
    assert form.is_valid()

    workflow = form.save()
    assert workflow.eif_date == date.today()
    assert workflow.policy_contact == form_data["policy_contact"]
    assert workflow.summary_task.title == form_data["title"]
    assert workflow.summary_task.description == form_data["description"]


def test_add_comment_form_valid(task_workflow):
    form_data = {"content": "Test comment."}
    form = forms.TicketCommentCreateForm(data=form_data, instance=task_workflow)
    assert form.is_valid()

    empty_form_data = {"content": ""}
    form = forms.TicketCommentCreateForm(data=empty_form_data, instance=task_workflow)
    assert not form.is_valid()
    assert "Enter your comment" in form.errors["content"]


def test_edit_comment_form_valid(task_workflow):
    comment = CommentFactory.create(
        task=task_workflow.summary_task,
        content="Test comment",
    )
    form_data = {"content": "Update comment"}
    form = forms.TicketCommentUpdateForm(
        data=form_data,
        instance=comment,
        ticket_pk=task_workflow.pk,
    )
    assert form.is_valid()
    form.save()
    comment.refresh_from_db()
    assert "Update comment" in comment.content

    empty_form_data = {"content": ""}
    form = forms.TicketCommentUpdateForm(
        data=empty_form_data,
        instance=comment,
        ticket_pk=task_workflow.pk,
    )
    assert not form.is_valid()
    assert "Enter your comment" in form.errors["content"]


def test_task_update_form():
    """Tests that `TaskUpdateForm's update_status function` correctly updates
    `Task.progress_state`"""

    task_instance = TaskFactory.create(
        progress_state__name=ProgressState.TO_DO,
    )

    new_progress_state = ProgressState.IN_PROGRESS

    form_data = {
        "progress_state": new_progress_state,
    }

    form = forms.TaskUpdateForm(data=form_data)
    assert form.is_valid()

    form.update_progress_state(task=task_instance)
    assert task_instance.progress_state == new_progress_state
