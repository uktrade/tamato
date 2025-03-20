import pytest

from workbaskets.models import WorkBasketAssignment

pytestmark = pytest.mark.django_db


def test_user_assignment_unassign_user_classmethod(user_assignment):
    user = user_assignment.user
    workbasket = user_assignment.workbasket

    assert WorkBasketAssignment.unassign_user(user=user, workbasket=workbasket)
    # User has already been unassigned
    assert not WorkBasketAssignment.unassign_user(user=user, workbasket=workbasket)


def test_user_assignment_assigned_queryset(
    user_assignment,
):
    assert WorkBasketAssignment.objects.assigned().count() == 1

    user = user_assignment.user
    workbasket = user_assignment.workbasket
    WorkBasketAssignment.unassign_user(user=user, workbasket=workbasket)

    assert not WorkBasketAssignment.objects.assigned()


def test_user_assignment_unassigned_queryset(
    user_assignment,
):
    assert not WorkBasketAssignment.objects.unassigned()

    user = user_assignment.user
    workbasket = user_assignment.workbasket
    WorkBasketAssignment.unassign_user(user=user, workbasket=workbasket)

    assert WorkBasketAssignment.objects.unassigned().count() == 1


def test_user_assignment_workbasket_workers_queryset(
    workbasket_worker_assignment,
    workbasket_reviewer_assignment,
):
    workbasket_workers = WorkBasketAssignment.objects.workbasket_workers()

    assert workbasket_workers.count() == 1
    assert workbasket_worker_assignment in workbasket_workers


def test_user_assignment_workbasket_reviewers_queryset(
    workbasket_worker_assignment,
    workbasket_reviewer_assignment,
):
    workbasket_reviewers = WorkBasketAssignment.objects.workbasket_reviewers()

    assert workbasket_reviewers.count() == 1
    assert workbasket_reviewer_assignment in workbasket_reviewers
