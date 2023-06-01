from datetime import datetime

from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from commodities.tasks import run_batch_task
from importer.management.commands.chunk_taric import chunk_taric
from importer.management.commands.chunk_taric import setup_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from measures.snapshots import MeasureSnapshot


def get_measures_on_declarable_commodities(transaction, item_id, date=None):
    """Uses CommodityTreeSnapshot and MeasureSnapshot to look up the commodity
    tree to find measures defined on parent commodities that therefore also
    apply to the given child commodity."""
    prefix = item_id[0:2]
    commodities_collection = CommodityCollectionLoader(prefix=prefix).load()

    moment = SnapshotMoment(transaction=transaction, date=date)
    tree = CommodityTreeSnapshot(
        commodities=commodities_collection.commodities,
        moment=moment,
    )
    this_commodity = list(
        filter(lambda c: c.item_id == item_id, tree.commodities),
    )[0]
    measure_snapshot = MeasureSnapshot(moment, tree)
    return measure_snapshot.get_applicable_measures(this_commodity)


def placeholder_clamav_check():
    return True


def placeholder_preflight_checks():
    return True


def placeholder_uk_changes_check(result=True):
    return result


def handle_batch(taric_file, user):
    now = datetime.now()
    current_time = now.strftime("%H%M%S")

    batch = setup_batch(
        batch_name=f"{taric_file.name}_{current_time}",
        author=user,
        dependencies=[],
        split_on_code=False,
    )
    return batch


def process_imported_taric_file(
    taric_file,
    user,
    workbasket_id=None,
):
    # run the validation check
    if placeholder_clamav_check():
        batch = handle_batch(taric_file, user)

        # Send file to S3 bucket
    else:
        # There was a discussion about not outing a virus check fail in order to prevent brute force attacks?
        raise Exception(
            f"ERROR: '{taric_file.name}' failed to import. Please report to Data Engineers.",
        )

    # Carry on with processing file
    if placeholder_preflight_checks() and placeholder_uk_changes_check():
        record_group = TARIC_RECORD_GROUPS["commodities"]
        chunk_taric(taric_file, batch, record_group)

        # Kick off celery task to run_batch.
        run_batch_task(
            batch,
            user,
            record_group,
            workbasket_id,
        )
