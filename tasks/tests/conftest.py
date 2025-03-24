import pytest

from common.tests.factories import WorkBasketAssignmentFactory
from workbaskets.models import AssignmentType


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
