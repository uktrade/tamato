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


measure_edit_condition_dict = {
    MeasureEditSteps.START_DATE: show_step_start_date,
    MeasureEditSteps.END_DATE: show_step_end_date,
}
