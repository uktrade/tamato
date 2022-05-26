from datetime import date

import pytest

from additional_codes import forms
from common.tests import factories

pytestmark = pytest.mark.django_db

# https://uktrade.atlassian.net/browse/TP2000-296
def test_additional_code_create_sid(session_with_workbasket):
    """Tests that additional code type is NOT considered when generating a new
    sid."""
    type_1 = factories.AdditionalCodeTypeFactory.create()
    type_2 = factories.AdditionalCodeTypeFactory.create()
    additional_code = factories.AdditionalCodeFactory.create(type=type_1)
    start_date = date.today()
    data = {
        "type": type_2,
        "code": 123,
        "description": "description",
        "start_date_0": start_date.day,
        "start_date_1": start_date.month,
        "start_date_2": start_date.year,
    }
    form = forms.AdditionalCodeCreateForm(data=data, request=session_with_workbasket)
    form.is_valid()
    new_additional_code = form.save(commit=False)

    assert new_additional_code.sid != additional_code.sid
