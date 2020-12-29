"""Transaction model and manager"""
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Prefetch

from common.business_rules import BusinessRuleViolation


class TransactionManager(models.Manager):
    """Sorts TrackedModels by record_number and subrecord_number"""

    def get_queryset(self):
        annotate_record_code = self.model.tracked_models.rel.related_model.objects.annotate_record_codes().order_by(
            "record_code",
            "subrecord_code",
        )
        return (
            super()
            .get_queryset()
            .prefetch_related(Prefetch("tracked_models", queryset=annotate_record_code))
        )


class Transaction(models.Model):
    """Contains a group of one or more TrackedModel instances that must be applied
    atomically.

    Linked to a WorkBasket and may be contained by one or more Envelopes when exported.

    Business rule validation is performed at Transaction level for creates, updates and
    deletes. Business rules are also validated at the TrackedModel level for creates.
    """

    import_transaction_id = models.IntegerField(null=True, editable=False)
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket", on_delete=models.PROTECT, related_name="transactions"
    )
    order = (
        models.IntegerField()
    )  # The order this transaction appears within the workbasket

    composite_key = models.CharField(max_length=16, unique=True)

    objects = TransactionManager()

    def clean(self):
        """Validate business rules against contained TrackedModels."""

        if settings.SKIP_VALIDATION:
            return

        self.errors = []
        for model in self.tracked_models.all():
            for rule in model.business_rules:
                try:
                    rule.validate(model)
                except BusinessRuleViolation as violation:
                    self.errors.append((model, violation))

        if self.errors:
            raise ValidationError(self.errors)

    def to_json(self):
        """Serialize to JSON. Used for storing in the session."""

        return json.dumps(
            {key: val for key, val in self.__dict__.items() if key != "_state"},
            cls=DjangoJSONEncoder,
        )

    def __enter__(self):
        models.signals.pre_save.connect(self.add_to_transaction, dispatch_uid=id(self))

    def __exit__(self, *exc):
        models.signals.pre_save.disconnect(
            self.add_to_transaction, dispatch_uid=id(self)
        )

    def add_to_transaction(self, instance, **kwargs):
        if hasattr(instance, "transaction"):
            instance.transaction = self


class TransactionGroup(models.Model):
    """An ordered group of Transactions.

    Transactions often must be applied in a specific sequence, for example to ensure
    a Measure exists before a Footnote can be associated with it.

    A Transaction may belong to several groups, for example a group associated with an
    imported Envelope, and with a WorkBasket.
    """

    group_id = models.IntegerField()
    order_in_group = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT)
