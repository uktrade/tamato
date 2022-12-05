import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_create():
    """Test multiple PackagedWorkBasket instances creation is managed
    correctly."""

    first_packaged_work_basket = factories.PackagedWorkBasket()
    second_packaged_work_basket = factories.PackagedWorkBasket()
    assert (
        first_packaged_work_basket.position == 1
        and second_packaged_work_basket.position == 2
    )


def test_create_duplicate_awaiting_instances():
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""
    # TODO


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""
    # TODO
