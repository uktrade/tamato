import pytest

from common.tests import factories
from publishing.models import QueueState


@pytest.fixture()
def pause_queue():
    return factories.OperationalStatusFactory(
        queue_state=QueueState.PAUSED,
    )


@pytest.fixture()
def unpause_queue():
    return factories.OperationalStatusFactory(
        queue_state=QueueState.UNPAUSED,
    )
