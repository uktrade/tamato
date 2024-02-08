import pytest

from checks.models import TransactionCheck
from checks.tests.factories import TrackedModelCheckFactory


@pytest.mark.django_db()
def test_timestamp_migration(migrator):
    migrator.reset()
    old_state = migrator.apply_initial_migration(
        (
            "checks",
            "0006_auto_20231211_1642",
        ),
    )
    migrator.apply_tested_migration(
        (
            "tests",
            "0003_auto_20210714_1522",
        ),
    )
    tracked_model_check_1 = TrackedModelCheckFactory.create(
        transaction_check__completed=True,
        transaction_check__successful=True,
        successful=True,
    )

    transaction_check = TransactionCheck.objects.get(
        pk=tracked_model_check_1.transaction_check.transaction.pk,
    )

    migrator.apply_tested_migration(
        (
            "checks",
            "0007_transactioncheck_timestamps",
        ),
    )

    new_transaction_check = TransactionCheck.objects.get(pk=transaction_check.pk)
    assert new_transaction_check.completed == True
    assert new_transaction_check.successful == False
    assert new_transaction_check.created_at == tracked_model_check_1.created_at
    assert new_transaction_check.updated_at >= tracked_model_check_1.updated_at

    migrator.reset()
