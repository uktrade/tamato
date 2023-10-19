from __future__ import annotations

from datetime import date

from common.validators import UpdateType


class ValidityMixin:
    """Parse validity start and end dates."""

    valid_between_lower: date = None
    valid_between_upper: date = None


class ValidityStartMixin:
    """Parse validity start date."""

    validity_start: date = None


class Writable:
    update_type: str

    def commit_to_database(self):
        kwargs = {
            "update_type": UpdateType.CREATE,
            "transaction": transaction,
            "order_number": quota_order_number,
            "geographical_area": resolve_geo_area(order_number["origin"]),
            "valid_between": valid_between,
        }


class ChildPeriod:
    def parent_attributes(self):
        return {
            "sid": self.sid,
            "validity_start": self.validity_start,
        }
