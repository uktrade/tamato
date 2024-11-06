from common.tests.factories import ProgressStateFactory
from common.tests.factories import TaskFactory
from tasks import forms
from tasks.models import ProgressState


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
