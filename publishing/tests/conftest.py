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
from publishing.models import PackagedWorkBasket
from publishing.models import QueueState
from publishing.models.state import CrownDependenciesPublishingState


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


@pytest.fixture()
def pause_publishing():
    return factories.CrownDependenciesPublishingOperationalStatusFactory(
        created_by=None,
        publishing_state=CrownDependenciesPublishingState.PAUSED,
    )


@pytest.fixture()
def unpause_publishing():
    return factories.CrownDependenciesPublishingOperationalStatusFactory(
        created_by=None,
        publishing_state=CrownDependenciesPublishingState.UNPAUSED,
    )


@pytest.fixture()
def mocked_publishing_models_send_emails_delay():
    with patch(
        "notifications.tasks.send_emails.delay",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ) as mocked_delay:
        yield mocked_delay


@pytest.fixture(scope="module", autouse=True)
def mocked_create_xml_envelope_file_apply_sync():
    """Mock the Celery delay() function on
    `publishing.tasks.create_xml_envelope_file` so that a Celery worker is never
    actually needed."""

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ) as mocked_apply_sync:
        yield mocked_apply_sync


@pytest.fixture(scope="function")
def packaged_workbasket_factory(queued_workbasket_factory):
    """
    Factory fixture to create a packaged workbasket.

    params:
    workbasket defaults to queued_workbasket_factory() which creates a
    Workbasket in the state QUEUED with an approved transaction and tracked models
    """

    def factory_method(workbasket=None, **kwargs):
        if not workbasket:
            workbasket = queued_workbasket_factory()
        with patch(
            "publishing.tasks.create_xml_envelope_file.apply_async",
            return_value=MagicMock(id=factory.Faker("uuid4")),
        ):
            packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
                workbasket=workbasket, **kwargs
            )
        return packaged_workbasket

    return factory_method


@pytest.fixture(scope="function")
def published_envelope_factory(packaged_workbasket_factory, envelope_storage):
    """
    Factory fixture to create an envelope and update the packaged_workbasket
    envelope field.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(packaged_workbasket=None, **kwargs):
        if not packaged_workbasket:
            packaged_workbasket = packaged_workbasket_factory()

        with patch(
            "publishing.storages.EnvelopeStorage.save",
            wraps=MagicMock(side_effect=envelope_storage.save),
        ) as mock_save:
            envelope = factories.PublishedEnvelopeFactory(
                packaged_work_basket=packaged_workbasket,
                **kwargs,
            )
            mock_save.assert_called_once()

        packaged_workbasket.envelope = envelope
        packaged_workbasket.save()
        return envelope

    return factory_method


@pytest.fixture(scope="function")
def successful_envelope_factory(published_envelope_factory):
    """
    Factory fixture to create a successfully processed envelope and update the
    packaged_workbasket envelope field.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(**kwargs):
        envelope = published_envelope_factory(**kwargs)

        packaged_workbasket = PackagedWorkBasket.objects.get(
            envelope=envelope,
        )

        packaged_workbasket.begin_processing()
        assert packaged_workbasket.position == 0
        assert (
            packaged_workbasket.pk
            == PackagedWorkBasket.objects.currently_processing().pk
        )
        packaged_workbasket.processing_succeeded()
        packaged_workbasket.save()
        assert packaged_workbasket.position == 0
        return envelope

    return factory_method


@pytest.fixture(scope="function")
def crown_dependencies_envelope_factory(successful_envelope_factory):
    """
    Factory fixture to create a crown dependencies envelope.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(**kwargs):
        envelope = successful_envelope_factory(**kwargs)

        packaged_workbasket = PackagedWorkBasket.objects.get(
            envelope=envelope,
        )
        return factories.CrownDependenciesEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
        )

    return factory_method
