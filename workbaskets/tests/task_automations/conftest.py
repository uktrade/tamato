import pytest

from tasks.tests.factories import TaskItemFactory
from workbaskets.models import CreateWorkBasketAutomation
from workbaskets.tests.task_automations.factories import (
    CreateWorkBasketAutomationFactory,
)


@pytest.fixture
def create_workbasket_automation_state_is_CAN_RUN() -> CreateWorkBasketAutomation:
    """Return a CreateWorkBasketAutomation instance that is associated with a
    workflow but no workbasket."""
    task_item = TaskItemFactory.create(
        workflow__summary_task__workbasket=None,
    )
    return CreateWorkBasketAutomationFactory.create(
        task=task_item.task,
    )


@pytest.fixture
def create_workbasket_automation_state_is_DONE() -> CreateWorkBasketAutomation:
    """Return a CreateWorkBasketAutomation instance that is associated with a
    workflow and a workbasket."""
    task_item = TaskItemFactory.create()
    return CreateWorkBasketAutomationFactory.create(
        task=task_item.task,
    )


@pytest.fixture
def create_workbasket_automation_state_is_ERRORED() -> CreateWorkBasketAutomation:
    """Return a CreateWorkBasketAutomation instance that is not associated with
    a workflow."""
    return CreateWorkBasketAutomationFactory.create()
