from datetime import date

import pytest

from reference_documents.forms.ref_quota_definition_range_forms import RefQuotaDefinitionRangeCreateUpdateForm, RefQuotaDefinitionRangeDeleteForm
from reference_documents.models import RefQuotaDefinitionRange
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaDefinitionRangeCreateUpdateForm:
    def test_init(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
        )

        # it sets initial values
        assert (
                target.reference_document_version
                == ref_quota_definition_range.ref_order_number.reference_document_version
        )
        assert target.Meta.model == RefQuotaDefinitionRange
        assert target.Meta.fields == [
            "ref_order_number",
            "commodity_code",
            "duty_rate",
            "initial_volume",
            "yearly_volume_increment",
            "yearly_volume_increment_text",
            "measurement",
            "start_day",
            "start_month",
            "end_day",
            "end_month",
            "start_year",
            "end_year",
        ]

    def test_clean_duty_rate(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {'duty_rate': ''}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        assert target.errors['duty_rate'] == ['Duty rate is required']

    @pytest.mark.parametrize(
        "value, expected_message",
        [
            ('zz', 'Enter a whole number.'),
            (0, 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
            (1980, 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
            (date.today().year + 2, None),
            (date.today().year + 101, 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
        ],
    )
    def test_clean_start_year(self, value, expected_message):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {'start_year': value}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        if expected_message:
            assert target.errors['start_year'] == [expected_message]
        else:
            assert 'start_year' not in target.errors

    @pytest.mark.parametrize(
        "value, field, expected_message",
        [
            # start day
            ('', 'start_day', 'This field is required.'),
            ('zz', 'start_day', 'Enter a whole number.'),
            (0, 'start_day', f'Start day is not valid, it must be between 1 and 31'),
            (32, 'start_day', f'Start day is not valid, it must be between 1 and 31'),
            (-1, 'start_day', f'Ensure this value is greater than or equal to 0.'),
            (15, 'start_day', None),
            # end day
            ('', 'end_day', 'This field is required.'),
            ('zz', 'end_day', 'Enter a whole number.'),
            (0, 'end_day', f'End day is not valid, it must be between 1 and 31'),
            (32, 'end_day', f'End day is not valid, it must be between 1 and 31'),
            (-1, 'end_day', f'Ensure this value is greater than or equal to 0.'),
            (15, 'end_day', None),
            # start month
            ('', 'start_month', 'This field is required.'),
            ('zz', 'start_month', 'Enter a whole number.'),
            (0, 'start_month', 'Start month is not valid, it must be between 1 and 12'),
            (13, 'start_month', 'Start month is not valid, it must be between 1 and 12'),
            (-1, 'start_month', 'Ensure this value is greater than or equal to 0.'),
            (1, 'start_month', None),
            # end month
            ('', 'end_month', 'This field is required.'),
            ('zz', 'end_month', 'Enter a whole number.'),
            (0, 'end_month', 'End month is not valid, it must be between 1 and 12'),
            (13, 'end_month', 'End month is not valid, it must be between 1 and 12'),
            (-1, 'end_month', 'Ensure this value is greater than or equal to 0.'),
            (1, 'end_month', None),
            # start year
            ('', 'start_year', 'This field is required.'),
            ('zz', 'start_year', 'Enter a whole number.'),
            (0, 'start_year', 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
            (1980, 'start_year', 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
            (date.today().year + 101, 'start_year', 'Start year is not valid, it must be a 4 digit year greater than 2010 and less than 2124'),
            (date.today().year + 2, 'start_year', None),
            # end year
            ('zz', 'end_year', 'Enter a whole number.'),
            (0, 'end_year', f'End year is not valid, it must be a 4 digit year, greater than 2010, less than {date.today().year + 100} or blank'),
            (1980, 'end_year', f'End year is not valid, it must be a 4 digit year, greater than 2010, less than {date.today().year + 100} or blank'),
            (date.today().year + 101, 'end_year', f'End year is not valid, it must be a 4 digit year, greater than 2010, less than {date.today().year + 100} or blank'),
            (date.today().year + 2, 'end_year', None),
            ('', 'end_year', None),
            # duty rate
            ('', 'duty_rate', 'Duty rate is required'),
            (0, 'duty_rate', None),
            (0.9, 'duty_rate', None),
            (1, 'duty_rate', None),
            (1.3, 'duty_rate', None),
            (123.77, 'duty_rate', None),
            (-123.77, 'duty_rate', None),
            ('banana', 'duty_rate', None),
        ],
    )
    def test_clean_fields(self, value, field, expected_message):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {field: value}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        if expected_message:
            assert target.errors[field] == [expected_message]
        else:
            assert field not in target.errors

    def test_clean_duty_rate_not_entered(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        assert target.errors['duty_rate'] == ['Duty rate is required']

    def test_clean_ref_order_number_valid(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {'ref_order_number': ref_quota_definition_range.ref_order_number}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        assert 'ref_order_number' not in target.errors.keys()

    def test_clean_ref_order_number_invalid(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        data = {'ref_order_number': None}

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        assert not target.is_valid()
        assert target.errors['ref_order_number'] == ['Quota order number is required']

    @pytest.mark.parametrize(
        "data, expected_error_messages",
        [
            # no data - all failure messages
            (
                    {},
                    {
                        'ref_order_number': ['Quota order number is required'],
                        'commodity_code': ['Enter the commodity code'],
                        'duty_rate': ['Duty rate is required'],
                        'initial_volume': ['This field is required.'],
                        'measurement': ['Measurement is required'],
                        'start_day': ['This field is required.'],
                        'start_month': ['This field is required.'],
                        'end_day': ['This field is required.'],
                        'end_month': ['This field is required.'],
                        'start_year': ['This field is required.']
                    }
            ),
            # all data needed to pass
            (
                    {
                        'ref_order_number': 'generate',
                        'commodity_code': '1231230000',
                        'duty_rate': 'xyz',
                        'initial_volume': 20,
                        'measurement': 'kgs',
                        'start_day': 1,
                        'start_month': 1,
                        'end_day': 31,
                        'end_month': 12,
                        'start_year': date.today().year
                    },
                    None
            ),
            # end year < start year
            (
                    {
                        'ref_order_number': 'generate',
                        'commodity_code': '1231230000',
                        'duty_rate': 'xyz',
                        'initial_volume': 20,
                        'measurement': 'kgs',
                        'start_day': 1,
                        'start_month': 1,
                        'end_day': 31,
                        'end_month': 12,
                        'start_year': date.today().year,
                        'end_year': date.today().year - 1
                    },
                    {
                        'end_year': ['Please enter an end year greater than or equal to the start year']
                    }
            ),
            # end month < start month
            (
                    {
                        'ref_order_number': 'generate',
                        'commodity_code': '1231230000',
                        'duty_rate': 'xyz',
                        'initial_volume': 20,
                        'measurement': 'kgs',
                        'start_day': 1,
                        'start_month': 12,
                        'end_day': 1,
                        'end_month': 11,
                        'start_year': date.today().year
                    },
                    {
                        "end_day": ['The calculated end date is later than start date in a calendar year'],
                        "end_month": ['The calculated end date is later than start date in a calendar year'],
                        "start_day": ['The calculated end date is later than start date in a calendar year'],
                        "start_month": ['The calculated end date is later than start date in a calendar year'],
                    }
            ),
            # invalid start date
            (
                    {
                        'ref_order_number': 'generate',
                        'commodity_code': '1231230000',
                        'duty_rate': 'xyz',
                        'initial_volume': 20,
                        'measurement': 'kgs',
                        'start_day': 31,
                        'start_month': 6,
                        'end_day': 1,
                        'end_month': 11,
                        'start_year': date.today().year
                    },
                    {
                        "start_day": ['The calculated start date is not valid for the year range'],
                        "start_month": ['The calculated start date is not valid for the year range'],
                    }
            ),
            # invalid end date
            (
                    {
                        'ref_order_number': 'generate',
                        'commodity_code': '1231230000',
                        'duty_rate': 'xyz',
                        'initial_volume': 20,
                        'measurement': 'kgs',
                        'start_day': 1,
                        'start_month': 1,
                        'end_day': 31,
                        'end_month': 6,
                        'start_year': date.today().year
                    },
                    {
                        "end_day": ['The calculated date using the day or month is not valid for the year range'],
                        "end_month": ['The calculated date using the day or month is not valid for the year range'],
                    }
            ),
        ])
    def test_clean(self, data, expected_error_messages):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        # cant attach factories to parametrize so order number needs ading if required
        if 'ref_order_number' in data.keys() and data['ref_order_number'] == 'generate':
            data['ref_order_number'] = ref_quota_definition_range.ref_order_number

        target = RefQuotaDefinitionRangeCreateUpdateForm(
            ref_quota_definition_range.ref_order_number.reference_document_version,
            ref_quota_definition_range.ref_order_number,
            instance=ref_quota_definition_range,
            data=data,
        )

        target.is_valid()

        if expected_error_messages is None:
            assert target.errors == {}
        else:
            for key in expected_error_messages:
                for message in expected_error_messages[key]:
                    assert message in target.errors[key]

@pytest.mark.reference_documents
class TestRefQuotaDefinitionRangeDeleteForm:
    def test_init(self):
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory()

        target = RefQuotaDefinitionRangeDeleteForm(
            instance=ref_quota_definition_range
        )

        assert target.instance == ref_quota_definition_range