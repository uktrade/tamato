import random

import pytest

from common.tests import factories
from common.tests.factories import WorkBasketAssignmentFactory
from tasks.tests.factories import TaskWorkflowFactory
from workbaskets.models import AssignmentType
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus


@pytest.fixture(params=WorkflowStatus.values)
def workbasket(request):
    """WorkBaskets with all possible statuses as a parametrized fixture."""
    yield factories.WorkBasketFactory.create(status=request.param)


@pytest.fixture(
    params=WorkBasket.status.field.get_all_transitions(WorkBasket),
    ids=lambda t: t.name,
)
def transition(request):
    """All status transitions as a parametrized fixture."""
    return request.param


@pytest.fixture()
def workbasket_assignment():
    """Create and return a WorkBasketAssignment instance with randomly allocated
    AssignmentTYpe."""
    return WorkBasketAssignmentFactory.create(
        assignment_type=random.choice(AssignmentType.choices),
    )


@pytest.fixture()
def workbasket_worker_assignment():
    return WorkBasketAssignmentFactory.create(
        assignment_type=AssignmentType.WORKBASKET_WORKER,
    )


@pytest.fixture()
def workbasket_reviewer_assignment():
    return WorkBasketAssignmentFactory.create(
        assignment_type=AssignmentType.WORKBASKET_REVIEWER,
    )


@pytest.fixture()
def workbasket_with_task_workflow(user_workbasket):
    """Returns a workbasket with an associated task workflow."""
    workflow = TaskWorkflowFactory.create()
    workflow.summary_task.title = "TC1: Test ticket"
    workflow.summary_task.save()

    workbasket = user_workbasket
    workflow.summary_task.workbasket = workbasket
    workflow.summary_task.save()

    return workbasket
