from django.db import models


class WorkflowStatus(models.TextChoices):
    # Workbasket can still be edited
    EDITING = "EDITING", "Editing"
    # Submitted for approval, pending response from an approver
    PROPOSED = "PROPOSED", "Proposed"
    # Approved and scheduled for sending to CDS
    APPROVED = "APPROVED", "Approved"
    # Send to CDS and waiting for response
    SENT = "SENT", "Sent"
    # Received a validation receipt from CDS systems
    PUBLISHED = "PUBLISHED", "Published"
    # Sent to CDS, but CDS returned an invalid data receipt
    ERRORED = "ERRORED", "Errored"

    @classmethod
    def approved_statuses(cls):
        return (
            cls.APPROVED,
            cls.SENT,
            cls.PUBLISHED,
            cls.ERRORED,
        )
