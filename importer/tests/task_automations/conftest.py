import pytest

from common.tests.factories import ImportBatchFactory
from importer.models import ImportBatchStatus
from importer.models import ImportGoodsAutomation
from importer.tests.task_automations.factories import ImportGoodsAutomationFactory
from tasks.tests.factories import TaskItemFactory


@pytest.fixture
def import_goods_automation_state_is_CAN_RUN() -> ImportGoodsAutomation:
    """Return an ImportGoodsAutomation instance that has no ImportBatch instance
    and is associated with a workflow that has no workbasket."""
    task_item = TaskItemFactory.create(
        workflow__summary_task__workbasket=None,
    )
    return ImportGoodsAutomationFactory.create(
        task=task_item.task,
        import_batch=None,
    )


@pytest.fixture
def import_goods_automation_state_is_RUNNING() -> ImportGoodsAutomation:
    """Return an ImportGoodsAutomation instance that has an ImportBatch instance
    with status set to IMPORTING and a workflow with an associated
    workbasket."""

    import_goods = ImportBatchFactory()
    task_item = TaskItemFactory.create(
        workflow__summary_task__workbasket=import_goods.workbasket,
    )
    return ImportGoodsAutomationFactory.create(
        task=task_item.task,
        import_batch=None,
    )


@pytest.fixture
def import_goods_automation_state_is_DONE() -> ImportGoodsAutomation:
    """Return an ImportGoodsAutomation instance that has an ImportBatch instance
    with status set to SUCCEEDED and a workflow with an associated
    workbasket."""

    import_goods = ImportBatchFactory(
        status=ImportBatchStatus.SUCCEEDED,
    )
    task_item = TaskItemFactory.create(
        workflow__summary_task__workbasket=import_goods.workbasket,
    )
    return ImportGoodsAutomationFactory.create(
        task=task_item.task,
        import_batch=None,
    )


@pytest.fixture
def import_goods_automation_state_is_ERRORED() -> ImportGoodsAutomation:
    """Return an ImportGoodsAutomation instance that has an ImportBatch instance
    with status set to FAILED and a workflow with an associated workbasket."""

    import_goods = ImportBatchFactory(
        status=ImportBatchStatus.FAILED,
    )
    task_item = TaskItemFactory.create(
        workflow__summary_task__workbasket=import_goods.workbasket,
    )
    return ImportGoodsAutomationFactory.create(
        task=task_item.task,
        import_batch=None,
    )
