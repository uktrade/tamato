import pytest

from tasks.models import UserAssignment

pytestmark = pytest.mark.django_db


def test_user_assignment_unassign_user_classmethod(user_assignment):
    user = user_assignment.user
    task = user_assignment.task

    assert UserAssignment.unassign_user(user=user, task=task)
    # User has already been unassigned
    assert not UserAssignment.unassign_user(user=user, task=task)


def test_user_assignment_assigned_queryset(
    user_assignment,
):
    assert UserAssignment.objects.assigned().count() == 1

    user = user_assignment.user
    task = user_assignment.task
    UserAssignment.unassign_user(user=user, task=task)

    assert not UserAssignment.objects.assigned()


def test_user_assignment_unassigned_queryset(
    user_assignment,
):
    assert not UserAssignment.objects.unassigned()

    user = user_assignment.user
    task = user_assignment.task
    UserAssignment.unassign_user(user=user, task=task)

    assert UserAssignment.objects.unassigned().count() == 1


def test_user_assignment_workbasket_workers_queryset(
    workbasket_worker_assignment,
    workbasket_reviewer_assignment,
):
    workbasket_workers = UserAssignment.objects.workbasket_workers()

    assert workbasket_workers.count() == 1
    assert workbasket_worker_assignment in workbasket_workers


def test_user_assignment_workbasket_reviewers_queryset(
    workbasket_worker_assignment,
    workbasket_reviewer_assignment,
):
    workbasket_reviewers = UserAssignment.objects.workbasket_reviewers()

    assert workbasket_reviewers.count() == 1
    assert workbasket_reviewer_assignment in workbasket_reviewers
