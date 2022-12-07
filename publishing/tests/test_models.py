import pytest

from common.tests import factories
from publishing import models
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_create():
    """Test multiple PackagedWorkBasket instances creation is managed
    correctly."""

    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
    second_packaged_work_basket = factories.PackagedWorkBasketFactory()
    assert first_packaged_work_basket.position > 0
    assert second_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_create_duplicate_awaiting_instances():
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""

    packaged_work_basket = factories.PackagedWorkBasketFactory()
    with pytest.raises(models.PackagedWorkBasketDuplication):
        factories.PackagedWorkBasketFactory(workbasket=packaged_work_basket.workbasket)


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""

    editing_workbasket = factories.WorkBasketFactory(
        status=WorkflowStatus.EDITING,
    )
    with pytest.raises(models.PackagedWorkBasketInvalidCheckStatus):
        factories.PackagedWorkBasketFactory(workbasket=editing_workbasket)


def test_begin_processing_transition():
    """TODO test successful transition conditions."""


def test_begin_processing_transition_invalid():
    """
    TODO test failed conditions:

    begin_processing_condition_at_position_1()
    begin_processing_condition_no_instances_currently_processing()
    """
