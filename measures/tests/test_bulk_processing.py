from unittest.mock import ANY
from unittest.mock import patch

import pytest

from measures.tests import factories

pytestmark = pytest.mark.django_db


def test_schedule_bulk_measures_create(
    user_empty_workbasket,
    approved_transaction,
    mocked_schedule_apply_async,
):
    """Test that calling MeasuresBulkCreator.shedule() correctly schedules a
    Celery task."""

    measures_bulk_creator = factories.MeasuresBulkCreatorFactory.create(
        form_data={},
        form_kwargs={},
        current_transaction=approved_transaction,
        workbasket=user_empty_workbasket,
    )
    measures_bulk_creator.schedule()

    mocked_schedule_apply_async.assert_called_once_with(
        kwargs={
            "measures_bulk_creator_pk": measures_bulk_creator.pk,
        },
        countdown=ANY,
    )


def test_REVOKE_TASKS_AND_SET_NULL(
    user_empty_workbasket,
    approved_transaction,
    mocked_schedule_apply_async,
):
    """Test that deleting an object, referenced by a ForeignKey field that has
    `on_delete=REVOKE_TASKS_AND_SET_NULL`, correctly revokes any associated
    Celery task on the owning object."""

    measures_bulk_creator = factories.MeasuresBulkCreatorFactory.create(
        form_data={},
        form_kwargs={},
        current_transaction=approved_transaction,
        workbasket=user_empty_workbasket,
    )
    # mocked_schedule_apply_async used to set `task_id` in the call to
    # `schedule()`, which is necessary for testing revocation of the Celery
    # task.
    measures_bulk_creator.schedule()

    with patch(
        "common.celery.app.control.revoke",
    ) as revoke_mock:
        approved_transaction.delete()

        revoke_mock.assert_called()
