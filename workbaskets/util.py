from django.db import transaction

from importer.nursery import get_nursery


@transaction.atomic
def clear_workbasket(workbasket):
    """
    Deletes all objects connected to the workbasket while preserving the
    workbasket itself.

    Due to the DB relations this has to be done in a specific order.

    - First the Tracked Models must be deleted in reverse order.
        - As these are deleted their VersionGroups must be deleted
          or reset to have the previous version as current.
        - Also if any of these exist within the cache they must
          be removed from the cache.
    - Second Transactions are deleted.
    """
    nursery = get_nursery()

    for obj in workbasket.tracked_models.order_by("-pk"):
        version_group = obj.version_group
        obj.delete()
        nursery.remove_object_from_cache(obj)
        if version_group.versions.count() == 0:
            version_group.delete()
        else:
            version_group.current_version = version_group.versions.order_by(
                "-pk",
            ).first()
            version_group.save()

    workbasket.transactions.all().delete()


@transaction.atomic
def delete_workbasket(workbasket):
    """Deletes all objects connected to the workbasket and the workbasket
    itself."""
    clear_workbasket(workbasket)
    workbasket.delete()
