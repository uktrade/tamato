import pytest

from workbaskets.models import WorkBasket


def assert_workbasket_valid(workbasket: WorkBasket):
    # TODO - port the ideas in this test to the new business checking system.
    pytest.fail()
    #
    # check_workbasket_sync(workbasket)
    # assert not workbasket.unchecked_or_errored_transactions.exists()
