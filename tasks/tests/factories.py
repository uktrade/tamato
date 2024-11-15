import factory
from factory import SubFactory
from factory.django import DjangoModelFactory

from common.tests.factories import CategoryFactory
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflowTemplate


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
