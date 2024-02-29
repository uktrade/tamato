from unittest.mock import ANY
from unittest.mock import patch

import pytest

from measures.models import MeasuresBulkCreator
from measures.models import ProcessingState

pytestmark = pytest.mark.django_db


def test_schedule_task_bulk_measures_create(
    simple_measures_bulk_creator,
    mocked_schedule_apply_async,
):
    """Test that calling MeasuresBulkCreator.shedule() correctly schedules a
    Celery task."""

    simple_measures_bulk_creator.schedule_task()

    mocked_schedule_apply_async.assert_called_once_with(
        kwargs={
            "measures_bulk_creator_pk": simple_measures_bulk_creator.pk,
        },
        countdown=ANY,
    )


def test_REVOKE_TASKS_AND_SET_NULL(
    simple_measures_bulk_creator,
    mocked_schedule_apply_async,
):
    """Test that deleting an object, referenced by a ForeignKey field that has
    `on_delete=BulkProcessor.REVOKE_TASKS_AND_SET_NULL`, correctly revokes any
    associated Celery task on the owning object."""

    # mocked_schedule_apply_async used to set `task_id` down in the call to
    # `schedule_task()`, which is necessary for testing revocation of the Celery
    # task.
    simple_measures_bulk_creator.schedule_task()

    with patch(
        "common.celery.app.control.revoke",
    ) as revoke_mock:
        simple_measures_bulk_creator.current_transaction.delete()

        revoke_mock.assert_called()


def test_cancel_task(
    simple_measures_bulk_creator,
    mocked_schedule_apply_async,
):
    """Test BulkProcessor.cancel_task() behaviours correctly apply."""

    simple_measures_bulk_creator.cancel_task()
    # Direct modification of processing_state prevents use of
    # Model.refresh_from_db() to get the latest, updated state.
    updated_1_measures_bulk_creator = MeasuresBulkCreator.objects.get(
        pk=simple_measures_bulk_creator.pk,
    )

    assert updated_1_measures_bulk_creator.processing_state == ProcessingState.CANCELLED

    # Multiple cancels shouldn't error.
    updated_1_measures_bulk_creator.cancel_task()
    updated_2_measures_bulk_creator = MeasuresBulkCreator.objects.get(
        pk=simple_measures_bulk_creator.pk,
    )

    assert updated_2_measures_bulk_creator.processing_state == ProcessingState.CANCELLED
