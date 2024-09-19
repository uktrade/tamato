import datetime

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode
from quotas import models
from quotas import forms
from quotas import validators
from quotas.models import QuotaBlocking, QuotaDefinition
from quotas.models import QuotaSuspension
from quotas.serializers import serialize_duplicate_data

pytestmark = pytest.mark.django_db


def test_update_quota_form_safeguard_invalid(session_request_with_workbasket):
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    data = {
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
    }
    with override_current_transaction(quota.transaction):
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            request=session_request_with_workbasket,
            initial={},
            geo_area_options=[],
            existing_origins=[],
            exclusions_options=[],
            groups_with_members=[],
        )
        assert not form.is_valid()
        assert forms.SAFEGUARD_HELP_TEXT in form.errors["category"]


def test_update_quota_form_safeguard_disabled(session_request_with_workbasket):
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    data = {
        # if the widget is disabled the data is not submitted
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
    }
    with override_current_transaction(quota.transaction):
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            request=session_request_with_workbasket,
            initial={},
            geo_area_options=[],
            existing_origins=[],
            exclusions_options=[],
            groups_with_members=[],
        )
        assert form.is_valid()
        assert quota.category == validators.QuotaCategory.SAFEGUARD


def test_update_quota_form_safeguard_disabled(client_with_current_workbasket):
    """When a QuotaOrderNumber with the category safeguard is edited the
    category cannot be changed and the form field is disabled."""
    quota = factories.QuotaOrderNumberFactory.create(
        category=validators.QuotaCategory.SAFEGUARD,
    )
    response = client_with_current_workbasket.get(
        reverse("quota-ui-edit", kwargs={"sid": quota.sid}),
    )
    html = response.content.decode(response.charset)
    soup = BeautifulSoup(html, "html.parser")
    assert "disabled" in soup.find(id="id_category").attrs.keys()


def test_quota_definition_errors(date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    measurement_unit = factories.MeasurementUnitFactory()

    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Lorem ipsum.",
        "volume": "foo",
        "initial_volume": "bar",
        "measurement_unit": measurement_unit.pk,
        "measurement_unit_qualifier": "",
        "quota_critical_threshold": "foo",
        "quota_critical": "",
    }

    tx = Transaction.objects.last()

    def check_error_messages(form):
        assert not form.is_valid()
        assert form.errors["volume"][0] == "Volume must be a number"
        assert form.errors["initial_volume"][0] == "Initial volume must be a number"
        assert (
            form.errors["quota_critical_threshold"][0]
            == "Critical threshold must be a number"
        )
        assert form.errors["quota_critical"][0] == "Critical state must be set"

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionUpdateForm(data=data, instance=quota_definition)
        check_error_messages(form)

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionCreateForm(data=data)
        check_error_messages(form)


def test_quota_definition_volume_validation(date_ranges):
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.big_no_end,
    )
    measurement_unit = factories.MeasurementUnitFactory()

    data = {
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "description": "Lorem ipsum.",
        "volume": "600.000",
        "initial_volume": "500.000",
        "measurement_unit": measurement_unit.pk,
        "measurement_unit_qualifier": "",
        "quota_critical_threshold": "90",
        "quota_critical": "False",
    }

    tx = Transaction.objects.last()

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionUpdateForm(data=data, instance=quota_definition)
        assert not form.is_valid()
        assert (
            form.errors["__all__"][0]
            == "Current volume cannot be higher than initial volume"
        )

    with override_current_transaction(tx):
        form = forms.QuotaDefinitionCreateForm(data=data)
        assert not form.is_valid()
        assert (
            form.errors["__all__"][0]
            == "Current volume cannot be higher than initial volume"
        )


def test_quota_update_react_form_cleaned_data(session_request_with_workbasket):
    quota = factories.QuotaOrderNumberFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    area_1 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_2 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_3 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    # create geo area group with members to be excluded
    data = {
        "category": quota.category,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "end_date_0": 1,
        "end_date_1": 1,
        "end_date_2": 2010,
        "origins-0-geographical_area": quota.quotaordernumberorigin_set.first().geographical_area.pk,
        "origins-0-start_date_0": 1,
        "origins-0-start_date_1": 1,
        "origins-0-start_date_2": 2000,
        "origins-0-end_date_0": 1,
        "origins-0-end_date_1": 1,
        "origins-0-end_date_2": 2010,
        "origins-0-exclusions-0-geographical_area": area_1.pk,
        "origins-0-exclusions-1-geographical_area": area_2.pk,
        "submit": "Save",
    }

    tx = Transaction.objects.last()

    with override_current_transaction(tx):
        geo_area_options = (
            GeographicalArea.objects.all()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        existing_origins = (
            quota.quotaordernumberorigin_set.current().with_latest_geo_area_description()
        )
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            initial={},
            request=session_request_with_workbasket,
            geo_area_options=geo_area_options,
            existing_origins=existing_origins,
            exclusions_options=geo_area_options.exclude(area_code=AreaCode.GROUP),
            groups_with_members=[],
        )
        assert form.is_valid()

        assert "valid_between" in form.cleaned_data["origins"][0].keys()
        assert "exclusions" in form.cleaned_data["origins"][0].keys()
        assert "geographical_area" in form.cleaned_data["origins"][0].keys()

        assert form.cleaned_data["origins"][0]["valid_between"] == TaricDateRange(
            datetime.date(2000, 1, 1),
            datetime.date(2010, 1, 1),
        )

        assert (
            form.cleaned_data["origins"][0]["geographical_area"]
            == quota.quotaordernumberorigin_set.first().geographical_area
        )

        assert len(form.cleaned_data["origins"][0]["exclusions"]) == 2


def test_quota_update_exclusions_origins_errors(session_request_with_workbasket):
    quota = factories.QuotaOrderNumberFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    area_1 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_2 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_3 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    factories.GeographicalAreaFactory.create()
    # create geo area group with members to be excluded
    data = {
        "category": quota.category,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "end_date_0": 1,
        "end_date_1": 1,
        "end_date_2": 2010,
        "origins-0-geographical_area": quota.quotaordernumberorigin_set.first().geographical_area.pk,
        "origins-0-start_date_0": 1,
        "origins-0-start_date_1": 1,
        "origins-0-start_date_2": 2000,
        "origins-0-end_date_0": 1,
        "origins-0-end_date_1": 1,
        # invalid end date
        "origins-0-end_date_2": 1999,
        "origins-0-exclusions-0-geographical_area": area_1.pk,
        # invalid exclusion
        "origins-0-exclusions-1-geographical_area": "foo",
        "submit": "Save",
    }

    tx = Transaction.objects.last()

    with override_current_transaction(tx):
        geo_area_options = (
            GeographicalArea.objects.all()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        existing_origins = (
            quota.quotaordernumberorigin_set.current().with_latest_geo_area_description()
        )
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            initial={},
            request=session_request_with_workbasket,
            geo_area_options=geo_area_options,
            existing_origins=existing_origins,
            exclusions_options=geo_area_options.exclude(area_code=AreaCode.GROUP),
            groups_with_members=[],
        )
        assert not form.is_valid()

        assert form.errors["origins-0-exclusions-0-geographical_area"] == [
            "Select a valid choice. That choice is not one of the available choices.",
        ]
        assert form.errors["origins-0-end_date"] == [
            "The end date must be the same as or after the start date.",
        ]


@pytest.mark.parametrize(
    "field_name, error",
    [
        ("some_field", "There is a problem"),
        ("some_field", ValidationError("There is a problem")),
        (None, {"some_field": "There is a problem"}),
    ],
)
def test_quota_update_add_extra_error(
    field_name,
    error,
    session_request_with_workbasket,
):
    quota = factories.QuotaOrderNumberFactory.create()
    data = {
        "category": quota.category,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "submit": "Save",
    }
    with override_current_transaction(quota.transaction):
        geo_area_options = (
            GeographicalArea.objects.all()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        existing_origins = (
            quota.quotaordernumberorigin_set.current().with_latest_geo_area_description()
        )
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            initial={},
            request=session_request_with_workbasket,
            geo_area_options=geo_area_options,
            existing_origins=existing_origins,
            exclusions_options=geo_area_options.exclude(area_code=AreaCode.GROUP),
            groups_with_members=[],
        )
        form.add_extra_error(field_name, error)

        assert "There is a problem" in form.errors["some_field"]


def test_quota_update_add_extra_error_type_error(session_request_with_workbasket):
    quota = factories.QuotaOrderNumberFactory.create()
    data = {
        "category": quota.category,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "submit": "Save",
    }
    with override_current_transaction(quota.transaction):
        geo_area_options = (
            GeographicalArea.objects.all()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        existing_origins = (
            quota.quotaordernumberorigin_set.current().with_latest_geo_area_description()
        )
        form = forms.QuotaUpdateForm(
            data=data,
            instance=quota,
            initial={},
            request=session_request_with_workbasket,
            geo_area_options=geo_area_options,
            existing_origins=existing_origins,
            exclusions_options=geo_area_options.exclude(area_code=AreaCode.GROUP),
            groups_with_members=[],
        )
        with pytest.raises(TypeError):
            form.add_extra_error(
                "a_field",
                {"some_field": "Error", "some_other_field": "Error"},
            )


def test_quota_suspension_or_blocking_create_form_required():
    """Tests that `QuotaSuspensionOrBlockingCreateForm` adds form errors for
    missing required fields."""
    quota_definition = factories.QuotaDefinitionFactory.create()
    quota_order_number = quota_definition.order_number

    form = forms.QuotaSuspensionOrBlockingCreateForm(
        data={},
        quota_order_number=quota_order_number,
    )
    assert not form.is_valid()
    assert "Select a quota definition SID" in form.errors["quota_definition"]
    assert (
        "Select if you want to create a suspension or blocking period"
        in form.errors["suspension_type"]
    )
    assert "Enter the day, month and year" in form.errors["start_date"]


def test_quota_suspension_or_blockling_create_form_clean(date_ranges):
    """Tests that `QuotaSuspensionOrBlockingCreateForm` raises a validation
    error if the given validity period isn't contained within that of the
    selected quota definition."""
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.normal,
    )
    quota_order_number = quota_definition.order_number
    data = {
        "quota_definition": quota_definition.pk,
        "suspension_type": forms.QuotaSuspensionType.SUSPENSION,
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaSuspensionOrBlockingCreateForm(
            data=data,
            quota_order_number=quota_order_number,
        )
        assert not form.is_valid()
        assert (
            f"The start and end date must sit within the selected quota definition's start and end date ({quota_definition.valid_between.lower} - {quota_definition.valid_between.upper})"
            in form.errors["__all__"]
        )


@pytest.mark.parametrize(
    "data, expected_model",
    [
        (
            {"suspension_type": forms.QuotaSuspensionType.SUSPENSION},
            QuotaSuspension,
        ),
        (
            {
                "suspension_type": forms.QuotaSuspensionType.BLOCKING,
                "blocking_period_type": validators.BlockingPeriodType.END_USER_DECISION,
            },
            QuotaBlocking,
        ),
    ],
)
def test_quota_suspension_or_blockling_create_form_save(
    data,
    expected_model,
    workbasket,
    date_ranges,
):
    """Tests that `QuotaSuspensionOrBlockingCreateForm.save()` creates a
    suspension period or blocking period."""
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.normal,
    )
    quota_order_number = quota_definition.order_number
    data.update(
        {
            "quota_definition": quota_definition.pk,
            "description": "Test description",
            "start_date_0": quota_definition.valid_between.lower.day,
            "start_date_1": quota_definition.valid_between.lower.month,
            "start_date_2": quota_definition.valid_between.lower.year,
            "end_date_0": quota_definition.valid_between.upper.day,
            "end_date_1": quota_definition.valid_between.upper.month,
            "end_date_2": quota_definition.valid_between.upper.year,
        },
    )

    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaSuspensionOrBlockingCreateForm(
            data=data,
            quota_order_number=quota_order_number,
        )
        assert form.is_valid()
        object = form.save(workbasket)
        assert isinstance(object, expected_model)
        assert object.quota_definition == quota_definition
        assert object.description == data["description"]
        assert object.valid_between == quota_definition.valid_between
        assert object.update_type == UpdateType.CREATE
        assert object.transaction.workbasket == workbasket


@pytest.fixture
def main_quota_order_number() -> models.QuotaOrderNumber:
    """Provides a main quota order number for use across the fixtures and following tests"""
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def quota_definition_1(main_quota_order_number, date_ranges) -> QuotaDefinition:
    """Provides a definition, linked to the main_quota_order_number to be used across the following tests"""
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.normal,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )


def test_select_sub_quota_form_set_staged_definition_data(
    quota_definition_1, session_request
):
    session_request.path = ""
    form = forms.SelectSubQuotaDefinitionsForm(
        request=session_request, prefix="select_definition_periods"
    )
    quotas = models.QuotaDefinition.objects.all()
    with override_current_transaction(Transaction.objects.last()):
        form.set_staged_definition_data(quotas)
        assert (
            session_request.session["staged_definition_data"][0]["main_definition"]
            == quota_definition_1.pk
        )


"""
The following test the business rules checks against the provided data.
The checks are run in order, so subsequent tests require the data to
pass the previous rule check. More extensive testing is in test_business_rules.py
"""


def test_quota_duplicator_form_clean_QA2(
    date_ranges, session_request, quota_definition_1
):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        }
    ]
    session_request.session["staged_definition_data"] = staged_definition_data

    data = {
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
        "end_date_0": date_ranges.earlier.upper.day,
        "end_date_1": date_ranges.earlier.upper.month,
        "end_date_2": date_ranges.earlier.upper.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionsUpdatesForm(
            request=session_request,
            data=data,
            pk=quota_definition_1.pk,
        )
        assert not form.is_valid()
        assert (
            "QA2: Validity period for sub quota must be within the validity period of the main quota"
            in form.errors["__all__"]
        )


def test_quota_duplicator_form_clean_QA3(session_request, quota_definition_1):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        }
    ]

    data = {
        "start_date_0": quota_definition_1.valid_between.lower.day,
        "start_date_1": quota_definition_1.valid_between.lower.month,
        "start_date_2": quota_definition_1.valid_between.lower.year,
        "end_date_0": quota_definition_1.valid_between.upper.day,
        "end_date_1": quota_definition_1.valid_between.upper.month,
        "end_date_2": quota_definition_1.valid_between.upper.year,
        "measurement_unit": quota_definition_1.measurement_unit,
        "volume": 1235,
        "initial_volume": 1235,
    }
    session_request.session["staged_definition_data"] = staged_definition_data

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionsUpdatesForm(
            request=session_request,
            data=data,
            pk=quota_definition_1.pk,
        )
        assert not form.is_valid()
        assert (
            "QA3: When converted to the measurement unit of the main quota, the volume of a sub-quota must always be lower than or equal to the volume of the main quota"
            in form.errors["__all__"]
        )


def test_quota_duplicator_form_clean_QA4(session_request, quota_definition_1):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        }
    ]

    data = {
        "start_date_0": quota_definition_1.valid_between.lower.day,
        "start_date_1": quota_definition_1.valid_between.lower.month,
        "start_date_2": quota_definition_1.valid_between.lower.year,
        "end_date_0": quota_definition_1.valid_between.upper.day,
        "end_date_1": quota_definition_1.valid_between.upper.month,
        "end_date_2": quota_definition_1.valid_between.upper.year,
        "measurement_unit": quota_definition_1.measurement_unit,
        "volume": quota_definition_1.volume,
        "initial_volume": quota_definition_1.initial_volume,
        "coefficient": -1,
    }
    session_request.session["staged_definition_data"] = staged_definition_data

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionsUpdatesForm(
            request=session_request,
            data=data,
            pk=quota_definition_1.pk,
        )
        assert not form.is_valid()
        assert (
            "QA4: A coefficient must be a positive decimal number"
            in form.errors["__all__"]
        )


def test_quota_duplicator_form_clean_QA5_nm(session_request, quota_definition_1):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        }
    ]

    data = {
        "start_date_0": quota_definition_1.valid_between.lower.day,
        "start_date_1": quota_definition_1.valid_between.lower.month,
        "start_date_2": quota_definition_1.valid_between.lower.year,
        "end_date_0": quota_definition_1.valid_between.upper.day,
        "end_date_1": quota_definition_1.valid_between.upper.month,
        "end_date_2": quota_definition_1.valid_between.upper.year,
        "measurement_unit": quota_definition_1.measurement_unit,
        "volume": quota_definition_1.volume,
        "initial_volume": quota_definition_1.initial_volume,
        "coefficient": 1.5,
        "relationship_type": "NM",
    }
    session_request.session["staged_definition_data"] = staged_definition_data

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionsUpdatesForm(
            request=session_request,
            data=data,
            pk=quota_definition_1.pk,
        )
        assert not form.is_valid()
        assert (
            "QA5: Where the relationship type is Normal, the coefficient value must be 1"
            in form.errors["__all__"]
        )


def test_quota_duplicator_form_clean_QA5_eq(session_request, quota_definition_1):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        }
    ]

    data = {
        "start_date_0": quota_definition_1.valid_between.lower.day,
        "start_date_1": quota_definition_1.valid_between.lower.month,
        "start_date_2": quota_definition_1.valid_between.lower.year,
        "end_date_0": quota_definition_1.valid_between.upper.day,
        "end_date_1": quota_definition_1.valid_between.upper.month,
        "end_date_2": quota_definition_1.valid_between.upper.year,
        "measurement_unit": quota_definition_1.measurement_unit,
        "volume": quota_definition_1.volume,
        "initial_volume": quota_definition_1.initial_volume,
        "coefficient": 1,
        "relationship_type": "EQ",
    }
    session_request.session["staged_definition_data"] = staged_definition_data

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionsUpdatesForm(
            request=session_request,
            data=data,
            pk=quota_definition_1.pk,
        )
        assert not form.is_valid()
        assert (
            "QA5: Where the relationship type is Equivalent, the coefficient value must be something other than 1"
            in form.errors["__all__"]
        )
