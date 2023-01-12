import pytest
from django_fsm import TransitionNotAllowed

from common.tests import factories
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import PackagedWorkBasketDuplication
from publishing.models import PackagedWorkBasketInvalidCheckStatus
from publishing.models import ProcessingState
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
    with pytest.raises(PackagedWorkBasketDuplication):
        factories.PackagedWorkBasketFactory(workbasket=packaged_work_basket.workbasket)


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""

    editing_workbasket = factories.WorkBasketFactory(
        status=WorkflowStatus.EDITING,
    )
    with pytest.raises(PackagedWorkBasketInvalidCheckStatus):
        factories.PackagedWorkBasketFactory(workbasket=editing_workbasket)


def test_success_processing_transition():
    factories.PackagedWorkBasketFactory()

    packaged_work_basket = PackagedWorkBasket.objects.get(position=1)
    assert packaged_work_basket.position == 1
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING

    packaged_work_basket.begin_processing()
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )

    packaged_work_basket.processing_succeeded()
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED
    )


def test_begin_processing_transition_invalid_position():
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().last()
    assert packaged_work_basket.position == PackagedWorkBasket.objects.max_position()
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    with pytest.raises(TransitionNotAllowed):
        packaged_work_basket.begin_processing()


def test_begin_processing_transition_invalid_start_state():
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    # Begin processing the first instance in the queue.
    packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().first()
    assert packaged_work_basket.position == 1
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    packaged_work_basket.begin_processing()
    assert packaged_work_basket.position == 0
    assert (
        packaged_work_basket.pk == PackagedWorkBasket.objects.currently_processing().pk
    )

    # Try to start processing what is now the first instance in the queue,
    # which should fail - only one instance may be processed at any time.
    next_packaged_work_basket = PackagedWorkBasket.objects.awaiting_processing().first()
    assert (
        next_packaged_work_basket.position == PackagedWorkBasket.objects.max_position()
    )
    assert (
        next_packaged_work_basket.processing_state
        == ProcessingState.AWAITING_PROCESSING
    )
    with pytest.raises(TransitionNotAllowed):
        next_packaged_work_basket.begin_processing()


def test_abandon_transition():
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    assert packaged_work_basket.processing_state == ProcessingState.AWAITING_PROCESSING
    assert packaged_work_basket.position > 0
    packaged_work_basket.abandon()
    assert packaged_work_basket.processing_state == ProcessingState.ABANDONED
    assert packaged_work_basket.position == 0


def test_abandon_transition_from_invalid_state():
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    packaged_work_basket.begin_processing()
    assert packaged_work_basket.processing_state == ProcessingState.CURRENTLY_PROCESSING
    assert packaged_work_basket.position == 0
    with pytest.raises(TransitionNotAllowed):
        packaged_work_basket.abandon()


def test_remove_from_queue():
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    assert packaged_work_basket.position > 0

    packaged_work_basket.remove_from_queue()
    assert packaged_work_basket.position == 0


def test_promote_to_top_position():
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    packaged_work_basket = PackagedWorkBasket.objects.last()
    assert packaged_work_basket.position == PackagedWorkBasket.objects.max_position()

    packaged_work_basket.promote_to_top_position()
    assert packaged_work_basket.position == 1
    assert PackagedWorkBasket.objects.filter(position=1).count() == 1


def test_promote_position():
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    initially_first = PackagedWorkBasket.objects.get(position=1)
    initially_second = PackagedWorkBasket.objects.get(position=2)
    initially_second.promote_position()
    initially_first.refresh_from_db()
    assert initially_first.position == 2
    assert initially_second.position == 1


def test_demote_position():
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    initially_first = PackagedWorkBasket.objects.get(position=1)
    initially_second = PackagedWorkBasket.objects.get(position=2)
    initially_first.demote_position()
    initially_second.refresh_from_db()
    assert initially_first.position == 2
    assert initially_second.position == 1


def test_pause_and_unpause_queue(unpause_queue):
    assert not OperationalStatus.is_queue_paused()
    OperationalStatus.pause_queue(user=None)
    assert OperationalStatus.is_queue_paused()
    OperationalStatus.unpause_queue(user=None)
    assert not OperationalStatus.is_queue_paused()
