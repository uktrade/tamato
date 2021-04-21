"""WorkBasket models."""
import json
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Prefetch
from django.db.models import QuerySet
from django.db.models import Subquery
from django_fsm import FSMField
from django_fsm import transition

from common.models import TimestampedMixin
from common.models import TrackedModel
from common.models import Transaction
from common.models.records import TrackedModelQuerySet
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
        default=WorkflowStatus.NEW_IN_PROGRESS,
        choices=WorkflowStatus.choices,
        db_index=True,
    )

    def __str__(self):
        return f"({self.pk}) [{self.status}]"

    @transition(
        field=status,
        source=[
            WorkflowStatus.NEW_IN_PROGRESS,
            WorkflowStatus.EDITING,
        ],
        target=WorkflowStatus.AWAITING_APPROVAL,
    )
    def submit_for_approval(self):
        self.full_clean()

    @transition(
        field=status,
        source=[
            WorkflowStatus.APPROVAL_REJECTED,
            WorkflowStatus.AWAITING_APPROVAL,
            WorkflowStatus.CDS_ERROR,
        ],
        target=WorkflowStatus.EDITING,
    )
    def withdraw(self):
        pass

    @transition(
        field=status,
        source=WorkflowStatus.AWAITING_APPROVAL,
        target=WorkflowStatus.APPROVAL_REJECTED,
        permission="workbaskets.can_approve",
    )
    def reject(self):
        pass

    @transition(
        field=status,
        source=WorkflowStatus.AWAITING_APPROVAL,
        target=WorkflowStatus.READY_FOR_EXPORT,
        permission="workbaskets.can_approve",
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
        source=WorkflowStatus.READY_FOR_EXPORT,
        target=WorkflowStatus.SENT_TO_CDS,
    )
    def export_to_cds(self):
        pass

    @transition(
        field=status,
        source=WorkflowStatus.SENT_TO_CDS,
        target=WorkflowStatus.PUBLISHED,
    )
    def cds_confirmed(self):
        pass

    @transition(
        field=status,
        source=WorkflowStatus.SENT_TO_CDS,
        target=WorkflowStatus.CDS_ERROR,
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

    def to_json(self):
        """Used for serializing the workbasket to the session."""

        data = {key: val for key, val in self.__dict__.items() if key != "_state"}
        if "transactions" in data:
            data["transactions"] = [
                transaction.to_json() for transaction in data["transactions"]
            ]

        # return a dict for convenient access to fields
        return json.loads(json.dumps(data, cls=DjangoJSONEncoder))

    @property
    def tracked_models(self) -> TrackedModelQuerySet:
        return TrackedModel.objects.filter(transaction__workbasket=self)

    @classmethod
    def from_json(cls, data):
        """Restore from session."""

        return WorkBasket(
            id=int(data["id"]),
            pk=int(data["id"]),
            title=data["title"],
            reason=data["reason"],
            status=data["status"],
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00"),
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00"),
            ),
            author_id=int(data["author_id"]),
            approver_id=int(data["approver_id"]) if data["approver_id"] else None,
        )

    @classmethod
    def current(cls, request):
        """Get the current workbasket in the session."""

        if "workbasket" in request.session:
            return cls.from_json(request.session["workbasket"])

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
