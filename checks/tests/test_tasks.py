import pytest
from pytest_django.asserts import assertQuerysetEqual  # type: ignore

pytestmark = pytest.mark.django_db

# TODO - see if the assertion here can be ported to the new business rule checking system.

# def create_checker(check, name: str, complete: bool, success: bool):
#     checker = factories.DummyChecker(name=name, success=success)
#
#     if complete:
#         factories.TrackedModelCheckFactory.create(
#             model=check.transaction.tracked_models.first(),
#             transaction_check=check,
#             check_name=name,
#             successful=success,
#         )
#
#     return checker
#
#
# @pytest.fixture(
#     params=(
#         (0, 0, 0, {"incomplete", "empty"}),
#         (0, 0, 0, {"incomplete"}),
#         (1, 0, 0, {"incomplete"}),
#         (1, 1, 1, {"incomplete"}),
#         (1, 1, 0, {"incomplete"}),
#         (2, 1, 1, {"incomplete"}),
#         (1, 1, 1, set()),
#     ),
#     ids=(
#         "check of transaction with no models",
#         "check of models with no checks",
#         "check of models with missing checks",
#         "check of models with successful checks",
#         "check of models with unsuccessful checks",
#         "check of models with some incomplete checks",
#         "check that is already completed",
#     ),
# )
# def check(request):
#     num_checks, num_completed, num_successful, traits = request.param
#     assert num_checks >= num_completed
#     assert num_completed >= num_successful
#
#     check = factories.TransactionCheckFactory.create(
#         **{trait: True for trait in traits}
#     )
#     check_names = [str(i) for i in range(num_checks)]
#     completes = repeat(True, num_completed)
#     successes = repeat(True, num_successful)
#
#     checkers = set(
#         create_checker(check, name, complete, successful)
#         for name, complete, successful in zip_longest(
#             check_names,
#             completes,
#             successes,
#             fillvalue=False,
#         )
#     )
#
#     assert check.model_checks.count() == num_completed
#     assert check.model_checks.filter(successful=True).count() == num_successful
#
#     with mock.patch("checks.tasks.applicable_to", new=lambda m: checkers):
#         yield check, num_checks, num_completed, num_successful
#
#
# def test_model_checking(check):
#     check, num_checks, num_completed, num_successful = check
#
#     model = check.transaction.tracked_models.first()
#     if model is None:
#         pytest.skip("No model to check")
#     tasks.check_model(model.id, check.id)
#
#     assert check.model_checks.count() == num_checks
#     assert check.model_checks.filter(successful=True).count() == num_successful


# def test_completion_of_transaction_checks(check):
#     check, num_checks, num_completed, num_successful = check
#     expect_completed = num_completed == num_checks
#     expect_successful = (num_successful == num_checks) if expect_completed else None
#
#     complete = tasks.is_transaction_check_complete(check.id)
#     assert complete == expect_completed
#
#     check.refresh_from_db()
#     assert check.completed == expect_completed
#     assert check.successful == expect_successful
#
#
# @pytest.mark.parametrize("check_already_exists", (True, False))
# def test_checking_of_transaction(check, check_already_exists):
#     check, num_checks, num_completed, num_successful = check
#     expect_completed = num_completed == num_checks
#     expect_successful = (num_successful == num_checks) if expect_completed else None
#     if expect_completed:
#         check.completed = True
#         check.successful = expect_successful
#         check.save()
#
#     transaction = check.transaction
#     if not check_already_exists:
#         check.delete()
#
#     # The task will replace itself with a new workflow. Testing this is hard.
#     # Instead, we will capture the new workflow and assert it is calling the
#     # right things. This is brittle but probably better than nothing.
#     with mock.patch("celery.app.task.Task.replace", new=lambda _, t: t):
#         workflow = tasks.check_transaction(transaction.id)  # type: ignore
#
#     check = TransactionCheck.objects.filter(transaction=transaction).get()
#     if expect_completed and check_already_exists:
#         # If the check is already done, it should be skipped.
#         assert workflow is None
#     else:
#         # If checks need to happen, the workflow should have one check task per
#         # model and finish with a decide task.
#         assert transaction.tracked_models.count() == len(workflow.tasks)
#         model_ids = set(transaction.tracked_models.values_list("id", flat=True))
#         for task in workflow.tasks:
#             model_id, context_id = task.args
#             model_ids.remove(model_id)
#             assert task.task == tasks.check_model.name
#             assert context_id == check.id
#
#         assert workflow.body.task == tasks.is_transaction_check_complete.name
#         assert workflow.body.args[0] == check.id
#
#
# def test_detecting_of_transactions_to_update():
#     head_transaction = common_factories.ApprovedTransactionFactory.create()
#
#     # Transaction with no check
#     no_check = common_factories.UnapprovedTransactionFactory.create()
#
#     # Transaction that does not require update
#     no_update = factories.TransactionCheckFactory.create(
#         head_transaction=head_transaction,
#     )
#     assert_requires_update(no_update, False)
#
#     # Transaction that requires update in DRAFT
#     draft_update = factories.StaleTransactionCheckFactory.create(
#         transaction__partition=TransactionPartition.DRAFT,
#         head_transaction=head_transaction,
#     )
#     assert_requires_update(draft_update, True)
#
#     # Transaction that requires update in REVISION
#     revision_update = factories.StaleTransactionCheckFactory.create(
#         transaction__partition=TransactionPartition.REVISION,
#         transaction__order=-(head_transaction.order),
#         head_transaction=head_transaction,
#     )
#     assert_requires_update(revision_update, True)
#
#     expected_transaction_ids = {no_check.id, draft_update.transaction.id}
#
#     # The task will replace itself with a new workflow. Testing this is hard.
#     # Instead, we will capture the new workflow and assert it is calling the
#     # right things. This is brittle but probably better than nothing.
#     with mock.patch("celery.app.task.Task.replace", new=lambda _, t: t):
#         workflow = tasks.update_checks()  # type: ignore
#
#     assert set(t.task for t in workflow.tasks) == {tasks.check_transaction.name}
#     assert set(t.args[0] for t in workflow.tasks) == expected_transaction_ids
#
#
# @pytest.mark.parametrize("include_archived", [True, False])
# @pytest.mark.parametrize(
#     "transaction_partition", [TransactionPartition.DRAFT, TransactionPartition.REVISION]
# )
# def test_archived_workbasket_checks(include_archived, transaction_partition):
#     """
#     Verify transactions in ARCHIVED workbaskets do not require checking unless
#     include_archived is True.
#     """
#     head_transaction = common_factories.ApprovedTransactionFactory.create()
#
#     # Transaction that requires update in DRAFT or REVISION
#     transaction_check = factories.StaleTransactionCheckFactory.create(
#         transaction__partition=transaction_partition,
#         head_transaction=head_transaction,
#     )
#
#     all_checks = TransactionCheck.objects.filter(pk=transaction_check.pk)
#     initial_require_update = all_checks.requires_update(True, include_archived)
#
#     # Initially the transaction should require update.
#     assert initial_require_update.count() == 1
#     assert initial_require_update.get().pk == transaction_check.pk
#
#     # Set workbasket status to ARCHIVED and verify requires_update only returns their transaction checks if
#     # include_archived is True
#     transaction_check.transaction.workbasket.status = WorkflowStatus.ARCHIVED
#     transaction_check.transaction.workbasket.save()
#
#     checks_require_update = all_checks.requires_update(True, include_archived)
#
#     if include_archived:
#         assert checks_require_update.count() == 1
#         assert checks_require_update.get().pk == transaction_check.pk
#     else:
#         assert checks_require_update.count() == 0
