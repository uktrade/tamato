from datetime import date
from typing import List

from celery import group
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import F
from django.db.transaction import atomic

from checks.models import MissingMeasureCommCode
from checks.models import MissingMeasuresCheck
from checks.tasks import check_transaction
from checks.tasks import check_transaction_sync
from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from commodities.models.orm import GoodsNomenclature
from common.celery import app
from common.models import Transaction
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from measures.models.tracked_models import Measure
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

# Celery logger adds the task id and status and outputs via the worker.
logger = get_task_logger(__name__)


@shared_task
@atomic
def transition(instance_id: int, state: str, *args):
    """
    Runs the named state transition on the passed workbasket instance.

    The task will fail if the transition raises any exception and the state
    transition will not be applied. Any extra arguments passed to the task will
    be passed along to the transition function.
    """
    instance = WorkBasket.objects.get(pk=instance_id)
    getattr(instance, state)(*args)
    instance.save()
    logger.info("Transitioned workbasket %s to state %s", instance_id, instance.status)


@app.task(bind=True)
def check_workbasket(self, workbasket_id: int):
    """Run and record transaction checks for the passed workbasket ID,
    asynchronously."""

    workbasket: WorkBasket = WorkBasket.objects.get(pk=workbasket_id)
    transactions = workbasket.transactions.values_list("pk", flat=True)

    logger.debug("Setup task to check workbasket %s", workbasket_id)
    return self.replace(group(check_transaction.si(id) for id in transactions))


def check_workbasket_sync(workbasket: WorkBasket):
    """
    Run and record transaction checks for the passed workbasket ID,
    synchronously.

    This method will run all of the checks one after the other and won't return
    until they are complete. This is useful for testing and debugging.
    """
    transactions = workbasket.transactions.all()

    logger.debug(
        "Start synchronous check of workbasket %s with % transactions",
        workbasket.pk,
        transactions.count(),
    )
    for transaction in transactions:
        check_transaction_sync(transaction)


@app.task(bind=True)
def call_check_workbasket_sync(self, workbasket_id: int):
    workbasket: WorkBasket = WorkBasket.objects.get(pk=workbasket_id)
    workbasket.delete_checks()
    check_workbasket_sync(workbasket)


@atomic
def promote_item_to_top(promoted_item, workbasket_transactions):
    """Set the transaction order of `promoted_measure` to be first in the
    workbasket, demoting the transactions that came before it."""

    top_transaction = workbasket_transactions.first()

    if not promoted_item or not top_transaction or promoted_item == top_transaction:
        return

    current_position = promoted_item.order
    top_position = top_transaction.order
    workbasket_transactions.filter(order__lt=current_position).update(
        order=F("order") + 1,
    )
    promoted_item.order = top_position
    promoted_item.save(update_fields=["order"])


@atomic
def end_objects(objects, workbasket):
    """Iterate through a queryset of objects on commodities, end-date those
    which have already began and delete those which have not yet started."""
    for object in objects:
        workbasket_transactions = Transaction.objects.filter(
            workbasket=workbasket,
            workbasket__status=WorkflowStatus.EDITING,
        ).order_by("order")
        commodity = (
            GoodsNomenclature.objects.all()
            .filter(
                sid=object.goods_nomenclature.sid,
                transaction__workbasket=workbasket,
            )
            .last()
        )
        if object.valid_between.lower > min(
            date.today(),
            commodity.valid_between.upper,
        ):
            logger.info(f"Deleting object {type(object)} - {object.pk}")
            new_version = object.new_version(
                workbasket=workbasket,
                update_type=UpdateType.DELETE,
            )
        else:
            logger.info(f"End dating object {type(object)} - {object.pk}")
            new_version = object.new_version(
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                valid_between=TaricDateRange(
                    object.valid_between.lower,
                    commodity.valid_between.upper,
                ),
            )
        promote_item_to_top(new_version.transaction, workbasket_transactions)


@atomic
def delete_objects(objects, workbasket):
    """Iterate through a queryset of tracked models on deleted commodities and
    delete them."""
    for object in objects:
        workbasket_transactions = Transaction.objects.filter(
            workbasket=workbasket,
            workbasket__status=WorkflowStatus.EDITING,
        ).order_by("order")

        logger.info(f"Deleting object {type(object)} - {object.pk}")
        new_version = object.new_version(
            workbasket=workbasket,
            update_type=UpdateType.DELETE,
        )

        promote_item_to_top(new_version.transaction, workbasket_transactions)


@app.task
def call_end_measures(
    measure_pks,
    footnote_association_pks,
    objects_to_delete_pks,
    workbasket_pk,
):
    """Calls end_objects for measures and footnote associations."""
    workbasket = WorkBasket.objects.all().get(pk=workbasket_pk)
    measures = Measure.objects.all().filter(pk__in=measure_pks)
    footnote_associations = FootnoteAssociationGoodsNomenclature.objects.all().filter(
        pk__in=footnote_association_pks,
    )
    objects_to_delete = TrackedModel.objects.all().filter(pk__in=objects_to_delete_pks)
    logger.info(f"Calling end objects for measures")
    end_objects(measures, workbasket)
    logger.info(f"Calling end objects for footnote associations")
    end_objects(footnote_associations, workbasket)
    logger.info(f"Calling delete objects for measures and footnote associations")
    delete_objects(objects_to_delete, workbasket)


def check_comm_code_for_missing_measures(
    tx_pk: int,
    comm_code_pk: int,
    index: int,
    total_num: int,
    missing_measures_check,
):
    code = GoodsNomenclature.objects.get(pk=comm_code_pk)

    logger.info(f"Checking commodity {code.item_id}")
    logger.info(
        f"Progress: {index + 1} out of {total_num}",
    )

    if code.item_id.startswith("99") or code.item_id.startswith("98"):
        logger.info(f"Chapters 98 and 99 are exempt. Skipping.")
        return MissingMeasureCommCode.objects.create(
            commodity=code,
            missing_measures_check=missing_measures_check,
            successful=True,
        )

    if code.valid_between.upper and code.valid_between.upper < date.today():
        logger.info(f"Commodity validity has ended. Skipping.")
        return MissingMeasureCommCode.objects.create(
            commodity=code,
            missing_measures_check=missing_measures_check,
            successful=True,
        )

    tx = Transaction.objects.get(pk=tx_pk)

    applicable_measures = get_measures_on_declarable_commodities(
        tx,
        code.item_id,
        None,
    )

    if not applicable_measures:
        logger.info(
            f"Commodity {code.item_id} has no applicable measures of any type!",
        )
        return MissingMeasureCommCode.objects.create(
            commodity=code,
            missing_measures_check=missing_measures_check,
            successful=False,
        )

    # check for 103 and 105 measure types
    filtered_measures = applicable_measures.filter(
        measure_type__sid__in=[103, 105],
        geographical_area=GeographicalArea.objects.erga_omnes().first(),
    )

    if not filtered_measures:
        logger.info(
            f"Commodity {code.item_id} has no applicable measures of type 103 or 105!",
        )
        return MissingMeasureCommCode.objects.create(
            commodity=code,
            missing_measures_check=missing_measures_check,
            successful=False,
        )

    logger.info(
        f"Commodity {code.item_id} has {filtered_measures.count()} applicable type 103 and/or 105 measure(s)",
    )
    return MissingMeasureCommCode.objects.create(
        commodity=code,
        missing_measures_check=missing_measures_check,
        successful=True,
    )


def create_missing_measure_comm_codes(
    tx_pk: int,
    comm_code_pks: List[int],
    total_num: int,
    missing_measures_check,
):
    for i, pk in enumerate(comm_code_pks):
        check_comm_code_for_missing_measures(
            tx_pk,
            pk,
            i,
            total_num,
            missing_measures_check,
        )


@app.task
def check_workbasket_for_missing_measures(
    workbasket_id: int,
    tx_pk: int,
    comm_code_pks: List[int],
):
    logger.info(
        f"Checking workbasket {workbasket_id} for missing measures on updated commodity codes",
    )
    all_commodities = GoodsNomenclature.objects.filter(pk__in=comm_code_pks)
    workbasket: WorkBasket = WorkBasket.objects.get(pk=workbasket_id)
    logger.info(
        f"Deleting previous missing measure checks from workbasket {workbasket_id}",
    )
    workbasket.delete_missing_measure_comm_codes()

    missing_measures_check = getattr(workbasket, "missing_measures_check", None)
    if missing_measures_check is None:
        missing_measures_check = MissingMeasuresCheck.objects.create(
            workbasket=workbasket,
        )

    create_missing_measure_comm_codes(
        tx_pk,
        comm_code_pks,
        all_commodities.count(),
        missing_measures_check,
    )

    missing_measures_check.successful = (
        workbasket.missing_measure_comm_codes.filter(successful=False).count() == 0
    )
    missing_measures_check.hash = workbasket.commodity_measure_changes_hash

    missing_measures_check.save()
