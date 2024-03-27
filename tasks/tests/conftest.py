import pytest

from common.tests.factories import TaskFactory
from common.tests.factories import UserAssignmentFactory
from tasks.models import UserAssignment


@pytest.fixture()
def task():
    return TaskFactory.create()


@pytest.fixture()
def user_assignment():
    return UserAssignmentFactory.create()


@pytest.fixture()
def workbasket_worker_assignment():
    return UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_WORKER,
    )


@pytest.fixture()
def workbasket_reviewer_assignment():
    return UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_REVIEWER,
    )
