import datetime
from unittest.mock import ANY
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from common.models.utils import override_current_transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import ApplicabilityCode
from measures.models import MeasuresBulkCreator
from measures.models import MeasuresBulkEditor
from measures.models import ProcessingState
from measures.tests.factories import MeasuresBulkCreatorFactory
from measures.tests.factories import MeasuresBulkEditorFactory
from measures.validators import MeasureExplosionLevel

pytestmark = pytest.mark.django_db


def test_schedule_task_bulk_measures_create(
    simple_measures_bulk_creator,
    mocked_create_schedule_apply_async,
):
    """Test that calling MeasuresBulkCreator.schedule() correctly schedules a
    Celery task."""

    simple_measures_bulk_creator.schedule_task()

    mocked_create_schedule_apply_async.assert_called_once_with(
        kwargs={
            "measures_bulk_creator_pk": simple_measures_bulk_creator.pk,
        },
        countdown=ANY,
    )


def test_schedule_task_bulk_measures_edit(
    simple_measures_bulk_editor,
    mocked_edit_schedule_apply_async,
):
    """Test that calling MeasuresBulkCreator.schedule() correctly schedules a
    Celery task."""

    simple_measures_bulk_editor.schedule_task()

    mocked_edit_schedule_apply_async.assert_called_once_with(
        kwargs={
            "measures_bulk_editor_pk": simple_measures_bulk_editor.pk,
        },
        countdown=ANY,
    )


def test_REVOKE_TASKS_AND_SET_NULL(
    simple_measures_bulk_creator,
    mocked_create_schedule_apply_async,
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
        simple_measures_bulk_creator.workbasket.delete()

        revoke_mock.assert_called()


def test_cancel_task(
    simple_measures_bulk_creator,
    mocked_create_schedule_apply_async,
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


@patch("measures.parsers.DutySentenceParser")
@patch("measures.forms.wizard.LarkDutySentenceParser")
def test_bulk_creator_get_forms_cleaned_data(
    mock_lark_duty_sentence_parser,
    mock_duty_sentence_parser,
    user_empty_workbasket,
    regulation,
    lark_duty_sentence_parser,
    duty_sentence_parser,
    erga_omnes,
):
    measure_type = factories.MeasureTypeFactory.create(
        measure_explosion_level=MeasureExplosionLevel.TARIC,
        measure_component_applicability_code=ApplicabilityCode.PERMITTED,
        valid_between=TaricDateRange(datetime.date(2020, 1, 1), None, "[)"),
    )
    commodity1, commodity2 = factories.GoodsNomenclatureFactory.create_batch(2)

    mock_lark_duty_sentence_parser.return_value = lark_duty_sentence_parser
    mock_duty_sentence_parser.return_value = duty_sentence_parser

    form_data = {
        "measure_details": {
            "measure_type": measure_type.pk,
            "start_date_0": 2,
            "start_date_1": 4,
            "start_date_2": 2021,
            "min_commodity_count": 2,
        },
        "regulation_id": {"generating_regulation": regulation.pk},
        "quota_order_number": {
            "order_number": "",
        },
        "geographical_area": {
            "geographical_area-geo_area": "ERGA_OMNES",
        },
        "commodities": {
            "measure_commodities_duties_formset-0-commodity": commodity1.pk,
            "measure_commodities_duties_formset-0-duties": "33 GBP/100kg",
            "measure_commodities_duties_formset-1-commodity": commodity2.pk,
            "measure_commodities_duties_formset-1-duties": "40 GBP/100kg",
        },
        "additional_code": {},
        "conditions": {},
        "footnotes": {},
    }
    form_kwargs = {
        "measure_details": {},
        "regulation_id": {},
        "quota_order_number": {},
        "quota_origins": {},
        "geographical_area": {},
        "commodities": {
            "min_commodity_count": 2,
        },
        "additional_code": {},
        "conditions": {},
        "footnotes": {},
    }

    mock_bulk_creator = MeasuresBulkCreatorFactory.create(
        form_data=form_data,
        form_kwargs=form_kwargs,
        workbasket=user_empty_workbasket,
        user=None,
    )
    with override_current_transaction(user_empty_workbasket.current_transaction):
        data = mock_bulk_creator.get_forms_cleaned_data()
        assert data == {
            "measure_type": measure_type,
            "valid_between": TaricDateRange(datetime.date(2021, 4, 2), None, "[)"),
            "min_commodity_count": 2,
            "generating_regulation": regulation,
            "order_number": None,
            "geo_area": "ERGA_OMNES",
            "erga_omnes_exclusions_formset": [],
            "geo_group_exclusions_formset": [],
            "geo_areas_and_exclusions": [{"geo_area": erga_omnes}],
            "formset-commodities": [
                {"commodity": commodity1, "duties": "33 GBP/100kg", "form_prefix": 0},
                {"commodity": commodity2, "duties": "40 GBP/100kg", "form_prefix": 1},
            ],
            "additional_code": None,
            "formset-conditions": [],
            "formset-footnotes": [],
        }


# Run the form and get the form data from the sync done
@patch("measures.parsers.DutySentenceParser")
def test_bulk_editor_get_forms_cleaned_data(
    mock_duty_sentence_parser,
    user_empty_workbasket,
    duty_sentence_parser,
):

    mock_duty_sentence_parser.return_value = duty_sentence_parser

    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    measure_1 = factories.MeasureFactory.create()
    measure_2 = factories.MeasureFactory.create()
    measure_3 = factories.MeasureFactory.create()
    regulation = factories.RegulationFactory()
    order_number = factories.QuotaOrderNumberFactory.create()

    selected_measures = [measure_1.pk, measure_2.pk, measure_3.pk]

    form_data = {
        "start_date": {
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2023,
        },
        "end_date": {
            "end_date_0": 2,
            "end_date_1": 2,
            "end_date_2": 2026,
        },
        "quota_order_number": {"order_number": order_number.pk},
        "regulation": {"generating_regulation": regulation.pk},
        "duties": {"duties": "4%"},
        "geographical_area_exclusions": {
            "form-0-excluded_area": geo_area1.pk,
            "form-1-excluded_area": geo_area2.pk,
        },
    }

    form_kwargs = {
        "start_date": {"selected_measures": selected_measures},
        "end_date": {"selected_measures": selected_measures},
        "quota_order_number": {},
        "regulation": {"selected_measures": selected_measures},
        "duties": {"selected_measures": selected_measures},
        "geographical_area_exclusions": {},
    }

    mock_bulk_editor = MeasuresBulkEditorFactory.create(
        form_data=form_data,
        form_kwargs=form_kwargs,
        workbasket=user_empty_workbasket,
        selected_measures=selected_measures,
        user=None,
    )
    with override_current_transaction(user_empty_workbasket.current_transaction):
        data = mock_bulk_editor.get_forms_cleaned_data()
        assert data == {
            "start_date": datetime.date(2023, 1, 1),
            "end_date": datetime.date(2026, 2, 2),
            "generating_regulation": regulation,
            "order_number": order_number,
            "duties": "4%",
            "formset-geographical_area_exclusions": [
                {"excluded_area": geo_area1, "DELETE": False},
                {"excluded_area": geo_area2, "DELETE": False},
            ],
        }


@patch("measures.parsers.DutySentenceParser")
@patch("measures.forms.wizard.LarkDutySentenceParser")
def test_bulk_creator_get_forms_cleaned_data_errors(
    mock_lark_duty_sentence_parser,
    mock_duty_sentence_parser,
    user_empty_workbasket,
    lark_duty_sentence_parser,
    duty_sentence_parser,
):
    mock_lark_duty_sentence_parser.return_value = lark_duty_sentence_parser
    mock_duty_sentence_parser.return_value = duty_sentence_parser

    form_data = {
        "measure_details": {
            "measure_type": "",
            "start_date_0": "",
            "start_date_1": "",
            "start_date_2": "",
            "min_commodity_count": "",
        },
        "regulation_id": {"generating_regulation": ""},
        "quota_order_number": {
            "order_number": "",
        },
        "geographical_area": {
            "geo_area": "",
        },
        "commodities": {
            "measure_commodities_duties_formset-0-commodity": "",
            "measure_commodities_duties_formset-0-duties": "",
        },
        "additional_code": {},
        "conditions": {},
        "footnotes": {},
    }
    form_kwargs = {
        "measure_details": {},
        "regulation_id": {},
        "quota_order_number": {},
        "quota_origins": {},
        "geographical_area": {},
        "commodities": {
            "min_commodity_count": 2,
        },
        "additional_code": {},
        "conditions": {},
        "footnotes": {},
    }

    mock_bulk_creator = MeasuresBulkCreatorFactory.create(
        form_data=form_data,
        form_kwargs=form_kwargs,
        workbasket=user_empty_workbasket,
        user=None,
    )
    with override_current_transaction(user_empty_workbasket.current_transaction):
        with pytest.raises(ValidationError):
            mock_bulk_creator.get_forms_cleaned_data()


@patch("measures.parsers.DutySentenceParser")
def test_bulk_editor_get_forms_cleaned_data_errors(
    mock_duty_sentence_parser,
    user_empty_workbasket,
    duty_sentence_parser,
):
    mock_duty_sentence_parser.return_value = duty_sentence_parser

    measure_1 = factories.MeasureFactory.create()
    measure_2 = factories.MeasureFactory.create()
    measure_3 = factories.MeasureFactory.create()

    selected_measures = [measure_1.pk, measure_2.pk, measure_3.pk]

    form_data = {
        "start_date": {
            "start_date_0": "",
            "start_date_1": "",
            "start_date_2": "",
        },
        "end_date": {
            "end_date_0": "",
            "end_date_1": "",
            "end_date_2": "",
        },
        "quota_order_number": {"order_number": ""},
        "regulation": {"generating_regulation": ""},
        "duties": {"duties": ""},
        "geographical_area_exclusions": {
            "form-0-excluded_area": "",
            "form-1-excluded_area": "",
        },
    }

    form_kwargs = {
        "start_date": {"selected_measures": selected_measures},
        "end_date": {"selected_measures": selected_measures},
        "quota_order_number": {},
        "regulation": {"selected_measures": selected_measures},
        "duties": {"selected_measures": selected_measures},
        "geographical_area_exclusions": {},
    }

    mock_bulk_editor = MeasuresBulkEditorFactory.create(
        form_data=form_data,
        form_kwargs=form_kwargs,
        workbasket=user_empty_workbasket,
        selected_measures=selected_measures,
        user=None,
    )

    with override_current_transaction(user_empty_workbasket.current_transaction):
        with pytest.raises(ValidationError):
            mock_bulk_editor.get_forms_cleaned_data()
