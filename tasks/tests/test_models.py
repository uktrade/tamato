import pytest
from django.conf import settings
from django.db.utils import IntegrityError

from common.tests.factories import CategoryFactory
from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskFactory
from common.tests.factories import UserFactory
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskLog
from tasks.tests.factories import TaskWorkflowFactory

pytestmark = pytest.mark.django_db


def test_task_category_uniqueness():
    name = "Most favoured nation"
    CategoryFactory.create(name=name)
    with pytest.raises(IntegrityError):
        CategoryFactory.create(name=name)


def test_task_progress_state_uniqueness():
    name = "Blocked"
    ProgressState.objects.create(name=name)
    with pytest.raises(IntegrityError):
        ProgressState.objects.create(name=name)


def test_task_assignee_unassign_user_classmethod(task_assignee):
    user = task_assignee.user
    task = task_assignee.task

    assert TaskAssignee.unassign_user(user=user, task=task, instigator=user)
    # User has already been unassigned
    assert not TaskAssignee.unassign_user(user=user, task=task, instigator=user)


def test_task_assignee_assign_user_classmethod(task_assignee, valid_user):
    """Tests that `TaskAssignee.assign_user()` assigns the new user to the task
    and unassigns the existing assignee."""
    old_assignee = task_assignee.user
    task = task_assignee.task

    new_assignee = TaskAssignee.assign_user(
        user=valid_user,
        task=task,
        instigator=valid_user,
    )
    assert task.assignees.assigned().get() == new_assignee
    assert TaskAssignee.objects.unassigned().get(user=old_assignee, task=task)


def test_task_assignee_assigned_queryset(
    task_assignee,
):
    assert TaskAssignee.objects.assigned().count() == 1

    user = task_assignee.user
    task = task_assignee.task
    TaskAssignee.unassign_user(user=user, task=task, instigator=user)

    assert not TaskAssignee.objects.assigned()


def test_task_assignee_unassigned_queryset(
    task_assignee,
):
    assert not TaskAssignee.objects.unassigned()

    user = task_assignee.user
    task = task_assignee.task
    TaskAssignee.unassign_user(user=user, task=task, instigator=user)

    assert TaskAssignee.objects.unassigned().count() == 1


def test_task_incomplete_queryset():
    """Tests that `TaskQueryset.incomplete()` excludes `Task` instances that are
    marked as done."""
    task = TaskFactory.create(
        progress_state=ProgressStateFactory.create(
            name=ProgressState.State.IN_PROGRESS,
        ),
    )
    done_task = TaskFactory.create(
        progress_state=ProgressStateFactory.create(name=ProgressState.State.DONE),
    )
    incomplete_tasks = Task.objects.incomplete()

    assert Task.objects.count() == 2
    assert task in incomplete_tasks
    assert done_task not in incomplete_tasks


def test_non_workflow_queryset(task, task_workflow_single_task_item):
    """Test correct behaviour of TaskQueryset.non_workflow()."""

    SubTaskFactory(parent_task=task)
    SubTaskFactory(parent_task=task_workflow_single_task_item.get_tasks().get())

    non_workflow_tasks = Task.objects.non_workflow()

    # 1 x standalone task + 1 summary task + 1 x workflow task + 2 x subtasks
    assert Task.objects.count() == 5
    assert non_workflow_tasks.get() == task


def test_workflow_summary_queryset(task, task_workflow_single_task_item):
    """Test correct behaviour of TaskQueryset.workflow_summary()."""

    """Return a queryset of TaskWorkflow summary Task instances, i.e. those
    with a non-null related_name=taskworkflow."""

    SubTaskFactory(parent_task=task)
    SubTaskFactory(parent_task=task_workflow_single_task_item.get_tasks().get())

    workflow_summary_tasks = Task.objects.workflow_summary()

    # 1 x standalone task + 1 summary task + 1 x workflow task + 2 x subtasks
    assert Task.objects.count() == 5
    assert workflow_summary_tasks.get() == task_workflow_single_task_item.summary_task


def test_top_level_task_queryset(task, task_workflow_single_task_item):
    """Test correct behaviour of TaskQueryset.top_level()."""

    SubTaskFactory(parent_task=task)
    SubTaskFactory(parent_task=task_workflow_single_task_item.get_tasks().get())

    top_level_tasks = Task.objects.top_level()

    # 1 x standalone task + 1 summary task + 1 x workflow task + 2 x subtasks
    assert Task.objects.count() == 5
    assert top_level_tasks.count() == 2
    assert task_workflow_single_task_item.summary_task in top_level_tasks
    assert task in top_level_tasks
    assert task_workflow_single_task_item.get_tasks().get() not in top_level_tasks


def test_assigned_task_queryset(
    assigned_task_no_previous_assignee,
    assigned_task_with_previous_assignee,
    not_assigned_task_no_previous_assignee,
    not_assigned_task_with_previous_assignee,
):
    assigned_tasks = [
        assigned_task_no_previous_assignee,
        assigned_task_with_previous_assignee,
    ]
    assert Task.objects.count() == 4
    assert Task.objects.assigned().count() == 2
    assert set(assigned_tasks) == set(Task.objects.assigned())


def test_not_assigned_task_queryset(
    assigned_task_no_previous_assignee,
    assigned_task_with_previous_assignee,
    not_assigned_task_no_previous_assignee,
    not_assigned_task_with_previous_assignee,
):
    not_assigned_tasks = [
        not_assigned_task_no_previous_assignee,
        not_assigned_task_with_previous_assignee,
    ]
    assert Task.objects.count() == 4
    assert Task.objects.not_assigned().count() == 2
    assert set(not_assigned_tasks) == set(Task.objects.not_assigned())


def test_actively_assigned_to_task_queryset(
    assigned_task_no_previous_assignee,
    assigned_task_with_previous_assignee,
    not_assigned_task_no_previous_assignee,
    not_assigned_task_with_previous_assignee,
):
    user_1 = assigned_task_no_previous_assignee.assignees.get().user
    user_1_actively_assigned = Task.objects.actively_assigned_to(user=user_1)
    assert set([assigned_task_no_previous_assignee]) == set(user_1_actively_assigned)

    user_2 = (
        assigned_task_with_previous_assignee.assignees.filter(
            unassigned_at__isnull=True,
        )
        .get()
        .user
    )
    user_2_actively_assigned = Task.objects.actively_assigned_to(user=user_2)
    assert set([assigned_task_with_previous_assignee]) == set(user_2_actively_assigned)


def test_create_task_log_task_assigned():
    task = TaskFactory.create()
    instigator = task.creator
    action = TaskLog.AuditActionType.TASK_ASSIGNED
    task_log = TaskLog.objects.create(
        task=task,
        action=action,
        instigator=instigator,
        assignee=instigator,
    )

    assert task_log.task == task
    assert task_log.instigator == instigator
    assert task_log.action == action
    assert task_log.description == f"{instigator} assigned {instigator}"


def test_create_task_log_task_unassigned():
    task = TaskFactory.create()
    instigator = task.creator
    action = TaskLog.AuditActionType.TASK_UNASSIGNED
    task_log = TaskLog.objects.create(
        task=task,
        action=action,
        instigator=instigator,
        assignee=instigator,
    )

    assert task_log.task == task
    assert task_log.instigator == instigator
    assert task_log.action == action
    assert task_log.description == f"{instigator} unassigned {instigator}"


def test_create_task_log_progress_state_updated():
    task = TaskFactory.create()
    instigator = task.creator
    action = TaskLog.AuditActionType.PROGRESS_STATE_UPDATED
    progress_state = ProgressStateFactory.create()
    task_log = TaskLog.objects.create(
        task=task,
        action=action,
        instigator=instigator,
        progress_state=progress_state,
    )

    assert task_log.task == task
    assert task_log.instigator == instigator
    assert task_log.action == action
    assert (
        task_log.description == f"{instigator} changed the status to {progress_state}"
    )


def test_create_task_log_invalid_audit_action():
    task = TaskFactory.create()
    instigator = task.creator
    action = "INVALID_AUDIT_ACTION"

    with pytest.raises(ValueError) as error:
        TaskLog.objects.create(task=task, action=action, instigator=instigator)
    assert f"The action '{action}' is an invalid TaskLog.AuditActionType value." in str(
        error,
    )


def test_create_task_log_missing_kwargs():
    task = TaskFactory.create()
    instigator = task.creator
    action = TaskLog.AuditActionType.TASK_ASSIGNED

    with pytest.raises(ValueError) as error:
        TaskLog.objects.create(task=task, action=action, instigator=instigator)
    assert f"Missing 'assignee' in kwargs for action '{action}'." in str(
        error,
    )


@pytest.mark.parametrize(
    ("task_factory"),
    [TaskFactory, SubTaskFactory],
    ids=("task test", "subtask test"),
)
def test_task_is_subtask_property(task_factory):
    task = task_factory.create()

    assert bool(task.parent_task) == task.is_subtask


@pytest.mark.parametrize(
    ("create_task_fn"),
    (
        lambda: TaskFactory.create(),
        lambda: TaskWorkflowFactory.create().summary_task,
    ),
    ids=("standalone task test", "summary task test"),
)
def test_task_is_summary_task_property(create_task_fn):
    task = create_task_fn()
    assert bool(hasattr(task, "taskworkflow")) == task.is_summary_task


def test_prefixed_id(task_workflow):
    expected_prefixed_id = f"{settings.TICKET_PREFIX}{task_workflow.id}"
    assert task_workflow.prefixed_id == expected_prefixed_id


def test_with_latest_assignees_task_queryset(
    not_assigned_task_no_previous_assignee,
    assigned_task_no_previous_assignee,
):

    workflow_1 = not_assigned_task_no_previous_assignee
    workflow_2 = assigned_task_no_previous_assignee

    new_assignee_1 = UserFactory.create(first_name="Aaa")
    new_assignee_2 = UserFactory.create(first_name="Bbb")

    qs = Task.objects.with_latest_assignees()
    assert qs.assigned().count() == 1

    TaskAssignee.assign_user(
        user=new_assignee_1,
        task=workflow_1,
        instigator=new_assignee_1,
    )

    TaskAssignee.assign_user(
        user=new_assignee_2,
        task=workflow_2,
        instigator=new_assignee_2,
    )

    assert qs.assigned().count() == 2
    assert qs.first().assigned_user == new_assignee_1.first_name
    assert qs.last().assigned_user == new_assignee_2.first_name
