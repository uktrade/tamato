from django.core.validators import RegexValidator
from django.db import models

tops_jira_number_validator = RegexValidator(
    r"^[0-9]+$",
    message="Your TOPS/Jira number must only include numbers. You do not need to add ‘TOPS’ or ‘Jira’ in front of the number.",
)


class WorkflowStatus(models.TextChoices):
    # Mark a workbasket as no longer in use.
    ARCHIVED = "ARCHIVED", "Archived"
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
        )

    @classmethod
    def unchecked_statuses(cls):
        """
        A successful transition out of EDITING may only occur when all business
        rule checks have succeeded.

        WorkBaskets with the following set of statuses may have successful rule
        checks, but this isn't guarenteed.
        """
        return (
            cls.ARCHIVED,
            cls.EDITING,
            cls.ERRORED,
        )
