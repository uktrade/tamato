from dataclasses import dataclass
from typing import Optional

from checks.checks import Checker
from common.models.trackedmodel import TrackedModel


@dataclass(frozen=True)
class DummyChecker(Checker):
    name: str = "DummyChecker"
    success: bool = True
    message: Optional[str] = None

    def run(self, model: TrackedModel):
        return self.success, self.message


# class TransactionCheckFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = models.TransactionCheck
#
#     transaction = factory.SubFactory(
#         factories.TransactionFactory,
#         draft=True,
#     )
#     completed = True
#     successful = True
#     head_transaction = factory.SubFactory(factories.ApprovedTransactionFactory)
#     tracked_model_count = factory.LazyAttribute(
#         lambda check: (len(check.transaction.tracked_models.all())),
#     )
#     latest_tracked_model = factory.SubFactory(
#         factories.TestModel1Factory,
#         transaction=factory.SelfAttribute("..transaction"),
#     )
#
#     class Params:
#         incomplete = factory.Trait(
#             completed=False,
#             successful=None,
#         )
#
#         empty = factory.Trait(
#             latest_tracked_model=None,
#             tracked_model_count=0,
#         )
#
#
# class StaleTransactionCheckFactory(TransactionCheckFactory):
#     class Meta:
#         exclude = ("first", "second")
#
#     first = factory.SubFactory(
#         factories.TestModel1Factory,
#         transaction=factory.SelfAttribute("..transaction"),
#     )
#     second = factory.SubFactory(
#         factories.TestModel1Factory,
#         transaction=factory.SelfAttribute("..transaction"),
#     )
#
#     latest_tracked_model = factory.SelfAttribute("second")
#
#     @classmethod
#     def _after_postgeneration(cls, instance: TrackedModel, create, results=None):
#         """Save again the instance if creating and at least one hook ran."""
#         super()._after_postgeneration(instance, create, results)
#
#         if create:
#             assert instance.transaction.tracked_models.count() >= 2
#             instance.transaction.tracked_models.first().delete()
#
#
# class TrackedModelCheckFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = models.TrackedModelCheck
#
#     model = factory.SubFactory(
#         factories.TestModel1Factory,
#         transaction=factory.SelfAttribute("..transaction_check.transaction"),
#     )
#     transaction_check = factory.SubFactory(TransactionCheckFactory)
#     check_name = factories.string_sequence()
#     successful = True
#     message = None
