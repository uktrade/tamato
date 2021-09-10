"""Includes constants and enumerators for use in commodities models."""
from enum import Enum
from enum import auto

SUFFIX_DECLARABLE = "80"


class TreeNodeRelation(Enum):
    """Provides an enumeration for commodity relation attributes."""

    PARENT = "parent"
    SIBLINGS = "siblings"
    CHILDREN = "children"
    ANCESTORS = "ancestors"
    DESCENDANTS = "descendants"


class ClockType(Enum):
    """Provides an enumeration for clock types used in the Taric system."""

    CALENDAR = auto()
    TRANSACTION = auto()
