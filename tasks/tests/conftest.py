import pytest

from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskFactory
from tasks.models import TaskAssignee


@pytest.fixture()
def task():
    return TaskFactory.create()


@pytest.fixture()
def task_assignee():
    return TaskAssigneeFactory.create()


@pytest.fixture()
def workbasket_worker_assignee():
    return TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
    )


@pytest.fixture()
def workbasket_reviewer_assignee():
    return TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
    )
