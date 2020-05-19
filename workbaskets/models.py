from enum import Enum

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django_fsm import FSMField
from django_fsm import transition

from common.models import TimestampedMixin


class Workflow(models.Model):
    """Encapsulates the workbasket workflow state machine

    See https://uktrade.atlassian.net/wiki/spaces/TARIFFSALPHA/pages/953581609/a.+Workbasket+workflow
    """

    class Meta:
        abstract = True

    WorkflowStatus = models.TextChoices(
        "WorkflowStatus",
        [
            # Newly started, but not yet submitted into workflow
            "NEW_IN_PROGRESS",
            # Existing item, already on CDS, being edited but not yet submitted into workflow
            "EDITING",
            # Submitted for approval, pending response from Approver
            "AWAITING_APPROVAL",
            # Was not approved, returned to submitter
            "APPROVAL_REJECTED",
            # Approved but not yet scheduled for sending to CDS
            "READY_FOR_EXPORT",
            # New item approved and scheduled for sending to CDS
            "AWAITING_CDS_UPLOAD_CREATE_NEW",
            # Edited item approved and scheduled for sending to CDS, existing version will be end-dated and replaced
            "AWAITING_CDS_UPLOAD_EDIT",
            # Edited item approved and scheduled for sending to CDS, existing version will be updated
            "AWAITING_CDS_UPLOAD_OVERWRITE",
            # Delete instruction approved and scheduled for sending to CDS
            "AWAITING_CDS_UPLOAD_DELETE",
            # Sent to CDS, waiting for response
            "SENT_TO_CDS",
            # Delete instruction sent to CDS, waiting for response
            "SENT_TO_CDS_DELETE",
            # On CDS, may or may not have taken effect
            "PUBLISHED",
            # Sent to CDS, but CDS returned an error
            "CDS_ERROR",
        ],
    )

    status = FSMField(
        default=WorkflowStatus.NEW_IN_PROGRESS, choices=WorkflowStatus.choices,
    )

    @transition(
        field=status,
        source=[WorkflowStatus.NEW_IN_PROGRESS, WorkflowStatus.EDITING,],
        target=WorkflowStatus.AWAITING_APPROVAL,
    )
    def submit_for_approval(self):
        pass

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


class ApprovalDecision(TimestampedMixin):
    """ApprovalDecision represents whether a WorkBasket (or WorkBasketItem) has been
    approved or rejected
    """

    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(
        max_length=8,
        choices=models.TextChoices(
            "ApprovalDecision", ["APPROVED", "REJECTED"]
        ).choices,
    )
    reason = models.TextField(blank=True, help_text="Reason for decision")


class WorkBasket(TimestampedMixin, Workflow):
    """A WorkBasket groups tariff edits which will be applied at the same time"""

    title = models.CharField(max_length=255)
    reason = models.TextField(
        blank=True, help_text="Reason for the changes to the tariff"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approval = models.ForeignKey(ApprovalDecision, on_delete=models.PROTECT, null=True)


class WorkBasketItem(TimestampedMixin):
    """A WorkBasketItem represents draft changes to records (measures, quotas, etc)"""

    workbasket = models.ForeignKey(
        WorkBasket, on_delete=models.CASCADE, related_name="items"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    existing_record = GenericForeignKey("content_type", "object_id")
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True)
    object_id = models.PositiveIntegerField(null=True)

    """The diff field encodes the changes to be applied to the record, for audit logging
    """
    diff = JSONField(default=dict)

    """The draft field encodes the record data with the changes applied, for efficiency
    when previewing the changes
    """
    draft = JSONField(default=dict)

    """The errors field encodes the errors returned by QAM and CDS (if there are any)"""
    errors = JSONField(default=list)
