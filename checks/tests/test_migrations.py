# test transaction checks

# create tracked model, transaction, workbasket, tracked model check and transaction check
# create a workbasket in published, editing, queued
# apply 0006
# check transaction check datetime
# apply 0007
# check transaction check incompletful, unsuccessful and equal to tracked model checl

from datetime import date

import pytest

from checks.tests.factories import TrackedModelCheckFactory
from checks.tests.factories import TransactionCheckFactory
from common.tests import factories
from workbaskets.validators import WorkflowStatus


@pytest.mark.django_db()
def test_timestamp_migration(migrator, setup_content_types):
    old_state = migrator.apply_initial_migration(
        (
            "checks",
            "0005_trackedmodelcheck_processing_time",
        ),
    )
    setup_content_types(old_state.apps)

    User = old_state.apps.get_model("auth", "User")
    WorkBasket = old_state.apps.get_model("workbaskets", "WorkBasket")
    # workbasket = factories.WorkBasketFactory.create(
    #     status=WorkflowStatus.EDITING,
    # )
    user = User.objects.create(username="testuser")
    workbasket = WorkBasket.objects.create(author=user, status=WorkflowStatus.EDITING)
    FootnoteType = old_state.apps.get_model("footnotes", "FootnoteType")
    # txn = factories.TransactionFactory.create(workbasket=workbasket)
    with factories.TransactionFactory.create(workbasket=workbasket) as transaction:
        # with workbasket.new_transaction() as transaction:
        trked_1 = FootnoteType.objects.create(transaction=transaction)
        trked_2 = FootnoteType.objects.create(transaction=transaction)
        txn = transaction

    tracked_models = workbasket.tracked_models.all()
    txn_check = TransactionCheckFactory.create(
        transaction=txn,
        completed=True,
        successful=True,
        tracked_model_count=len(tracked_models),
    )
    tracked_model_check_1 = TrackedModelCheckFactory.create(
        transaction_check__transaction=txn,
        model=trked_1,
        successful=True,
    )
    tracked_model_check_2 = TrackedModelCheckFactory.create(
        transaction_check__transaction=txn,
        model=trked_2,
        successful=True,
    )

    inner_state = migrator.apply_initial_migration(
        (
            "checks",
            "0006_auto_20231211_1642",
        ),
    )
    inner_transaction_check_class = inner_state.apps.get_model(
        "checks",
        "TransactionCheck",
    )
    transaction_check = inner_transaction_check_class.objects.get(pk=txn_check.pk)
    assert transaction_check.created_at == date.fromtimestamp(000000000)

    new_state = migrator.apply_initial_migration(
        (
            "checks",
            "0007_transactioncheck_timestamp",
        ),
    )

    transaction_check_class = new_state.apps.get_model("checks", "TransactionCheck")
    new_transaction_check = transaction_check_class.objects.get(pk=txn_check.pk)
    assert new_transaction_check.completed == True
    assert new_transaction_check.successful == False
    assert new_transaction_check.created_at == tracked_model_check_1.created_at
    assert new_transaction_check.updated_at == tracked_model_check_2.updated_at

    migrator.reset()
