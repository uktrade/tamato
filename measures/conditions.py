from measures import constants


def show_step_end_dates(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.END_DATES in cleaned_data.get("fields_to_edit")


def show_step_regulation_id(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.REGULATION_ID in cleaned_data.get("fields_to_edit")


def show_step_quota_order_number(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.QUOTA_ORDER_NUMBER in cleaned_data.get("fields_to_edit")


def show_step_geographical_area(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.GEOGRAPHICAL_AREA in cleaned_data.get("fields_to_edit")


def show_step_duties(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.DUTIES in cleaned_data.get("fields_to_edit")


def show_step_additional_code(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.ADDITIONAL_CODE in cleaned_data.get("fields_to_edit")


def show_step_conditions(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.CONDITIONS in cleaned_data.get("fields_to_edit")


def show_step_footnotes(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(constants.START)
    if cleaned_data:
        return constants.FOOTNOTES in cleaned_data.get("fields_to_edit")


measure_edit_condition_dict = {
    constants.END_DATES: show_step_end_dates,
    constants.REGULATION_ID: show_step_regulation_id,
    constants.QUOTA_ORDER_NUMBER: show_step_quota_order_number,
    constants.GEOGRAPHICAL_AREA: show_step_geographical_area,
    constants.DUTIES: show_step_duties,
    constants.ADDITIONAL_CODE: show_step_additional_code,
    constants.CONDITIONS: show_step_conditions,
    constants.FOOTNOTES: show_step_footnotes,
}
