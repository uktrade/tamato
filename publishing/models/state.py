from django.db.models import TextChoices


class QueueState(TextChoices):
    PAUSED = ("PAUSED", "Envelope processing is paused")
    UNPAUSED = ("UNPAUSED", "Envelope processing is unpaused and may proceed")


class ProcessingState(TextChoices):
    """Processing states of PackagedWorkBasket instances."""

    AWAITING_PROCESSING = (
        "AWAITING_PROCESSING",
        "Awaiting processing",
    )
    """Queued up and awaiting processing."""
    CURRENTLY_PROCESSING = (
        "CURRENTLY_PROCESSING",
        "Currently processing",
    )
    """Picked off the queue and now currently being processed - now attempting
    to ingest envelope into CDS."""
    SUCCESSFULLY_PROCESSED = (
        "SUCCESSFULLY_PROCESSED",
        "Successfully processed",
    )
    """Processing now completed with a successful outcome - envelope ingested
    into CDS."""
    FAILED_PROCESSING = (
        "FAILED_PROCESSING",
        "Failed processing",
    )
    """Processing now completed with a failure outcome - CDS rejected the
    envelope."""
    ABANDONED = (
        "ABANDONED",
        "Abandoned",
    )
    """Processing has been abandoned."""

    @classmethod
    def queued_states(cls):
        """Returns all states that represent a queued  instance, including those
        that are being processed."""
        return (cls.AWAITING_PROCESSING, cls.CURRENTLY_PROCESSING)

    @classmethod
    def completed_processing_states(cls):
        return (
            cls.SUCCESSFULLY_PROCESSED,
            cls.FAILED_PROCESSING,
        )


class ApiPublishingState(TextChoices):
    """Publishing states of TAPApiEnvelope instances."""

    AWAITING_PUBLISHING = (
        "AWAITING_PUBLISHING",
        "Awaiting publishing",
    )
    """Queued up and awaiting publishing."""
    CURRENTLY_PUBLISHING = (
        "CURRENTLY_PUBLISHING",
        "Currently publishing",
    )
    """Picked off the task queue and now currently being processed - now attempting
    to publish to the channel islands API."""
    SUCCESSFULLY_PUBLISHED = (
        "SUCCESSFULLY_PUBLISHED",
        "Successfully published",
    )
    """Publishing now completed with a successful outcome - envelope published
    to staging and production API."""
    FAILED_PUBLISHING_STAGING = (
        "FAILED_PUBLISHING_STAGING",
        "Failed publishing staging",
    )
    """Publishing now completed with a failure outcome - staging API failed publishing the
    envelope."""
    FAILED_PUBLISHING_PRODUCTION = (
        "FAILED_PUBLISHING_PRODUCTION",
        "Failed publishing production",
    )
    """Publishing now completed with a failure outcome - production API failed publishing the
    envelope."""

    @classmethod
    def queued_states(cls):
        """Returns all states that represent a queued  instance, including those
        that are being processed."""
        return (
            cls.FAILED_PUBLISHING_PRODUCTION,
            cls.FAILED_PUBLISHING_STAGING,
            cls.AWAITING_PUBLISHING,
            cls.CURRENTLY_PUBLISHING,
        )
