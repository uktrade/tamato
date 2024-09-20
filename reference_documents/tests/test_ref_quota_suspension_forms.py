from datetime import date

import pytest
from django.core.exceptions import ValidationError

from common.util import TaricDateRange
from reference_documents.forms.ref_quota_suspension_forms import (
    RefQuotaSuspensionCreateUpdateForm,
)
from reference_documents.forms.ref_quota_suspension_forms import (
    RefQuotaSuspensionDeleteForm,
)
from reference_documents.models import RefQuotaSuspension
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaSuspensionCreateUpdateForm:
    def test_init(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        target = RefQuotaSuspensionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
        )

        # it sets initial values
        assert (
            target.reference_document_version
            == ref_quota_definition.ref_order_number.reference_document_version
        )

        assert target.Meta.fields == [
            "ref_quota_definition",
            "valid_between",
        ]

    def test_clean_ref_quota_definition(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        target = RefQuotaSuspensionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
        )

        target.cleaned_data = {}

        target.cleaned_data["ref_quota_definition"] = ref_quota_definition.id
        assert target.clean_ref_quota_definition() == ref_quota_definition.id

        del target.cleaned_data["ref_quota_definition"]
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition()
            assert e.value == "Quota definition range is required"

        target.cleaned_data["ref_quota_definition"] = ""
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition()
            assert e.value == "Quota definition range is required"

    @pytest.mark.parametrize(
        "test_name, form_data, has_errors, form_errors",
        [
            (
                "Invalid year range (beyond range of definition start and end)",
                {
                    "start_date_0": "1",
                    "start_date_1": "1",
                    "start_date_2": "2021",
                    "end_date_0": "31",
                    "end_date_1": "12",
                    "end_date_2": "2021",
                },
                True,
                {"end_date": ["End date is after the quota definitions end date"]},
            ),
            (
                "End date < Start date",
                {
                    "start_date_0": "1",
                    "start_date_1": "2",
                    "start_date_2": "2024",
                    "end_date_0": "1",
                    "end_date_1": "1",
                    "end_date_2": "2023",
                },
                True,
                {"end_date": ["End date is before the start date"]},
            ),
            (
                "End date < Start date #2",
                {
                    "start_date_0": "28",
                    "start_date_1": "12",
                    "start_date_2": "2024",
                    "end_date_0": "1",
                    "end_date_1": "12",
                    "end_date_2": "2023",
                },
                True,
                {
                    "end_date": [
                        "End date is before the start date",
                        "End date is after the quota definitions end date",
                    ],
                },
            ),
            (
                "Start date is not valid",
                {
                    "start_date_0": "31",
                    "start_date_1": "6",
                    "start_date_2": "2024",
                    "end_date_0": "1",
                    "end_date_1": "12",
                    "end_date_2": "2024",
                },
                True,
                {
                    "start_date": [
                        "Day is out of range for month Start date is not valid",
                    ],
                },
            ),
            (
                "end date is not valid",
                {
                    "start_date_0": "1",
                    "start_date_1": "1",
                    "start_date_2": "2024",
                    "end_date_0": "31",
                    "end_date_1": "6",
                    "end_date_2": "2024",
                },
                True,
                {"end_date": ["Day is out of range for month End date is not valid"]},
            ),
            (
                "end date is not valid",
                {
                    "start_date_0": "1",
                    "start_date_1": "1",
                    "start_date_2": "2022",
                    "end_date_0": "28",
                    "end_date_1": "6",
                    "end_date_2": "2025",
                },
                True,
                {"end_date": ["End date is after the quota definitions end date"]},
            ),
        ],
    )
    def test_clean(self, test_name, form_data, has_errors, form_errors):
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            valid_between=TaricDateRange(date(2021, 1, 3), date(2021, 9, 1)),
        )

        form_data["ref_quota_definition"] = ref_quota_definition

        target = RefQuotaSuspensionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            data=form_data,
        )

        assert target.is_valid() is not has_errors

        if has_errors:
            for key, err_msgs in form_errors.items():
                for err_msg in err_msgs:
                    assert err_msg in " ".join(target.errors[key])


@pytest.mark.reference_documents
class TestRefQuotaSuspensionDeleteForm:
    def test_init(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory()

        target = RefQuotaSuspensionDeleteForm(
            instance=ref_quota_suspension,
        )

        # it sets initial values
        assert target.Meta.model == RefQuotaSuspension
        assert target.Meta.fields == []
