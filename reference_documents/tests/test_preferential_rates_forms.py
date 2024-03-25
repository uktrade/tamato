import pytest

from reference_documents.forms.preferential_rate_forms import (
    PreferentialRateCreateUpdateForm,
)
from reference_documents.forms.preferential_rate_forms import PreferentialRateDeleteForm
from reference_documents.models import PreferentialRate
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRateCreateUpdateForm:
    def test_validation_valid(self):
        form = PreferentialRateCreateUpdateForm(
            data={
                "commodity_code": "0100000000",
                "duty_rate": "10%",
                "start_date_0": "1",
                "start_date_1": "1",
                "start_date_2": "2024",
                "end_date": None,
            },
        )

        assert form.is_valid()

    def test_validation_no_comm_code(self):
        form = PreferentialRateCreateUpdateForm(
            data={
                "commodity_code": "",
                "duty_rate": "",
                "start_date_0": "1",
                "start_date_1": "1",
                "start_date_2": "2024",
                "end_date": None,
            },
        )

        assert not form.is_valid()
        assert "commodity_code" in form.errors.as_data().keys()
        assert "duty_rate" in form.errors.as_data().keys()
        assert "start_date" not in form.errors.as_data().keys()
        assert "end_date" not in form.errors.as_data().keys()


@pytest.mark.reference_documents
class TestPreferentialRateDeleteForm:
    def test_init(self):
        pref_rate = factories.PreferentialRateFactory()

        target = PreferentialRateDeleteForm(
            instance=pref_rate,
        )

        assert target.instance == pref_rate
        assert target.Meta.fields == []
        assert target.Meta.model == PreferentialRate
