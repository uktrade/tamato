import pytest

from common.tests.factories import CategoryFactory
from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskFactory
from tasks.models import TaskAssignee


@pytest.fixture()
def task():
    return TaskFactory.create()


@pytest.fixture()
def subtask():
    return SubTaskFactory.create()


@pytest.fixture()
def category():
    return CategoryFactory.create()


@pytest.fixture()
def progress_state():
    return ProgressStateFactory.create()


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
