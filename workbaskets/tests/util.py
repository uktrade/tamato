from workbaskets.models import WorkBasket
from workbaskets.tasks import check_workbasket_sync


def assert_workbasket_valid(workbasket: WorkBasket):
    check_workbasket_sync(workbasket)
    assert not workbasket.unchecked_or_errored_transactions.exists()
