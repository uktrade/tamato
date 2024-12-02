import pytest

from common.tests.factories import CategoryFactory
from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskFactory
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskItem
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from tasks.tests import factories


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


@pytest.fixture()
def task_workflow_template() -> TaskWorkflowTemplate:
    """Return an empty TaskWorkflowTemplate instance (containing no items)."""
    return factories.TaskWorkflowTemplateFactory.create()


@pytest.fixture()
def task_workflow_template_single_task_template_item(
    task_workflow_template,
) -> TaskWorkflowTemplate:
    """Return a TaskWorkflowTemplate instance containing a single
    TaskTemplateItem instance."""

    task_template = factories.TaskTemplateFactory.create()
    factories.TaskItemTemplateFactory.create(
        workflow=task_workflow_template,
        task_template=task_template,
    )

    assert task_workflow_template.get_items().count() == 1

    return task_workflow_template


@pytest.fixture()
def task_workflow_template_three_task_template_items(
    task_workflow_template,
) -> TaskWorkflowTemplate:
    """Return a TaskWorkflowTemplate instance containing three TaskItemTemplate
    and related TaskTemplates."""

    task_item_templates = []
    for _ in range(3):
        task_template = factories.TaskTemplateFactory.create()
        task_item_template = factories.TaskItemTemplateFactory.create(
            workflow=task_workflow_template,
            task_template=task_template,
        )
        task_item_templates.append(task_item_template)

    assert task_workflow_template.get_items().count() == 3
    assert (
        TaskItemTemplate.objects.filter(
            workflow=task_workflow_template,
        ).count()
        == 3
    )
    assert (
        TaskTemplate.objects.filter(
            taskitemtemplate__in=task_item_templates,
        ).count()
        == 3
    )

    return task_workflow_template


@pytest.fixture()
def task_workflow() -> TaskWorkflow:
    """Return an empty TaskWorkflow instance (containing no items)."""
    return factories.TaskWorkflowFactory.create()


@pytest.fixture()
def task_workflow_single_task_item(task_workflow) -> TaskWorkflow:
    """Return a TaskWorkflow instance containing a single TaskItem instance with
    associated Task instance."""

    task_item = factories.TaskItemFactory.create(
        workflow=task_workflow,
    )

    assert task_workflow.get_items().count() == 1
    assert task_workflow.get_items().get() == task_item

    return task_workflow


@pytest.fixture()
def task_workflow_three_task_items(
    task_workflow,
) -> TaskWorkflow:
    """Return a TaskWorkflow instance containing three TaskItems and related
    Tasks."""

    expected_count = 3

    task_items = factories.TaskItemFactory.create_batch(
        expected_count,
        queue=task_workflow,
    )

    assert task_workflow.get_items().count() == expected_count
    assert TaskItem.objects.filter(queue=task_workflow).count() == expected_count
    assert (
        Task.objects.filter(taskitem__in=[item.pk for item in task_items]).count()
        == expected_count
    )

    return task_workflow
