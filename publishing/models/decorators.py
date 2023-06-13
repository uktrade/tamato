import logging

from django.conf import settings
from django.db.transaction import atomic

# Common publishing decorators

logger = logging.getLogger(__name__)


def save_after(func):
    """
    Decorator used to save PackagedWorkBaskert instances after a state
    transition.

    This ensures a transitioned instance is always saved, which is necessary due
    to the DB updates that occur as part of a transition.
    """

    @atomic
    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save()
        return result

    return inner


def refresh_after(func):
    """
    Decorator used to refresh the PackagedWorkBasket instance after a state
    transition.

    This ensures a transitioned instance is always reload, which is necessary
    when another action may update the packaged workbasket for example when a
    TAPApiEnvelope is created.
    """

    @atomic
    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.refresh_from_db()
        return result

    return inner


def skip_notifications_if_disabled(func):
    """Decorator used to wrap notification issuing functions, ensuring
    notifications are not sent when settings.ENABLE_PACKAGING_NOTIFICATIONS is
    False."""

    def inner(self, *args, **kwargs):
        if not settings.ENABLE_PACKAGING_NOTIFICATIONS:
            logger.info(
                "Skipping ready for processing notifications - "
                "settings.ENABLE_PACKAGING_NOTIFICATIONS="
                f"{settings.ENABLE_PACKAGING_NOTIFICATIONS}",
            )
            return
        logger.info(
            "Sending ready for processing notifications - "
            "settings.ENABLE_PACKAGING_NOTIFICATIONS="
            f"{settings.ENABLE_PACKAGING_NOTIFICATIONS}",
        )
        return func(self, *args, **kwargs)

    return inner
