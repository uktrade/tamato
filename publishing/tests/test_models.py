import pytest

from common.tests import factories
from publishing import models
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_create():
    """Test multiple PackagedWorkBasket instances creation is managed
    correctly."""

    first_packaged_work_basket = factories.PackagedWorkBasket()
    second_packaged_work_basket = factories.PackagedWorkBasket()
    assert first_packaged_work_basket.position > 0
    assert second_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_create_duplicate_awaiting_instances():
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""

    packaged_work_basket = factories.PackagedWorkBasket()
    with pytest.raises(models.PackagedWorkBasketDuplication):
        factories.PackagedWorkBasket(workbasket=packaged_work_basket.workbasket)


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""

    editing_workbasket = factories.WorkBasketFactory(
        status=WorkflowStatus.EDITING,
    )
    with pytest.raises(models.PackagedWorkBasketInvalidCheckStatus):
        factories.PackagedWorkBasket(workbasket=editing_workbasket)
