from django.db import models
from django.db.models import fields

from checks.querysets import TransactionCheckQueryset
from common.models.mixins import TimestampedMixin
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction


class TransactionCheck(models.Model):
    """
    Represents an in-progress or completed check of a transaction for
    correctness.

    The ``TransactionCheck`` gets created once the check starts and has a flag
    to track completeness.
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="checks",
    )

    completed = fields.BooleanField(default=False)
    """True if all of the checks expected to be carried out against the models
    in this transaction have recorded any result."""

    successful = fields.BooleanField(null=True)
    """
    True if all of the checks carried out against the models in this
    transaction returned a positive result.
    
    This value will be null until ``completed`` is `True`.
    """

    head_transaction_id: int
    head_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
    )
    """
    The latest transaction in the stream of approved transactions (i.e. in the
    REVISION partition) at the moment this check was carried out.

    Once new transactions are commited and the head transaction is no longer the
    latest, this check will no longer be an accurate signal of correctness
    because the new transactions could include new data which would invalidate
    the checks. (Unless the checked transaction < head transaction, in which
    case it will always be correct.)
    """

    tracked_model_count = fields.PositiveSmallIntegerField()
    """
    The number of tracked models in the transaction at the moment this check was
    carried out.

    If something is removed from the transaction later, the number of tracked
    models will no longer match. This is used to detect if the check is now
    stale.
    """

    latest_tracked_model = models.ForeignKey(
        TrackedModel,
        on_delete=models.CASCADE,
        null=True,
    )
    """
    The latest tracked model in the transaction at the moment this check was
    carried out.
    
    If some models are removed and subsequent ones added to the transaction, the
    count may be the same but the latest transaction will have a new primary
    key. This is used to detect if the check is now stale.
    """

    model_checks: models.QuerySet["TrackedModelCheck"]

    objects: TransactionCheckQueryset = models.Manager.from_queryset(
        TransactionCheckQueryset,
    )()

    def save(self, *args, **kwargs):
        """Computes the metadata we will need later to detect if the check is
        current and fresh."""
        if not self.head_transaction_id:
            self.head_transaction = Transaction.approved.last()

        self.tracked_model_count = self.transaction.tracked_models.count()
        self.latest_tracked_model = self.transaction.tracked_models.order_by(
            "pk",
        ).last()

        return super().save(*args, **kwargs)

    class Meta:
        ordering = (
            "transaction__partition",
            "transaction__order",
            "head_transaction__partition",
            "head_transaction__order",
        )

        constraints = (
            models.CheckConstraint(
                check=(
                    models.Q(completed=False, successful__isnull=True)
                    | models.Q(completed=True, successful__isnull=False)
                ),
                name="completed_checks_include_successfulness",
            ),
        )


class TrackedModelCheck(TimestampedMixin):
    """
    Represents the result of running a single check against a single model.

    The ``TrackedModelCheck`` only gets created once the check is complete, and
    hence success should always be known. The reason is that a single model
    check is atomic (i.e. there is no smaller structure) and so it's either done
    or not, and it can't be "resumed".
    """

    model = models.ForeignKey(
        TrackedModel,
        related_name="checks",
        on_delete=models.CASCADE,
    )

    transaction_check = models.ForeignKey(
        TransactionCheck,
        on_delete=models.CASCADE,
        related_name="model_checks",
    )

    check_name = fields.CharField(max_length=255)
    """A string identifying the type of check carried out."""

    successful = fields.BooleanField()
    """True if the check was successful."""

    message = fields.TextField(null=True)
    """The text content returned by the check, if any."""

    @property
    def rule_code(self):
        """
        Expects `check_name` value in the format
        `BusinessRuleCheckerOf[footnotes.business_rules.FO4]`.

        Returns business rule code (e.g. `FO4`).
        """
        return self.check_name.split(".")[-1][:-1]
