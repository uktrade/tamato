import pytest

from common.tests.factories import ProgressStateFactory
from common.tests.factories import TaskFactory
from tasks import forms
from tasks.models import ProgressState

pytestmark = pytest.mark.django_db


def test_create_subtask_assigns_correct_parent_task(valid_user):
    """Tests that SubtaskCreateForm assigns the correct parent on form.save."""
    parent_task_instance = TaskFactory.create()
    progress_state = ProgressStateFactory.create(
        name=ProgressState.State.IN_PROGRESS,
    )

    subtask_form_data = {
        "progress_state": progress_state.pk,
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
        ({"ticket_name": ""}, "ticket_name", "Enter a title for the workflow"),
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
    ],
    ids=(
        "missing_title",
        "missing_work_type",
        "invalid_work_type",
    ),
)
def test_workflow_create_form_invalid_data(form_data, field, error_message):
    """Tests that `TaskWorkflowCreateForm` raises expected form errors given
    invalid form data."""

    form = forms.TaskWorkflowCreateForm(form_data)
    assert not form.is_valid()
    assert error_message in form.errors[field]


def test_workflow_update_form_save(task_workflow):
    """Tests that the details of `TaskWorkflow.summary_task` are updated when
    calling form.save()."""
    form_data = {
        "title": "Updated workflow title",
        "description": "Updated workflow description",
    }

    form = forms.TaskWorkflowUpdateForm(data=form_data, instance=task_workflow)
    assert form.is_valid()

    workflow = form.save()
    assert workflow.summary_task.title == form_data["title"]
    assert workflow.summary_task.description == form_data["description"]
