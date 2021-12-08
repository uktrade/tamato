class NoIdentifyingValuesGivenError(Exception):
    """Raised when TrackedModelQuerySet.get_versions is called without model
    identifying fields as keyword arguments."""


class IllegalSaveError(Exception):
    """Raised when a TrackedModel instance is saved when it already exists in
    the database (and not a force-write)."""


class NoDescriptionError(Exception):
    """Raised when trying to fetch description model instances for a
    TrackedModel which has no associated descriptions."""
