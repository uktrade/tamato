from django.db.models import TextChoices


class EventChoice(TextChoices):
    """Code which indicates the event in the datestamp table."""

    REFRESH_OPEN_DATA = "Refresh", "Refresh open data"
    EXPORT_OPEN_DATA = "Export", "Export open data"


class OriginChoice(TextChoices):
    """Code which indicates the origin event in the datestamp table."""

    MANAGEMENT_COMMAND = "Command", "Management command"
    CELERY_WORKER = "" "", "Async process"
    TEST = 2, "Test"
