"""
Celery tasks and workflow.

Build a workflow of tasks in one go and to pass to celery.
"""
import logging
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple

from celery import chain
from celery import chord
from celery.utils.log import get_task_logger

from checks.checks import ALL_CHECKERS
from checks.checks import Checker
from checks.models import TrackedModelCheck
from common.business_rules import ALL_RULES
from common.business_rules import BusinessRule
from common.celery import app
from common.models.celerytask import ModelCeleryTask
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.models.utils import get_current_transaction
from workbaskets.models import WorkBasket

# Celery logger adds the task id and status and outputs via the worker.
logger = get_task_logger(__name__)

# Types for passing over celery
CheckerModelRule = Tuple[Checker, TrackedModel, Sequence[BusinessRule]]
"""CheckerModelRule stores a checker, model, and a sequence of rules to apply to it."""

ModelPKInterval = Tuple[int, int]
"""ModelPKInterval is a tuple of (first_pk, last_pk) referring to a contiguous range of TrackedModels"""

TaskInfo = Tuple[int, str]
"""TaskInfo is a tuple of (task_id, task_name) which can be used to create a ModelCeleryTask."""


# @app.task(trail=True)
# def check_model(
#     transaction_pk: int,
#     model_pk: int,
#     rule_names: Optional[Sequence[str]] = None,
#     bind_to_task_kwargs: Optional[Dict] = None,
# ):
#     """
#     Task to check one model against one business rule and record the result.
#
#     As this is a celery task, parameters are in base formats that can be serialised, such as int and str.
#
#     Run one business rule against one model, this is called as part of the check_models workflow.
#
#     By setting bind_to_task_uuid, the task will be bound to the celery task with the given UUID,
#     this is useful for tracking the progress of the parent task, and cancelling it if needed.
#     """
#     # XXXX - TODO, re-add note on timings, from Simons original code.
#
#     if rule_names is None:
#         rule_names = set(ALL_RULES.keys())
#
#     assert set(ALL_RULES.keys()).issuperset(rule_names)
#
#     transaction = Transaction.objects.get(pk=transaction_pk)
#     model = TrackedModel.objects.get(pk=model_pk)
#     successful = True
#
#     for checker in ALL_CHECKERS.values():
#         for checker_model, model_rules in checker.get_model_rule_mapping(
#             model,
#             rule_names,
#         ).items():
#             """get_model_rules will return a different model in the case of
#             LinkedModelChecker, so the model to check use checker_model."""
#             for rule in model_rules:
#                 logger.debug(
#                     "%s rule:  %s, tx: %s,  model: %s",
#                     checker.__name__,
#                     rule,
#                     transaction,
#                     model,
#                 )
#                 check_result = checker.apply_rule_cached(
#                     rule,
#                     transaction,
#                     checker_model,
#                 )
#                 if bind_to_task_kwargs:
#                     logger.debug(
#                         "Binding result %s to task.  bind_to_task_kwargs: %s",
#                         check_result.pk,
#                         bind_to_task_kwargs,
#                     )
#                     bind_model_task(check_result, **bind_to_task_kwargs)
#
#                 logger.info(
#                     f"Ran check %s %s",
#                     check_result,
#                     "✅" if check_result.successful else "❌",
#                 )
#                 successful &= check_result.successful
#
#     return successful


@app.task(trail=True)
def check_model(
    transaction_pk: int,
    model_pk: int,
    rule_names: Optional[Sequence[str]] = None,
    bind_to_task_kwargs: Optional[Dict] = None,
):
    """
    Task to check one model against one business rule and record the result.

    As this is a celery task, parameters are in base formats that can be serialised, such as int and str.

    Run one business rule against one model, this is called as part of the check_models workflow.

    By setting bind_to_task_uuid, the task will be bound to the celery task with the given UUID,
    this is useful for tracking the progress of the parent task, and cancelling it if needed.
    """
    # XXXX - TODO, re-add note on timings, from Simons original code.

    if rule_names is None:
        rule_names = set(ALL_RULES.keys())

    assert set(ALL_RULES.keys()).issuperset(rule_names)

    transaction = Transaction.objects.get(pk=transaction_pk)
    initial_model = TrackedModel.objects.get(pk=model_pk)

    successful = True

    for checker in ALL_CHECKERS.values():
        for model, rules in checker.get_model_rule_mapping(
            initial_model,
            rule_names,
        ).items():
            Checker.apply_rules(rules, transaction, model)

    return successful


@app.task(trail=True)
def check_models_workflow(
    pk_intervals: Sequence[ModelPKInterval],
    bind_to_task_kwargs: Optional[Dict] = None,
    rules: Optional[Sequence[str]] = None,
):
    """
    Celery Workflow group containing 'check_model_rule' tasks to run applicable
    rules from checkers on supplied models in parallel via a celery group.

    If checkers is None, then default to all applicable checkers
    (see get_model_rules)

    Models checked will be the exact model versions passed in,
    this is useful for caching checks, e.g. those of linked_models
    where an older model is referenced.

    Callers should ensure models passed in are the correct version,
    e.g. by using override_transaction.
    """
    logger.debug("Build check_models_workflow")

    models = TrackedModel.objects.from_pk_intervals(*pk_intervals)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Got %s models", models.count())

    return chord(
        check_model.si(
            model.transaction.pk,
            model.pk,
            rules,
            bind_to_task_kwargs,
        )
        for model in models
    )(unbind_model_tasks.si([bind_to_task_kwargs["celery_task_id"]]))


@app.task(trail=True)
def cancel_workbasket_checks(workbasket_pk: int):
    """Find existing celery tasks and, revoke them ande delete the
    ModelCeleryTask objects tracking them."""
    celery_tasks = (
        ModelCeleryTask.objects.filter(celery_task_name="check_workbasket")
        .update_task_statuses()
        .filter_by_task_kwargs(workbasket_pk=workbasket_pk)
        .distinct("celery_task_id")
    )
    # Terminate the existing tasks, using SIGUSR1 which triggers the soft timeout handler.
    celery_tasks.revoke(terminate=True, signal="SIGUSR1")


@app.task(trail=True)
def get_workbasket_model_pk_intervals(workbasket_pk: int):
    """
    Return a list of all models in the workbasket.

    Ordinarily this step doesn't take very long, though for the seed workbasket
    of 9 million items it may take around 6 seconds (measured on a consumer
    laptop [Ryzen 2500u, 32gb ram]).
    """
    workbasket = WorkBasket.objects.get(pk=workbasket_pk)
    pks = [*workbasket.tracked_models.as_pk_intervals()]
    return pks


@app.task(trail=True)
def unbind_model_tasks(task_ids: Sequence[str]):
    """Called at the end of a workflow, as there is no ongoing celery task
    associated with this data."""
    logger.debug("Task_ids: [%s]", task_ids)
    deleted = ModelCeleryTask.objects.filter(celery_task_id__in=task_ids).delete()
    logger.debug("Deleted %s ModelCeleryTask objects", deleted[0])


@app.task(bind=True, trail=True)
def check_workbasket(
    self,
    workbasket_pk: int,
    current_transaction_pk: Optional[int] = None,
    rules: Optional[Sequence[str]] = None,
    clear_cache=False,
):
    """
    Orchestration task, that kicks off a workflow to check all models in the
    workbasket.

    Cancels existing tasks if they are running, the system has caching which
    will help with overlapping checks, cancelling existing checks will help keep
    the celery queue clear of stale tasks, which is makes it easier to manage
    when the system is under load.

    :param workbasket_pk: pk of the workbasket to check
    :param current_transaction_pk: pk of the current transaction, defaults to the current highest transaction
    :param rules: specify rule names to check (defaults to ALL_RULES)  [mostly for testing/debugging]
    :param clear_cache: clear the cache before checking  [mostly for testing/debugging]
    """
    logger.debug(
        "check_workbasket, workbasket_pk: %s, current_transaction_pk %s, clear_cache %s",
        workbasket_pk,
        current_transaction_pk,
        clear_cache,
    )

    if clear_cache:
        # Clearing the cache should not be needed in the usual workflow, but may be useful e.g. if
        # business rules are updated and need to be re-run.
        TrackedModelCheck.objects.filter(
            model__transaction__workbasket__pk=workbasket_pk,
        ).delete()

    if current_transaction_pk is None:
        current_transaction_pk = (
            get_current_transaction() or Transaction.objects.last()
        ).pk

    # Use 'bind_to_task' to pass in the celery task id to associate this task and it's subtasks, while
    # the task is running, allowing them to be revoked if the underlying data changes or another copy
    # of the task is started.
    #
    # get_workbasket_model_pk_intervals gets tuples of (first_pk, last_pk), a compact form to
    # represent the trackedmodels in the workbasket, which is passed to the subtasks tasks.
    return chain(
        cancel_workbasket_checks.si(workbasket_pk),
        get_workbasket_model_pk_intervals.si(workbasket_pk),
        check_models_workflow.s(
            bind_to_task_kwargs={
                "celery_task_id": self.request.id,
                "celery_task_name": "check_workbasket",
            },
            rules=rules,
        ),
    )()


def check_workbasket_sync(workbasket: WorkBasket, clear_cache: bool = False):
    # Run the celery task and wait
    tx = get_current_transaction()
    result = check_workbasket.delay(workbasket.pk, tx.pk, clear_cache)
    result.wait()
