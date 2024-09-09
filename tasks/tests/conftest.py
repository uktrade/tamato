import pytest

from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskCategoryFactory
from common.tests.factories import TaskFactory
from common.tests.factories import TaskProgressStateFactory
from tasks.models import TaskAssignee


@pytest.fixture()
def task():
    return TaskFactory.create()


@pytest.fixture()
def subtask():
    return SubTaskFactory.create()


@pytest.fixture()
def task_category():
    return TaskCategoryFactory.create()


@pytest.fixture()
def task_progress_state():
    return TaskProgressStateFactory.create()


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
