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


@pytest.mark.parametrize(
    "form_data",
    [
        {
            "title": "Test workflow 1",
            "description": "Workflow created without using template",
            "create_type": forms.TaskWorkflowCreateForm.CreateType.WITHOUT_TEMPLATE,
        },
        {
            "title": "Test workflow 2",
            "description": "Workflow created using template",
            "create_type": forms.TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE,
            "workflow_template": "",
        },
    ],
    ids=(
        "without_template",
        "with_template",
    ),
)
def test_workflow_create_form_valid_data(form_data, task_workflow_template):
    """Tests that `TaskWorkflowCreateForm` returns expected cleaned_data given
    valid form data."""

    if "workflow_template" in form_data:
        form_data["workflow_template"] = task_workflow_template

    form = forms.TaskWorkflowCreateForm(form_data)
    assert form.is_valid()
    assert form.cleaned_data == form_data


@pytest.mark.parametrize(
    ("form_data", "field", "error_message"),
    [
        ({"title": ""}, "title", "Enter a title for the workflow"),
        ({"description": ""}, "description", "Enter a description for the workflow"),
        (
            {"create_type": ""},
            "create_type",
            "Select if you want to use a workflow template",
        ),
        (
            {
                "create_type": forms.TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE,
                "workflow_template": "",
            },
            "create_type",
            "Select a workflow template",
        ),
        (
            {
                "create_type": forms.TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE,
                "workflow_template": "invalidchoice",
            },
            "create_type",
            "Select a valid choice. That choice is not one of the available choices.",
        ),
    ],
    ids=(
        "missing_title",
        "missing_description",
        "missing_create_type",
        "missing_workflow_template",
        "invalid_workflow_template",
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
