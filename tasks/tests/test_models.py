import pytest
from django.db.utils import IntegrityError

from common.tests.factories import TaskCategoryFactory
from common.tests.factories import TaskFactory
from common.tests.factories import TaskProgressStateFactory
from tasks.models import TaskAssignee
from tasks.models import TaskLog

pytestmark = pytest.mark.django_db


def test_task_category_uniqueness():
    name = "Most favoured nation"
    TaskCategoryFactory.create(name=name)
    with pytest.raises(IntegrityError):
        TaskCategoryFactory.create(name=name)


def test_task_progress_state_uniqueness():
    name = "Blocked"
    TaskProgressStateFactory.create(name=name)
    with pytest.raises(IntegrityError):
        TaskProgressStateFactory.create(name=name)


def test_task_assignee_unassign_user_classmethod(task_assignee):
    user = task_assignee.user
    task = task_assignee.task

    assert TaskAssignee.unassign_user(user=user, task=task)
    # User has already been unassigned
    assert not TaskAssignee.unassign_user(user=user, task=task)


def test_task_assignee_assigned_queryset(
    task_assignee,
):
    assert TaskAssignee.objects.assigned().count() == 1

    user = task_assignee.user
    task = task_assignee.task
    TaskAssignee.unassign_user(user=user, task=task)

    assert not TaskAssignee.objects.assigned()


def test_task_assignee_unassigned_queryset(
    task_assignee,
):
    assert not TaskAssignee.objects.unassigned()

    user = task_assignee.user
    task = task_assignee.task
    TaskAssignee.unassign_user(user=user, task=task)

    assert TaskAssignee.objects.unassigned().count() == 1


def test_task_assignee_workbasket_workers_queryset(
    workbasket_worker_assignee,
    workbasket_reviewer_assignee,
):
    workbasket_workers = TaskAssignee.objects.workbasket_workers()

    assert workbasket_workers.count() == 1
    assert workbasket_worker_assignee in workbasket_workers


def test_task_assignee_workbasket_reviewers_queryset(
    workbasket_worker_assignee,
    workbasket_reviewer_assignee,
):
    workbasket_reviewers = TaskAssignee.objects.workbasket_reviewers()

    assert workbasket_reviewers.count() == 1
    assert workbasket_reviewer_assignee in workbasket_reviewers


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
    progress_state = TaskProgressStateFactory.create()
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
