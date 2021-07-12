from django.db import models

# class TransactionStatus(models.TextChoices):
#     DRAFT = "Draft"
#
#     PUBLISHED = ""


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

    @classmethod
    def approved_statuses(cls):
        return (
            cls.READY_FOR_EXPORT,
            cls.AWAITING_CDS_UPLOAD_CREATE_NEW,
            cls.AWAITING_CDS_UPLOAD_EDIT,
            cls.AWAITING_CDS_UPLOAD_OVERWRITE,
            cls.AWAITING_CDS_UPLOAD_DELETE,
            cls.SENT_TO_CDS,
            cls.SENT_TO_CDS_DELETE,
            cls.PUBLISHED,
            cls.CDS_ERROR,
        )
