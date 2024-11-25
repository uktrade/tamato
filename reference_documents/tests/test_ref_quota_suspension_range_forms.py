from datetime import date

import pytest
from django.core.exceptions import ValidationError

from reference_documents.forms.ref_quota_suspension_range_forms import (
    RefQuotaSuspensionRangeCreateUpdateForm,
)
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaSuspensionRangeCreateUpdateForm:
    def test_init(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        # it sets initial values
        assert target.ref_order_number == ref_quota_definition_range.ref_order_number
        assert (
            target.reference_document_version
            == ref_quota_definition_range.ref_order_number.reference_document_version
        )
        assert target.Meta.fields == [
            "ref_quota_definition_range",
            "start_day",
            "start_month",
            "end_day",
            "end_month",
            "start_year",
            "end_year",
        ]

    def test_clean_start_year(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["start_year"] = 2000
        with pytest.raises(ValidationError) as e:
            target.clean_start_year()
            assert e.value == "Start year is not valid"

        target.cleaned_data["start_year"] = date.today().year + 101
        with pytest.raises(ValidationError) as e:
            target.clean_start_year()
            assert e.value == "Start year is not valid"

        del target.cleaned_data["start_year"]
        with pytest.raises(ValidationError) as e:
            target.clean_start_year()
            assert e.value == "Start year is not valid"

        target.cleaned_data["start_year"] = 2024
        assert target.clean_start_year() == 2024

    def test_clean_end_year(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["end_year"] = date.today().year + 101
        with pytest.raises(ValidationError) as e:
            target.clean_end_year()
            assert e.value == "End year is not valid"

        del target.cleaned_data["end_year"]
        with pytest.raises(ValidationError) as e:
            target.clean_end_year()
            assert e.value == "End year is not valid"

        target.cleaned_data["end_year"] = 2024
        assert target.clean_end_year() == 2024

    def test_clean_start_day(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["start_day"] = 32
        with pytest.raises(ValidationError) as e:
            target.clean_start_day()
            assert e.value == "Start day is not valid, it must be between 1 and 31"

        target.cleaned_data["start_day"] = 0
        with pytest.raises(ValidationError) as e:
            target.clean_start_day()
            assert e.value == "Start day is not valid, it must be between 1 and 31"

        del target.cleaned_data["start_day"]
        with pytest.raises(ValidationError) as e:
            target.clean_start_day()
            assert e.value == "Start day is not valid, it must be between 1 and 31"

        target.cleaned_data["start_day"] = 20
        assert target.clean_start_day() == 20

    def test_clean_end_day(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["end_day"] = 32
        with pytest.raises(ValidationError) as e:
            target.clean_end_day()
            assert e.value == "End day is not valid, it must be between 1 and 31"

        target.cleaned_data["end_day"] = 0
        with pytest.raises(ValidationError) as e:
            target.clean_end_day()
            assert e.value == "End day is not valid, it must be between 1 and 31"

        del target.cleaned_data["end_day"]
        with pytest.raises(ValidationError) as e:
            target.clean_end_day()
            assert e.value == "End day is not valid, it must be between 1 and 31"

        target.cleaned_data["end_day"] = 20
        assert target.clean_end_day() == 20

    def test_clean_end_month(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["end_month"] = 13
        with pytest.raises(ValidationError) as e:
            target.clean_end_month()
            assert e.value == "End month is not valid, it must be between 1 and 12"

        target.cleaned_data["end_month"] = 0
        with pytest.raises(ValidationError) as e:
            target.clean_end_month()
            assert e.value == "End month is not valid, it must be between 1 and 12"

        del target.cleaned_data["end_month"]
        with pytest.raises(ValidationError) as e:
            target.clean_end_month()
            assert e.value == "End month is not valid, it must be between 1 and 12"

        target.cleaned_data["end_month"] = 10
        assert target.clean_end_month() == 10

    def test_clean_start_month(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["start_month"] = 13
        with pytest.raises(ValidationError) as e:
            target.clean_start_month()
            assert e.value == "Start month is not valid, it must be between 1 and 12"

        target.cleaned_data["start_month"] = 0
        with pytest.raises(ValidationError) as e:
            target.clean_start_month()
            assert e.value == "Start month is not valid, it must be between 1 and 12"

        del target.cleaned_data["start_month"]
        with pytest.raises(ValidationError) as e:
            target.clean_start_month()
            assert e.value == "Start month is not valid, it must be between 1 and 12"

        target.cleaned_data["start_month"] = 10
        assert target.clean_start_month() == 10

    def test_clean_ref_quota_definition_range(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
        )

        target.cleaned_data = {}

        target.cleaned_data["ref_quota_definition_range"] = (
            ref_quota_definition_range.id
        )
        assert (
            target.clean_ref_quota_definition_range() == ref_quota_definition_range.id
        )

        del target.cleaned_data["ref_quota_definition_range"]
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition_range()
            assert e.value == "Quota definition range is required"

        target.cleaned_data["ref_quota_definition_range"] = ""
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition_range()
            assert e.value == "Quota definition range is required"

    @pytest.mark.parametrize(
        "test_name, form_data, has_errors, form_errors",
        [
            (
                "Invalid year range",
                {
                    "start_year": "2024",
                    "end_year": "2023",
                },
                True,
                {
                    "end_year": "Please enter an end year greater than or equal to the start year",
                },
            ),
            (
                "End date < Start date",
                {
                    "start_day": "1",
                    "start_month": "2",
                    "start_year": "2024",
                    "end_day": "1",
                    "end_month": "1",
                    "end_year": "2023",
                },
                True,
                {
                    "end_year": "Please enter an end year greater than or equal to the start year",
                },
            ),
            (
                "End date < Start date #2",
                {
                    "start_day": "28",
                    "start_month": "12",
                    "end_day": "1",
                    "end_month": "12",
                    "start_year": "2024",
                    "end_year": "2023",
                },
                True,
                {
                    "end_year": "Please enter an end year greater than or equal to the start year",
                },
            ),
            (
                "Start date is not valid",
                {
                    "start_day": "31",
                    "start_month": "6",
                    "start_year": "2024",
                    "end_day": "1",
                    "end_month": "12",
                    "end_year": "2024",
                },
                True,
                {
                    "start_day": "The calculated start date is not valid for the year range",
                },
            ),
            (
                "end date is not valid",
                {
                    "start_day": "1",
                    "start_month": "1",
                    "start_year": "2024",
                    "end_day": "31",
                    "end_month": "6",
                    "end_year": "2024",
                },
                True,
                {"end_day": "The calculated end date is not valid for the year range"},
            ),
            (
                "end date is not valid",
                {
                    "start_day": "1",
                    "start_month": "1",
                    "start_year": "2022",
                    "end_day": "28",
                    "end_month": "6",
                    "end_year": "2025",
                },
                True,
                {
                    "__all__": "does not fall within any definition defined by the selected quota definition template",
                },
            ),
        ],
    )
    def test_clean(self, test_name, form_data, has_errors, form_errors):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            start_year=2023,
            end_year=2024,
        )
        form_data["ref_quota_definition_range"] = ref_quota_definition_range

        target = RefQuotaSuspensionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            ref_quota_definition_range,
            data=form_data,
        )

        assert target.is_valid() is not has_errors

        if has_errors:
            for key, value in form_errors.items():
                assert value in " ".join(target.errors[key])
