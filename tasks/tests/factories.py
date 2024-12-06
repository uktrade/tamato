import factory
from factory import SubFactory
from factory.django import DjangoModelFactory

from common.tests.factories import CategoryFactory
from common.tests.factories import TaskFactory
from tasks.models import TaskItem
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate


class TaskWorkflowTemplateFactory(DjangoModelFactory):
    """Factory to create TaskWorkflowTemplate instances."""

    title = factory.Faker("sentence")
    description = factory.Faker("sentence")

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

    workflow_template = SubFactory(TaskWorkflowTemplateFactory)
    task_template = SubFactory(TaskTemplateFactory)


class TaskWorkflowFactory(DjangoModelFactory):
    """Factory to create TaskWorkflow instances."""

    class Meta:
        model = TaskWorkflow

    summary_task = SubFactory(TaskFactory)


class TaskItemFactory(DjangoModelFactory):
    """Factory to create TaskItem instances."""

    class Meta:
        model = TaskItem

    workflow = SubFactory(TaskWorkflowFactory)
    task = SubFactory(TaskFactory)
