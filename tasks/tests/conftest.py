import pytest

from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskFactory
from common.tests.factories import UserFactory
from tasks.models import ProgressState
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
def done_task():
    return TaskFactory.create(progress_state=ProgressState.DONE)


@pytest.fixture()
def subtask():
    return SubTaskFactory.create()


@pytest.fixture()
def task_assignee():
    return TaskAssigneeFactory.create()


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
        workflow_template=task_workflow_template,
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
            workflow_template=task_workflow_template,
            task_template=task_template,
        )
        task_item_templates.append(task_item_template)

    assert task_workflow_template.get_items().count() == 3
    assert (
        TaskItemTemplate.objects.filter(
            workflow_template=task_workflow_template,
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
def assigned_task_workflow(valid_user) -> TaskWorkflow:
    """Return an empty TaskWorkflow instance whose `summary_task` has an
    assignee."""
    workflow = factories.TaskWorkflowFactory.create()
    TaskAssigneeFactory.create(task=workflow.summary_task, user=valid_user)
    return workflow


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
        workflow=task_workflow,
    )

    assert task_workflow.get_items().count() == expected_count
    assert TaskItem.objects.filter(workflow=task_workflow).count() == expected_count
    assert (
        Task.objects.filter(taskitem__in=[item.pk for item in task_items]).count()
        == expected_count
    )

    return task_workflow


@pytest.fixture
def assigned_task_no_previous_assignee() -> Task:
    task = TaskFactory.create()
    user = UserFactory.create()
    TaskAssignee.assign_user(user=user, task=task, instigator=user)
    return task


@pytest.fixture
def assigned_task_with_previous_assignee() -> Task:
    task = TaskFactory.create()
    user_1 = UserFactory.create()
    TaskAssignee.assign_user(user=user_1, task=task, instigator=user_1)
    TaskAssignee.unassign_user(user=user_1, task=task, instigator=user_1)
    user_2 = UserFactory.create()
    TaskAssignee.assign_user(user=user_2, task=task, instigator=user_2)
    return task


@pytest.fixture
def not_assigned_task_no_previous_assignee() -> Task:
    return TaskFactory.create()


@pytest.fixture
def not_assigned_task_with_previous_assignee() -> Task:
    task = TaskFactory.create()
    user = UserFactory.create()
    TaskAssignee.assign_user(user=user, task=task, instigator=user)
    TaskAssignee.unassign_user(user=user, task=task, instigator=user)
    return task
