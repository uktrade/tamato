import pytest

from common.tests.factories import CategoryFactory
from common.tests.factories import ProgressStateFactory
from common.tests.factories import SubTaskFactory
from common.tests.factories import TaskAssigneeFactory
from common.tests.factories import TaskFactory
from tasks.models import TaskAssignee
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
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
def task_workflow_template_three_task_items(
    task_workflow_template,
) -> TaskWorkflowTemplate:
    """Return a TaskWorkflowTemplate instance containing three TaskItemTemplate
    and related TaskTemplates."""

    task_item_templates = []
    for _ in range(3):
        task_template = factories.TaskTemplateFactory.create()
        task_item_template = factories.TaskItemTemplateFactory.create(
            queue=task_workflow_template,
            task_template=task_template,
        )
        task_item_templates.append(task_item_template)

    assert task_workflow_template.get_items().count() == 3
    assert (
        TaskItemTemplate.objects.filter(
            queue=task_workflow_template,
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
