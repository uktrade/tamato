"""WorkBasket models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
from django.db.models import QuerySet
from django.db.models import Subquery
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from common.models.records import TrackedModel
from common.models.records import TrackedModelQuerySet
from common.models.transactions import Transaction
from workbaskets.validators import WorkflowStatus


class WorkBasketQueryset(QuerySet):
    def prefetch_ordered_tracked_models(self) -> QuerySet:
        """Sort tracked_models by record_number, subrecord_number by using
        prefetch and imposing the order there."""

        q_annotate_record_code = TrackedModel.objects.annotate_record_codes().order_by(
            "record_code",
            "subrecord_code",
        )
        return self.prefetch_related(
            Prefetch("tracked_models", queryset=q_annotate_record_code),
        )

    def ordered_transactions(self):
        """
        This Workbaskets transactions in creation order.

        Note: tracked_models are ordered by record_code, subrecord_code by TransactionManager
        """
        workbasket_pks = self.values_list("pk", flat=True)
        return Transaction.objects.filter(
            workbasket__pk__in=Subquery(workbasket_pks),
        ).order_by("order")

    def is_approved(self):
        return self.filter(
            status__in=WorkflowStatus.approved_statuses(),
            approver__isnull=False,
        )

    def is_not_approved(self):
        return self.exclude(
            status__in=WorkflowStatus.approved_statuses(),
            approver__isnull=False,
        )


class WorkBasket(TimestampedMixin):
    """
    A WorkBasket groups tariff edits which will be applied at the same time.

    WorkBasket status is controlled by a state machine:
    See https://uktrade.atlassian.net/wiki/spaces/TARIFFSALPHA/pages/953581609/a.+Workbasket+workflow
    """

    objects = WorkBasketQueryset.as_manager()

    title = models.CharField(
        max_length=255,
        help_text="Short name for this workbasket",
        db_index=True,
        unique=True,
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for the changes to the tariff",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name="approved_workbaskets",
    )
    status = FSMField(
        default=WorkflowStatus.EDITING,
        choices=WorkflowStatus.choices,
        db_index=True,
        # Ideally, we would protect the status field from being modified except by the
        # transition methods, otherwise the workbasket contents can be left in an
        # invalid state.  Unfortunately if `protected` is True the `clean` method raises
        # an exception.
        protected=False,
        editable=False,
    )

    @property
    def approved(self):
        return self.status in WorkflowStatus.approved_statuses()

    def __str__(self):
        return f"({self.pk}) [{self.status}]"

    @transition(
        field=status,
        source=WorkflowStatus.EDITING,
        target=WorkflowStatus.PROPOSED,
        custom={"label": "Submit for approval"},
    )
    def submit_for_approval(self):
        self.full_clean()

    @transition(
        field=status,
        source=WorkflowStatus.PROPOSED,
        target=WorkflowStatus.EDITING,
        custom={"label": "Withdraw or reject submission"},
    )
    def withdraw(self):
        """Withdraw/reject a proposed workbasket."""

    @transition(
        field=status,
        source=WorkflowStatus.PROPOSED,
        target=WorkflowStatus.APPROVED,
        custom={"label": "Approve"},
    )
    def approve(self, user):
        """Once a workbasket has been approved all related Tracked Models must
        be updated to the current versions of themselves."""
        self.approver = user
        for obj in self.tracked_models.order_by("pk"):
            version_group = obj.version_group
            version_group.current_version = obj
            version_group.save()

    @transition(
        field=status,
        source=WorkflowStatus.APPROVED,
        target=WorkflowStatus.SENT,
        custom={"label": "Send to HMRC"},
    )
    def export_to_cds(self):
        """Tariff changes in workbasket have been sent to HMRC CDS."""

    @transition(
        field=status,
        source=WorkflowStatus.SENT,
        target=WorkflowStatus.PUBLISHED,
        custom={"label": "Publish"},
    )
    def cds_confirmed(self):
        """HMRC CDS has accepted the changes to the tariff."""

    @transition(
        field=status,
        source=WorkflowStatus.SENT,
        target=WorkflowStatus.ERRORED,
        custom={"label": "Mark as in error"},
    )
    def cds_error(self):
        """If a workbasket, after approval, is then rejected by CDS it is
        important to roll back the current models to the previous approved
        version."""
        for obj in self.tracked_models.order_by("-pk").select_related("version_group"):
            version_group = obj.version_group
            versions = (
                version_group.versions.has_approved_state()
                .order_by("-pk")
                .exclude(pk=obj.pk)
            )
            if versions.count() == 0:
                version_group.current_version = None
            else:
                version_group.current_version = versions.first()
            version_group.save()

    def save_to_session(self, session):
        session["workbasket"] = {
            "id": self.pk,
            "status": self.status,
        }

    @property
    def tracked_models(self) -> TrackedModelQuerySet:
        return TrackedModel.objects.filter(transaction__workbasket=self)

    @classmethod
    def load_from_session(cls, session):
        if "workbasket" not in session:
            raise KeyError("WorkBasket not in session")
        return WorkBasket.objects.get(pk=session["workbasket"]["id"])

    @classmethod
    def current(cls, request):
        """Get the current workbasket in the session."""

        if "workbasket" in request.session:
            workbasket = cls.load_from_session(request.session)

            if workbasket.status in WorkflowStatus.approved_statuses():
                del request.session["workbasket"]
                return None

            return workbasket

    @classmethod
    def get_current_transaction(cls, request):
        workbasket = cls.current(request)
        if workbasket:
            return workbasket.transactions.order_by("order").last()

        return None

    def clean(self):
        errors = []
        for txn in self.transactions.order_by("order"):
            try:
                txn.clean()
            except ValidationError as e:
                errors.extend(e.error_list)

        if any(errors):
            raise ValidationError(errors)

    def new_transaction(self, **kwargs):
        """Create a new transaction in this workbasket."""
        if "order" not in kwargs:
            kwargs["order"] = self.transactions.count() + 1

        if "composite_key" not in kwargs:
            kwargs["composite_key"] = f"{self.pk}-{kwargs['order']}"

        return self.transactions.model.objects.create(workbasket=self, **kwargs)
