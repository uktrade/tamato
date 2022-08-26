from django.db import models
from django.db.models import QuerySet
from django.db.transaction import atomic
from polymorphic.query import PolymorphicQuerySet

from common.business_rules import ALL_RULES


class BusinessRuleResultStatus(models.IntegerChoices):
    """
    The outcome of running a business rule.

    PASSED: The business rule passed.
    FAILED: The business rule failed, message is populated.
    ERROR: An exception occurred while running the business rule, the name is added to the message field.
    """

    PASSED = 1
    FAILED = 2
    ERROR = 3


class BusinessRuleResultQuerySet(QuerySet):
    def errored(self):
        return self.filter(status=BusinessRuleResultStatus.ERROR)

    def failed(self):
        return self.filter(status=BusinessRuleResultStatus.FAILED)

    def not_passed(self):
        return self.filter(status__ne=BusinessRuleResultStatus.PASSED)

    def passed(self):
        return self.filter(status=BusinessRuleResultStatus.PASSED)


class BusinessRuleModelQuerySet(QuerySet):
    def current(self):
        """Return business rules that have not been removed."""
        return self.filter(current=True)

    def get_updated_rules(self):
        """
        :return (added, removed):  Lists of rules that were added and removed since sync_business_rules was last run.
        """
        all_rules = set(self.model.objects.current().values_list("name", flat=True))
        added_rules = set()

        for rule_name in ALL_RULES.keys():
            if rule_name not in all_rules:
                added_rules.add(rule_name)
            all_rules.discard(rule_name)

        return list(added_rules), list(all_rules)


class TrackedModelCheckQueryset(PolymorphicQuerySet):
    def delete(self):
        """
        Delete, modified to workaround a python bug that stops delete from
        working when some fields are ByteFields.

        Details:

        Using .delete() on a query with ByteFields does not work due to a python bug:
          https://github.com/python/cpython/issues/95081
        >>> TrackedModelCheck.objects.filter(
            model__transaction__workbasket=workbasket_pk,
            ).delete()

         File /usr/local/lib/python3.8/copy.py:161, in deepcopy(x, memo, _nil)
            159 reductor = getattr(x, "__reduce_ex__", None)
            160 if reductor is not None:
        --> 161     rv = reductor(4)
            162 else:
            163     reductor = getattr(x, "__reduce__", None)

        TypeError: cannot pickle 'memoryview' object

        Work around this by setting the bytefields to None and then calling delete.
        """
        with atomic():
            self.update(content_hash=None)
            return super().delete()
