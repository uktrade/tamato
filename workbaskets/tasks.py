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
from common.util import TaricDateRange
from common.validators import UpdateType
from measures.models.tracked_models import Measure
from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models.orm import GoodsNomenclature
from common.celery import app
from common.models import Transaction
from geo_areas.models import GeographicalArea
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
def promote_measure_to_top(promoted_measure, workbasket_transactions):
    """Set the transaction order of `promoted_measure` to be first in the
    workbasket, demoting the transactions that came before it."""

    top_transaction = workbasket_transactions.first()

    if (
        not promoted_measure
        or not top_transaction
        or promoted_measure == top_transaction
    ):
        return

    current_position = promoted_measure.order
    top_position = top_transaction.order
    workbasket_transactions.filter(order__lt=current_position).update(
        order=F("order") + 1,
    )
    promoted_measure.order = top_position
    promoted_measure.save(update_fields=["order"])


@atomic
def end_measures(measures, workbasket):
    """Iterate through measures on commodities, end-date those which have
    already began and delete those which have not yet started."""
    for measure in measures:
        workbasket_transactions = Transaction.objects.filter(
            workbasket=workbasket,
            workbasket__status=WorkflowStatus.EDITING,
        ).order_by("order")
        commodity = (
            GoodsNomenclature.objects.all()
            .filter(
                sid=measure.goods_nomenclature.sid,
                transaction__workbasket=workbasket,
            )
            .last()
        )
        if measure.valid_between.lower > min(
            date.today(),
            commodity.valid_between.upper,
        ):
            new_measure_version = measure.new_version(
                workbasket=workbasket,
                update_type=UpdateType.DELETE,
            )
        else:
            new_measure_version = measure.new_version(
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                valid_between=TaricDateRange(
                    measure.valid_between.lower,
                    commodity.valid_between.upper,
                ),
            )
        promote_measure_to_top(new_measure_version.transaction, workbasket_transactions)


@app.task
def call_end_measures(measure_pks, workbasket_pk):
    workbasket = WorkBasket.objects.all().get(pk=workbasket_pk)
    measures = Measure.objects.all().filter(pk__in=measure_pks)
    end_measures(measures, workbasket)


def get_comm_codes_with_missing_measures(tx_pk: int, comm_code_pks: List[int]):
    output = []

    for pk in comm_code_pks:
        code = GoodsNomenclature.objects.get(pk=pk)

        logger.info(f"Checking commodity {code.item_id}")

        if code.item_id.startswith("99") or code.item_id.startswith("98"):
            logger.info(f"Chapters 98 and 99 are exempt. Skipping.")
            continue

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
            output.append(code)
            continue

        filtered_measures = applicable_measures.filter(
            measure_type__sid=103,
            geographical_area=GeographicalArea.objects.erga_omnes().first(),
        )

        if not filtered_measures:
            logger.info(
                f"Commodity {code.item_id} has no applicable measures of type 103!",
            )
            output.append(code)

        logger.info(
            f"Commodity {code.item_id} has {filtered_measures.count()} applicable type 103 measure(s)",
        )

    return output


@app.task
def check_workbasket_for_missing_measures(
    workbasket_id: int,
    tx_pk: int,
    comm_code_pks: List[int],
):
    logger.info(
        f"Checking workbasket {workbasket_id} for missing measures on updated commodity codes",
    )
    commodities = get_comm_codes_with_missing_measures(tx_pk, comm_code_pks)
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

    missing_measures_check.successful = not bool(commodities)

    for commodity in commodities:
        MissingMeasureCommCode.objects.create(
            commodity=commodity,
            missing_measures_check=missing_measures_check,
        )

    missing_measures_check.save()
