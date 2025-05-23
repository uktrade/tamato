from factory import SubFactory
from factory.django import DjangoModelFactory

from common.tests.factories import ImportBatchFactory
from importer.models import ImportGoodsAutomation
from tasks.tests.factories import TaskFactory


class ImportGoodsAutomationFactory(DjangoModelFactory):
    """Factory to create ImportGoodsAutomation instances."""

    class Meta:
        model = ImportGoodsAutomation

    task = SubFactory(TaskFactory)
    import_batch = SubFactory(ImportBatchFactory)
