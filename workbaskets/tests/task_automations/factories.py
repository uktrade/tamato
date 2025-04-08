from factory import SubFactory
from factory.django import DjangoModelFactory

from tasks.tests.factories import TaskFactory
from workbaskets.models import CreateWorkBasketAutomation


class CreateWorkBasketAutomationFactory(DjangoModelFactory):
    """Factory to create CreateWorkBasketAutomation instances."""

    class Meta:
        model = CreateWorkBasketAutomation

    task = SubFactory(TaskFactory)
