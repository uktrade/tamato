from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField
from django_fsm import transition

from common.models import TimestampedMixin


class WorkflowStatus(models.TextChoices):
    # Newly started, but not yet submitted into workflow
    NEW_IN_PROGRESS = "NEW_IN_PROGRESS", "New - in progress"
    # Existing item, already on CDS, being edited but not yet submitted into workflow
    EDITING = "EDITING", "Editing"
    # Submitted for approval, pending response from Approver
    AWAITING_APPROVAL = "AWAITING_APPROVAL", "Awaiting approval"
    # Was not approved, returned to submitter
    APPROVAL_REJECTED = "APPROVAL_REJECTED", "Failed approval"
    # Approved but not yet scheduled for sending to CDS
    READY_FOR_EXPORT = "READY_FOR_EXPORT", "Ready for export"
    # New item approved and scheduled for sending to CDS
    AWAITING_CDS_UPLOAD_CREATE_NEW = (
        "AWAITING_CDS_UPLOAD_CREATE_NEW",
        "Awaiting CDS upload - create new",
    )
    # Edited item approved and scheduled for sending to CDS, existing version will be end-dated and replaced
    AWAITING_CDS_UPLOAD_EDIT = "AWAITING_CDS_UPLOAD_EDIT", "Awaiting CDS upload - edit"
    # Edited item approved and scheduled for sending to CDS, existing version will be updated
    AWAITING_CDS_UPLOAD_OVERWRITE = (
        "AWAITING_CDS_UPLOAD_OVERWRITE",
        "Awaiting CDS upload - overwrite",
    )
    # Delete instruction approved and scheduled for sending to CDS
    AWAITING_CDS_UPLOAD_DELETE = (
        "AWAITING_CDS_UPLOAD_DELETE",
        "Awaiting CDS upload - delete",
    )
    # Sent to CDS, waiting for response
    SENT_TO_CDS = "SENT_TO_CDS", "Sent to CDS"
    # Delete instruction sent to CDS, waiting for response
    SENT_TO_CDS_DELETE = "SENT_TO_CDS_DELETE", "Sent to CDS - delete"
    # On CDS, may or may not have taken effect
    PUBLISHED = "PUBLISHED", "Published"
    # Sent to CDS, but CDS returned an error
    CDS_ERROR = "CDS_ERROR", "CDS error"


class WorkBasket(TimestampedMixin):
    """A WorkBasket groups tariff edits which will be applied at the same time.

    WorkBasket status is controlled by a state machine:
    See https://uktrade.atlassian.net/wiki/spaces/TARIFFSALPHA/pages/953581609/a.+Workbasket+workflow
    """

    title = models.CharField(max_length=255, help_text="Short name for this workbasket")
    reason = models.TextField(
        blank=True, help_text="Reason for the changes to the tariff"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False,
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name="approved_workbaskets",
    )
    status = FSMField(
        default=WorkflowStatus.NEW_IN_PROGRESS, choices=WorkflowStatus.choices,
    )

    def __str__(self):
        return f"{self.title} ({self.pk})"

    @transition(
        field=status,
        source=[WorkflowStatus.NEW_IN_PROGRESS, WorkflowStatus.EDITING,],
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
        for model in self.trackedmodel_set.all():
            try:
                model.validate_workbasket()
            except ValidationError as error:
                self.errors.append((model, error))
        if self.errors:
            raise ValidationError("There are errors in the workbasket", self.errors)


class Transaction(TimestampedMixin):
    """A Transaction is created once the WorkBasket has been sent for approval"""

    workbasket = models.OneToOneField(
        WorkBasket, on_delete=models.PROTECT, editable=False,
    )
