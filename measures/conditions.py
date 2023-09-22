from measures.constants import START
from measures.constants import MeasureEditSteps


def show_step_start_date(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.START_DATE.value in cleaned_data.get("fields_to_edit")


def show_step_end_date(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.END_DATE.value in cleaned_data.get("fields_to_edit")


def show_step_quota_order_number(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.QUOTA_ORDER_NUMBER.value in cleaned_data.get(
            "fields_to_edit",
        )


def show_step_regulation(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.REGULATION.value in cleaned_data.get("fields_to_edit")


def show_step_duties(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.DUTIES.value in cleaned_data.get("fields_to_edit")


def show_step_geographical_area_exclusions(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(START)
    if cleaned_data:
        return MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS.value in cleaned_data.get(
            "fields_to_edit",
        )


measure_edit_condition_dict = {
    MeasureEditSteps.START_DATE: show_step_start_date,
    MeasureEditSteps.END_DATE: show_step_end_date,
    MeasureEditSteps.QUOTA_ORDER_NUMBER: show_step_quota_order_number,
    MeasureEditSteps.REGULATION: show_step_regulation,
    MeasureEditSteps.DUTIES: show_step_duties,
    MeasureEditSteps.GEOGRAPHICAL_AREA_EXCLUSIONS: show_step_geographical_area_exclusions,
}
