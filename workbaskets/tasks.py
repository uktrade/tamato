from celery import group
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from checks.tasks import check_transaction
from checks.tasks import check_transaction_sync
from common.celery import app
from workbaskets.models import WorkBasket

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
