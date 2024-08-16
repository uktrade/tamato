from datetime import date

import pytest
from django.core.exceptions import ValidationError

from common.util import TaricDateRange
from reference_documents.forms.ref_quota_suspension_forms import RefQuotaSuspensionCreateUpdateForm
from reference_documents.forms.ref_quota_suspension_range_forms import RefQuotaSuspensionRangeCreateUpdateForm
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

        target.cleaned_data['ref_quota_definition'] = ref_quota_definition.id
        assert target.clean_ref_quota_definition() == ref_quota_definition.id

        del target.cleaned_data['ref_quota_definition']
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition()
            assert e.value == "Quota definition range is required"

        target.cleaned_data['ref_quota_definition'] = ''
        with pytest.raises(ValidationError) as e:
            target.clean_ref_quota_definition()
            assert e.value == "Quota definition range is required"

    @pytest.mark.parametrize("test_name, form_data, has_errors, form_errors", [
        (
                "Invalid year range (beyond range of definition start and end)",
                {
                    'valid_between': TaricDateRange(date(2021, 1, 1), date(2021, 12, 31)),
                },
                True,
                {'end_year': 'Please enter an end year greater than or equal to the start year'}
        ), (
                "Invalid year range (beyond range of definition)",
                {
                    'valid_between': TaricDateRange(date(2021, 1, 1), date(2021, 12, 31)),
                },
                True,
                {'end_year': 'Please enter an end year greater than or equal to the start year'}
        ), (
                "End date < Start date",
                {
                    'start_day': '1',
                    'start_month': '2',
                    'start_year': '2024',
                    'end_day': '1',
                    'end_month': '1',
                    'end_year': '2023',
                },
                True,
                {'end_year': 'Please enter an end year greater than or equal to the start year'}
        ), (
                "End date < Start date #2",
                {
                    'start_day': '28',
                    'start_month': '12',
                    'end_day': '1',
                    'end_month': '12',
                    'start_year': '2024',
                    'end_year': '2023',

                },
                True,
                {'end_year': 'Please enter an end year greater than or equal to the start year'}
        ), (
                "Start date is not valid",
                {
                    'start_day': '31',
                    'start_month': '6',
                    'start_year': '2024',
                    'end_day': '1',
                    'end_month': '12',
                    'end_year': '2024',
                },
                True,
                {'start_day': 'The calculated start date is not valid for the year range'}
        ), (
                "end date is not valid",
                {
                    'start_day': '1',
                    'start_month': '1',
                    'start_year': '2024',
                    'end_day': '31',
                    'end_month': '6',
                    'end_year': '2024',
                },
                True,
                {'end_day': 'The calculated end date is not valid for the year range'}
        ), (
                "end date is not valid",
                {
                    'start_day': '1',
                    'start_month': '1',
                    'start_year': '2022',
                    'end_day': '28',
                    'end_month': '6',
                    'end_year': '2025',
                },
                True,
                {'__all__': 'does not fall within any definition defined by the selected quota definition template'}
        ),

    ])
    def test_clean(self, test_name, form_data, has_errors, form_errors):
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            valid_between=TaricDateRange(date(2021, 1, 3), date(2021, 9, 1))
        )

        form_data['ref_quota_definition'] = ref_quota_definition

        target = RefQuotaSuspensionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            data=form_data
        )

        assert target.is_valid() is not has_errors

        if has_errors:
            for key, value in form_errors.items():
                assert value in ' '.join(target.errors[key])
