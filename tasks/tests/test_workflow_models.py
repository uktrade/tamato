import datetime

import pytest
from django.core.exceptions import ObjectDoesNotExist

from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.tests import factories

pytestmark = pytest.mark.django_db


def test_create_task_workflow_from_task_workflow_template(
    valid_user,
    task_workflow_template_three_task_template_items,
):
    """Test creation of TaskWorkflow instances from TaskWorkflowTemplates using
    its `create_task_workflow()` method."""

    ticket_name = "Workflow title"
    description = "Workflow description"
    creator = valid_user
    eif_date = datetime.date(2026, 12, 12)
    policy_contact = "Policy Contact"

    task_workflow = (
        task_workflow_template_three_task_template_items.create_task_workflow(
            title=ticket_name,
            description=description,
            creator=creator,
            eif_date=eif_date,
            policy_contact=policy_contact,
        )
    )

    # Test that workflow values are valid.
    assert (
        task_workflow.creator_template
        == task_workflow_template_three_task_template_items
    )
    assert task_workflow.summary_task.title == ticket_name
    assert task_workflow.summary_task.description == description
    assert task_workflow.summary_task.creator == creator
    assert task_workflow.get_items().count() == 3
    assert task_workflow.eif_date == eif_date
    assert task_workflow.policy_contact == policy_contact

    # Validate that item positions are equivalent.
    zipped_items = zip(
        task_workflow_template_three_task_template_items.get_items(),
        task_workflow.get_items(),
    )
    for item_template, item in zipped_items:
        assert item_template.position == item.position

    # Validate that object values are equivalent.
    zipped_objs = zip(
        task_workflow_template_three_task_template_items.get_task_templates(),
        task_workflow.get_tasks(),
    )
    for task_template, task in zipped_objs:
        assert task_template.title == task.title
        assert task_template.description == task.description


def test_delete_task_item_template():
    task_item_template = factories.TaskItemTemplateFactory.create()
    task_item_template_id = task_item_template.id
    task_template_id = task_item_template.task_template.id

    assert TaskItemTemplate.objects.get(id=task_item_template_id)
    assert TaskTemplate.objects.get(id=task_template_id)

    task_item_template.delete()

    with pytest.raises(ObjectDoesNotExist):
        TaskItemTemplate.objects.get(id=task_item_template_id)
    assert TaskTemplate.objects.get(id=task_template_id)


def test_delete_task_template():
    task_item_template = factories.TaskItemTemplateFactory.create()
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


def test_delete_task_workflow_template(
    task_workflow_template_three_task_template_items,
):
    task_item_template_ids = [
        item.id for item in task_workflow_template_three_task_template_items.get_items()
    ]
    task_template_ids = [
        task.id
        for task in task_workflow_template_three_task_template_items.get_task_templates()
    ]

    assert len(task_item_template_ids) == 3
    assert len(task_template_ids) == 3

    task_workflow_template_three_task_template_items.delete()

    assert not TaskItemTemplate.objects.filter(id__in=task_item_template_ids).exists()
    assert TaskTemplate.objects.filter(id__in=task_template_ids).count() == 3
