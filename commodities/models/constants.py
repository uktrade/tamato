"""Includes constants and enumerators for use in commodities models."""
from enum import Enum

SUFFIX_DECLARABLE = "80"


class TreeNodeRelation(Enum):
    """Provides an enumeration for commodity relation attributes."""

    PARENT = "parent"
    SIBLINGS = "siblings"
    CHILDREN = "children"
    ANCESTORS = "ancestors"
    DESCENDANTS = "descendants"
