import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_local_export_task_ignores_unpublished_and_unapproved_transactions():
    """Only transactions that have been published should be included in the
    upload as draft and queued data may be sensitive and unpublished, and should
    therefore not be included."""
    factories.SeedFileTransactionFactory.create(order="999")
    transaction = factories.PublishedTransactionFactory.create(order="123")
    factories.ApprovedTransactionFactory.create(order="124")
    factories.UnapprovedTransactionFactory.create(order="125")
