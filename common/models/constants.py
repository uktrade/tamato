"""Includes constants and enumerators for use in orm models."""
from enum import Enum
from enum import auto


class ClockType(Enum):
    """Provides an enumeration for clock types used in the Taric system."""

    CALENDAR = auto()
    TRANSACTION = auto()
    COMBINED = auto()

    @property
    def is_calendar_clock(self):
        return self in (self.CALENDAR, self.COMBINED)

    @property
    def is_transaction_clock(self):
        return self in (self.TRANSACTION, self.COMBINED)
