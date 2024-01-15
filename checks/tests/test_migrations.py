# test transaction checks

# create tracked model, transaction, workbasket, tracked model check and transaction check
# create a workbasket in published, editing, queued
# apply 0006
# check transaction check datetime
# apply 0007
# check transaction check incompletful, unsuccessful and equal to tracked model checl

from datetime import date

import pytest

from checks.models import TransactionCheck
from checks.tests.factories import TrackedModelCheckFactory
from checks.tests.factories import TransactionCheckFactory
from common.tests import factories
from workbaskets.validators import WorkflowStatus


@pytest.mark.django_db()
def test_timestamp_migration(migrator):
    migrator.reset()
    old_state = migrator.apply_initial_migration(
        (
            "checks",
            "0006_auto_20231211_1642",
        ),
    )

    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    transaction = factories.TransactionFactory.create(workbasket=workbasket)
    trked_1 = factories.FootnoteTypeFactory.create(transaction=transaction)
    trked_2 = factories.FootnoteTypeFactory.create(transaction=transaction)

    tracked_models = workbasket.tracked_models.all()
    txn_check = TransactionCheckFactory.create(
        transaction=transaction,
        completed=True,
        successful=True,
        tracked_model_count=len(tracked_models),
    )
    tracked_model_check_1 = TrackedModelCheckFactory.create(
        transaction_check__transaction=transaction,
        model=trked_1,
        successful=True,
    )
    tracked_model_check_2 = TrackedModelCheckFactory.create(
        transaction_check__transaction=transaction,
        model=trked_2,
        successful=True,
    )

    # migrator.apply_tested_migration(
    #     (
    #         "checks",
    #         "0006_auto_20231211_1642",
    #     ),
    # )
    transaction_check = TransactionCheck.objects.get(pk=txn_check.pk)
    assert txn_check.created_at == date.fromtimestamp(000000000)
    # assert transaction_check.created_at == date.fromtimestamp(000000000)

    migrator.apply_tested_migration(
        (
            "checks",
            "0007_transactioncheck_timestamp",
        ),
    )

    new_transaction_check = TransactionCheck.objects.get(pk=txn_check.pk)
    assert new_transaction_check.completed == True
    assert new_transaction_check.successful == False
    assert new_transaction_check.created_at == tracked_model_check_1.created_at
    assert new_transaction_check.updated_at == tracked_model_check_2.updated_at

    migrator.reset()
