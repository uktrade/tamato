from django.conf import settings
from django.utils.module_loading import import_string

from notifications.notifications_api.interface import NotificationAPIBase
from notifications.notifications_api.interface import NotificationAPIStubbed


def get_notificaiton_api_interface() -> NotificationAPIBase:
    """Get the Notifications API interface from the NOTIFICATIONS_API_INTERFACE
    setting."""
    if not settings.NOTIFICATIONS_API_INTERFACE:
        return NotificationAPIStubbed()

    interface_class = import_string(settings.NOTIFICATIONS_API_INTERFACE)
    if not issubclass(interface_class, NotificationAPIBase):
        raise ValueError(
            "NOTIFICATIONS_API_INTERFACE must inherit from NotificationAPIBase",
        )

    return interface_class()
