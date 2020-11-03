import json
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Manager, Prefetch, QuerySet
from django_fsm import FSMField
from django_fsm import transition

from common.models import TimestampedMixin, TrackedModel
from workbaskets.validators import WorkflowStatus


class WorkBasketManager(Manager):
    def prefetch_ordered_tracked_models(self) -> QuerySet:
        """
        Sort tracked_models by record_number, subrecord_number by
        using prefetch and imposing the order there.
        """
        q = self.get_queryset()

        q_annotate_record_code = TrackedModel.objects.annotate_record_codes().order_by(
            "record_code", "subrecord_code"
        )
        return q.prefetch_related(
            Prefetch("tracked_models", queryset=q_annotate_record_code)
        )


class WorkBasket(TimestampedMixin):
    """A WorkBasket groups tariff edits which will be applied at the same time.

    WorkBasket status is controlled by a state machine:
    See https://uktrade.atlassian.net/wiki/spaces/TARIFFSALPHA/pages/953581609/a.+Workbasket+workflow
    """

    objects = WorkBasketManager()

    title = models.CharField(max_length=255, help_text="Short name for this workbasket")
    reason = models.TextField(
        blank=True, help_text="Reason for the changes to the tariff"
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
    )

    def __str__(self):
        return f"{self.title} ({self.pk}) - {self.status}"

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
    def approve(self):
        pass

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
        pass

    def clean(self):
        self.errors = []
        for model in self.tracked_models.all():
            try:
                model.validate_workbasket()
            except ValidationError as error:
                self.errors.append((model, error))
        if self.errors:
            raise ValidationError(self.errors)

    def to_json(self):
        """Used for serializing the workbasket to the session"""

        data = {key: val for key, val in self.__dict__.items() if key != "_state"}
        if "transaction" in data:
            data["transaction"] = self.transaction.to_json()

        # return a dict for convenient access to fields
        return json.loads(json.dumps(data, cls=DjangoJSONEncoder))

    @classmethod
    def from_json(cls, data):
        """Restore from session"""

        return WorkBasket(
            id=int(data["id"]),
            pk=int(data["id"]),
            title=data["title"],
            reason=data["reason"],
            status=data["status"],
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
            author_id=int(data["author_id"]),
            approver_id=int(data["approver_id"]) if data["approver_id"] else None,
        )

    @classmethod
    def current(cls, request):
        """Get the current workbasket in the session"""

        if "workbasket" in request.session:
            return cls.from_json(request.session["workbasket"])


class Transaction(TimestampedMixin):
    """A Transaction is created once the WorkBasket has been sent for approval"""

    workbasket = models.OneToOneField(
        WorkBasket,
        on_delete=models.PROTECT,
        editable=False,
    )

    def to_json(self):
        """Used for serializing to the session"""

        data = {key: val for key, val in self.__dict__.items() if key != "_state"}
        return json.dumps(data, cls=DjangoJSONEncoder)
