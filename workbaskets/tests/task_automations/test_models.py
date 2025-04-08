import pytest

from tasks.models import StateChoices
from tasks.tests.factories import TaskItemFactory
from workbaskets.models import CreateWorkBasketAutomation
from workbaskets.tests.task_automations.factories import (
    CreateWorkBasketAutomationFactory,
)

pytestmark = pytest.mark.django_db


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


def test_create_workbasket_automation_get_state_can_run(
    create_workbasket_automation_state_is_CAN_RUN,
):
    assert (
        create_workbasket_automation_state_is_CAN_RUN.get_state()
        == StateChoices.CAN_RUN
    )
    assert (
        "create workbasket"
        in create_workbasket_automation_state_is_CAN_RUN.rendered_state().lower()
    )


def test_create_workbasket_automation_get_state_done(
    create_workbasket_automation_state_is_DONE,
):
    assert create_workbasket_automation_state_is_DONE.get_state() == StateChoices.DONE
    assert (
        "workbasket created"
        in create_workbasket_automation_state_is_DONE.rendered_state().lower()
    )


def test_create_workbasket_automation_get_state_errored(
    create_workbasket_automation_state_is_ERRORED,
):
    assert (
        create_workbasket_automation_state_is_ERRORED.get_state()
        == StateChoices.ERRORED
    )
    assert (
        "error"
        in create_workbasket_automation_state_is_ERRORED.rendered_state().lower()
    )


def test_create_workbasket_automation_run_automation(
    create_workbasket_automation_state_is_CAN_RUN,
    valid_user,
):
    assert (
        create_workbasket_automation_state_is_CAN_RUN.get_state()
        == StateChoices.CAN_RUN
    )
    create_workbasket_automation_state_is_CAN_RUN.run_automation(user=valid_user)
    assert (
        create_workbasket_automation_state_is_CAN_RUN.get_state() == StateChoices.DONE
    )
