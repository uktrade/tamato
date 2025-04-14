import pytest

from common.tests import factories
from common.tests.factories import WorkBasketAssignmentFactory
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
def user_assignment():
    return WorkBasketAssignmentFactory.create()


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
