import factory
import pytest
from django.core.exceptions import ObjectDoesNotExist
from factory import SubFactory
from factory.django import DjangoModelFactory

from common.tests.factories import CategoryFactory
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflowTemplate

pytestmark = pytest.mark.django_db


class TaskWorkflowTemplateFactory(DjangoModelFactory):
    """Factory to create TaskWorkflowTemplate instances."""

    class Meta:
        model = TaskWorkflowTemplate


class TaskTemplateFactory(DjangoModelFactory):
    """Factory to create TaskTemplate instances."""

    title = factory.Faker("sentence")
    description = factory.Faker("sentence")
    category = factory.SubFactory(CategoryFactory)

    class Meta:
        model = TaskTemplate


class TaskItemTemplateFactory(DjangoModelFactory):
    """Factory to create TaskItemTemplate instances."""

    class Meta:
        model = TaskItemTemplate

    queue = SubFactory(TaskWorkflowTemplateFactory)
    task_template = SubFactory(TaskTemplateFactory)


@pytest.fixture()
def task_workflow_template() -> TaskWorkflowTemplate:
    """Return an empty TaskWorkflowTemplate instance (containing no items)."""
    return TaskWorkflowTemplateFactory.create()


@pytest.fixture()
def task_workflow_template_three_task_items(
    task_workflow_template,
) -> TaskWorkflowTemplate:
    """Return a TaskWorkflowTemplate instance containing three TaskItemTemplate
    and related TaskTemplates."""

    task_item_templates = []
    for _ in range(3):
        task_template = TaskTemplateFactory.create()
        task_item_template = TaskItemTemplateFactory.create(
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


def test_create_task_workflow_from_task_workflow_template(
    task_workflow_template_three_task_items,
):
    """Test creation of TaskWorkflow instances from TaskWorkflowTemplates using
    its `create_task_workflow()` method."""
    task_workflow = task_workflow_template_three_task_items.create_task_workflow()

    # Test that workflow values are valid.
    assert task_workflow.creator_template == task_workflow_template_three_task_items
    assert task_workflow.title == task_workflow_template_three_task_items.title
    assert (
        task_workflow.description == task_workflow_template_three_task_items.description
    )
    assert task_workflow.get_items().count() == 3

    # Validate that item positions are equivalent.
    zipped_items = zip(
        task_workflow_template_three_task_items.get_items(),
        task_workflow.get_items(),
    )
    for item_template, item in zipped_items:
        assert item_template.position == item.position

    # Validate that object values are equivalent.
    zipped_objs = zip(
        task_workflow_template_three_task_items.get_task_templates(),
        task_workflow.get_tasks(),
    )
    for task_template, task in zipped_objs:
        assert task_template.title == task.title
        assert task_template.description == task.description
        assert task_template.category == task.category


def test_delete_task_item_template():
    task_item_template = TaskItemTemplateFactory.create()
    task_item_template_id = task_item_template.id
    task_template_id = task_item_template.task_template.id

    assert TaskItemTemplate.objects.get(id=task_item_template_id)
    assert TaskTemplate.objects.get(id=task_template_id)

    task_item_template.delete()

    with pytest.raises(ObjectDoesNotExist):
        TaskItemTemplate.objects.get(id=task_item_template_id)
    assert TaskTemplate.objects.get(id=task_template_id)


def test_delete_task_template():
    task_item_template = TaskItemTemplateFactory.create()
    task_item_template_id = task_item_template.id
    task_template = task_item_template.task_template
    task_template_id = task_item_template.task_template.id

    assert TaskItemTemplate.objects.get(id=task_item_template_id)
    assert TaskTemplate.objects.get(id=task_template_id)

    task_template.delete()

    with pytest.raises(ObjectDoesNotExist):
        TaskItemTemplate.objects.get(id=task_item_template_id)
    with pytest.raises(ObjectDoesNotExist):
        assert TaskTemplate.objects.get(id=task_template_id)


def test_delete_task_workflow_template(task_workflow_template_three_task_items):
    task_item_template_ids = [
        item.id for item in task_workflow_template_three_task_items.get_items()
    ]
    task_template_ids = [
        task.id for task in task_workflow_template_three_task_items.get_task_templates()
    ]

    assert len(task_item_template_ids) == 3
    assert len(task_template_ids) == 3

    task_workflow_template_three_task_items.delete()

    assert not TaskItemTemplate.objects.filter(id__in=task_item_template_ids).exists()
    assert TaskTemplate.objects.filter(id__in=task_template_ids).count() == 3