import pytest

from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import override_current_transaction
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def assert_path_returns():
    def check(source, path, expected):
        approved = TransactionPartition.approved_partitions()
        for model in (source, *expected):
            assert model.transaction.partition in approved

        with override_current_transaction(Transaction.approved.last()):
            path_result = source.get_versions().current().follow_path(path)
            assert set(expected) == set(path_result)

    return check


def test_follow_path_with_foreign_key(assert_path_returns):
    description = factories.TestModelDescription1Factory.create()
    model = description.described_record

    assert_path_returns(description, "described_record", {model})


def test_follow_path_with_multiple_foreign_keys(assert_path_returns):
    condition_component = factories.MeasureConditionComponentFactory.create()
    measure = condition_component.condition.dependent_measure

    assert_path_returns(condition_component, "condition__dependent_measure", {measure})


def test_follow_path_with_reverse_foreign_key(assert_path_returns):
    descripiton = factories.TestModelDescription1Factory.create()
    model = descripiton.described_record

    assert_path_returns(model, "descriptions", {descripiton})


def test_follow_path_with_many_to_many_through(assert_path_returns):
    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create()
    measure = exclusion.modified_measure
    another = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure=measure,
    )

    assert_path_returns(
        measure,
        "exclusions__excluded_geographical_area",
        {
            exclusion.excluded_geographical_area,
            another.excluded_geographical_area,
        },
    )


def test_follow_path_with_many_to_many_auto(assert_path_returns):
    obj = factories.QuotaOrderNumberFactory.create(required_certificates=True)
    cert = obj.required_certificates.first()

    assert_path_returns(obj, "required_certificates", {cert})


def test_published_transaction_queryset():
    """Test that the TransactionQuerySet.published() custom filter only returns
    Transactions that are approved and associated with a workbasket that has
    been published."""

    editing_workbasket = factories.EditingWorkBasketFactory()
    queued_workbasket = factories.QueuedWorkBasketFactory()
    published_workbasket = factories.PublishedWorkBasketFactory()

    published_tranx = Transaction.objects.published()
    published_tranx_ids = published_tranx.values_list("id", flat=True)

    assert published_tranx.count() == published_workbasket.transactions.count()
    assert set(published_tranx_ids) == set(
        published_workbasket.transactions.values_list("id", flat=True),
    )
    assert not (
        set(published_tranx_ids).intersection(
            set(queued_workbasket.transactions.values_list("id", flat=True)),
        )
    )
    assert not (
        set(published_tranx_ids).intersection(
            set(editing_workbasket.transactions.values_list("id", flat=True)),
        )
    )
