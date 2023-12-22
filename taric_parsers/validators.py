from django.db import models


class ImportStatus(models.TextChoices):
    FAILED = "FAILED", "Failed"
    """An issue was detected that prevented the import from proceeding."""

    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS", "Completed with warnings"
    """Non failure issues were detected, but the import completed."""

    COMPLETED = "COMPLETED", "Completed"
    """Import completed without any issues."""

    EMPTY = "EMPTY", "Empty"
    """No data to import."""
