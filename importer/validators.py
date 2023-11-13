from django.db import models


class BatchImportErrorIssueType(models.TextChoices):
    ERROR = "ERROR", "Error"
    """An error occurred that prevents the processing of the import."""

    WARNING = "WARNING", "warning"
    """An issue was detected, but not severe enough to prevent import."""

    INFORMATION = "INFORMATION", "Information"
    """Information about the import that is of note but not effecting the
    success of the import."""
