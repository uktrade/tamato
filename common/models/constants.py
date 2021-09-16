"""Includes constants and enumerators for use in orm models."""
from enum import Enum
from enum import auto


class ClockType(Enum):
    """Provides an enumeration for clock types used in the Taric system."""

    CALENDAR = auto()
    TRANSACTION = auto()
