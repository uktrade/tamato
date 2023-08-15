from dataclasses import dataclass

from django.db import models


@dataclass
class NotificationType:
    notification_type: str
    display_name: str
    query: models.Q


GOODS_REPORT = NotificationType(
    "goods_report",
    "Goods Report",
    models.Q(enrol_goods_report=True),
)
PACKAGING = NotificationType("packaging", "Packaging", models.Q(enrol_packaging=True))
PUBLISHING = NotificationType(
    "publishing",
    "Publishing",
    models.Q(enrol_api_publishing=True),
)

NOTIFICATION_TYPES = [GOODS_REPORT, PACKAGING, PUBLISHING]
NOTIFICATION_CHOICES = [
    (nt.notification_type, nt.display_name) for nt in NOTIFICATION_TYPES
]
