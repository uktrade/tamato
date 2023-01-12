"""
Pytest config for publishing module.

Note that a mocked Celery delay() fixture,
mocked_create_xml_envelope_file_delay(), is applied to all tests in this
module/app.
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import pytest

from common.tests import factories
from publishing.models import QueueState


@pytest.fixture()
def pause_queue():
    return factories.OperationalStatusFactory(
        created_by=None,
        queue_state=QueueState.PAUSED,
    )


@pytest.fixture()
def unpause_queue():
    return factories.OperationalStatusFactory(
        created_by=None,
        queue_state=QueueState.UNPAUSED,
    )


@pytest.fixture(scope="module", autouse=True)
def mocked_create_xml_envelope_file_delay():
    """Mock the Celery delay() function on
    `publishing.tasks.create_xml_envelope_file` so that a Celery worker is never
    actually needed."""

    with patch(
        "publishing.tasks.create_xml_envelope_file.delay",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ) as mocked_delay:
        yield mocked_delay
