import logging
from itertools import cycle

from celery import group

from checks.checks import applicable_to
from checks.models import TransactionCheck
from common.celery import app
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import override_current_transaction
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


@app.task(time_limit=60)
def check_model(trackedmodel_id: int, context_id: int):
    """
    Runs all of the applicable checkers on the passed model ID, and records the
    results.

    Model checks are expected (from observation) to be short – on the order of
    6-7 seconds max. So if the check is taking considerably longer than this, it
    is probably broken and should be killed to free up the worker.
    """

    model: TrackedModel = TrackedModel.objects.get(pk=trackedmodel_id)
    context: TransactionCheck = TransactionCheck.objects.get(pk=context_id)
    transaction = context.transaction

    with override_current_transaction(transaction):
        for check in applicable_to(model):
            if not context.model_checks.filter(
                model=model,
                check_name=check.name,
            ).exists():
                # Run the checker on the model and record the result. (This is
                # not Celery ``apply`` but ``Checker.apply``).
                check.apply(model, context)


@app.task
def is_transaction_check_complete(check_id: int) -> bool:
    """Checks and returns whether the given transaction check is complete, and
    records the success if so."""

    check: TransactionCheck = TransactionCheck.objects.get(pk=check_id)
    check.completed = True

    with override_current_transaction(check.transaction):
        for model in check.transaction.tracked_models.all():
            applicable_checks = set(check.name for check in applicable_to(model))
            performed_checks = set(
                check.model_checks.filter(model=model).values_list(
                    "check_name",
                    flat=True,
                ),
            )

            if applicable_checks != performed_checks:
                check.completed = False
                break

    if check.completed:
        check.successful = not check.model_checks.filter(successful=False).exists()
        logger.info("Completed checking transaction %s", check.transaction.id)

    check.save()
    return check.completed


def setup_or_resume_transaction_check(transaction: Transaction):
    """Return a current, fresh transaction check for the passed transaction ID
    and a list of model IDs that need to be checked."""

    head_transaction = Transaction.approved.last()

    existing_checks = TransactionCheck.objects.filter(
        transaction=transaction,
        head_transaction=head_transaction,
    )

    up_to_date_check = existing_checks.requires_update(False).filter(completed=True)
    if up_to_date_check.exists():
        return up_to_date_check.get(), []

    context = existing_checks.requires_update(False).filter(completed=False).last()
    if context is None:
        context = TransactionCheck(
            transaction=transaction,
            head_transaction=head_transaction,
        )
        context.save()

    return (
        context,
        transaction.tracked_models.values_list("pk", flat=True),
    )


@app.task(bind=True)
def check_transaction(self, transaction_id: int):
    """Run and record checks for the passed transaction ID, asynchronously."""

    transaction = Transaction.objects.get(pk=transaction_id)
    check, model_ids = setup_or_resume_transaction_check(transaction)
    if check.completed and not any(model_ids):
        logger.debug(
            "Skipping check of transaction %s "
            "because an up-to-date check already exists",
            transaction_id,
        )
        return

    # Create a workflow: firstly run all of the model checks (in parallel) and
    # then once they are all done see if the transaction check is now complete.
    logger.info("Beginning check of transaction %s", transaction_id)
    workflow = group(
        check_model.si(*args) for args in zip(model_ids, cycle([check.pk]))
    ) | is_transaction_check_complete.si(check.pk)

    # Execute the workflow by replacing this task with it.
    return self.replace(workflow)


def check_transaction_sync(transaction: Transaction):
    """
    Run and record checks for the passed transaction ID, syncronously.

    This method will run all of the checks one after the other and won't return
    until they are complete. This is useful for testing and debugging.
    """
    check, model_ids = setup_or_resume_transaction_check(transaction)
    if check.completed and not any(model_ids):
        logger.debug(
            "Skipping check of transaction %s "
            "because an up-to-date check already exists",
            transaction.pk,
        )
    else:
        logger.info("Beginning syncronous check of transaction %s", transaction.pk)
        for model_id in model_ids:
            check_model(model_id, check.pk)
        is_transaction_check_complete(check.pk)


@app.task(bind=True, rate_limit="1/m")
def update_checks(self):
    """Triggers checking for any transaction that requires an update.

    A rate limit is specified here to mitigate instances where this
    task stacks up and prevents other tasks from running by monopolising
    the worker.

    TODO: Ensure this task is *not* stacking up and blocking the worker!
    """

    ids_require_update = (
        Transaction.objects.exclude(
            pk__in=TransactionCheck.objects.requires_update(False).values(
                "transaction__pk",
            ),
        )
        .filter(partition=TransactionPartition.DRAFT)
        .values_list("pk", flat=True)
    )

    # Execute a check for each transaction that requires an update by replacing
    # this task with a parallel workflow.
    return self.replace(group(check_transaction.si(id) for id in ids_require_update))
