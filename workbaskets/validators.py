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
    # Workbasket added to the queue, ready to be downloaded by CDS
    QUEUED = "QUEUED", "Queued"
    # Received a validation receipt from CDS systems
    PUBLISHED = "PUBLISHED", "Published"
    # Sent to CDS, but CDS returned an invalid data receipt
    ERRORED = "ERRORED", "Errored"

    @classmethod
    def approved_statuses(cls):
        return (
            cls.QUEUED,
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
