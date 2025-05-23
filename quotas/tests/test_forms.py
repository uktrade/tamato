import datetime
import decimal

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
from quotas import forms
from quotas import models
from quotas import validators
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
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
        form = forms.QuotaDefinitionCreateForm(
            data=data,
            buttons={
                "submit": "Submit",
                "link_text": "Cancel",
                "link": "/workbaskets/current",
            },
        )
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
        form = forms.QuotaDefinitionCreateForm(
            data=data,
            buttons={
                "submit": "Submit",
                "link_text": "Cancel",
                "link": "/workbaskets/current",
            },
        )
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


def test_quota_create_form_extra_errors(session_request_with_workbasket):
    geo_group = factories.GeoGroupFactory.create()
    area_1 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_2 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_3 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    non_member = factories.GeographicalAreaFactory.create()

    data = {
        "order_number": "054000",
        "mechanism": validators.AdministrationMechanism.LICENSED.value,
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "origins-0-geographical_area": geo_group.pk,
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

    with override_current_transaction(non_member.transaction):
        form = forms.QuotaOrderNumberCreateForm(
            data=data,
            request=session_request_with_workbasket,
            initial={},
            geo_area_options=[],
            exclusions_options=[],
            groups_with_members=[],
        )
        assert not form.is_valid()
        assert form.errors["origins-0-exclusions-0-geographical_area"] == [
            "Select a valid choice. That choice is not one of the available choices.",
        ]
        assert form.errors["origins-0-end_date"] == [
            "The end date must be the same as or after the start date.",
        ]


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
    """Provides a main quota order number for use across the fixtures and
    following tests."""
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def quota_definition_1(main_quota_order_number, date_ranges) -> QuotaDefinition:
    """Provides a definition, linked to the main_quota_order_number to be used
    across the following tests."""
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.normal,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )


@pytest.fixture
def sub_quota(main_quota_order_number, date_ranges) -> QuotaDefinition:
    """
    Provides a definition to be used as a sub_quota.

    It has a valid between in the future as otherwise only the end date can be
    edited.
    """
    return factories.QuotaDefinitionFactory.create(
        order_number=main_quota_order_number,
        valid_between=date_ranges.future,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )


def test_select_sub_quota_form_set_staged_definition_data(
    quota_definition_1,
    session_request,
):
    session_request.path = ""
    form = forms.SelectSubQuotaDefinitionsForm(
        request=session_request,
        prefix="select_definition_periods",
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
    date_ranges,
    session_request,
    quota_definition_1,
):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        },
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
            "QA2: Validity period for sub-quota must be within the validity period of the main quota"
            in form.errors["__all__"]
        )


def test_quota_duplicator_form_clean_QA3(session_request, quota_definition_1):
    staged_definition_data = [
        {
            "main_definition": quota_definition_1.pk,
            "sub_definition_staged_data": serialize_duplicate_data(quota_definition_1),
        },
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
        },
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
        },
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
        },
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


def test_sub_quota_update_form_valid(session_request_with_workbasket, sub_quota):
    """Test that the sub-quota update form initialises correctly and is valid
    when valid data is passed in."""
    main_quota = factories.QuotaDefinitionFactory.create(
        volume=9999,
        initial_volume=9999,
        measurement_unit=sub_quota.measurement_unit,
    )
    association = factories.QuotaAssociationFactory.create(
        sub_quota=sub_quota,
        main_quota=main_quota,
        sub_quota_relation_type="EQ",
        coefficient=1.5,
    )
    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionAssociationUpdateForm(
            instance=sub_quota,
            request=session_request_with_workbasket,
            sid=sub_quota.sid,
        )
        assert float(form.fields["coefficient"].initial) == association.coefficient
        assert (
            form.fields["relationship_type"].initial
            == association.sub_quota_relation_type
        )
        assert form.fields["measurement_unit"].initial == sub_quota.measurement_unit
        assert form.fields["initial_volume"].initial == sub_quota.initial_volume
        assert form.fields["volume"].initial == sub_quota.volume
        assert form.fields["start_date"].initial == sub_quota.valid_between.lower
        assert form.fields["end_date"].initial == sub_quota.valid_between.upper

    data = {
        "start_date_0": sub_quota.valid_between.lower.day,
        "start_date_1": sub_quota.valid_between.lower.month,
        "start_date_2": sub_quota.valid_between.lower.year,
        "end_date_0": sub_quota.valid_between.upper.day,
        "end_date_1": sub_quota.valid_between.upper.month,
        "end_date_2": sub_quota.valid_between.upper.year,
        "measurement_unit": sub_quota.measurement_unit,
        "volume": 100,
        "initial_volume": 100,
        "coefficient": 1.5,
        "relationship_type": "EQ",
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionAssociationUpdateForm(
            request=session_request_with_workbasket,
            data=data,
            sid=sub_quota.sid,
            instance=sub_quota,
        )
        assert form.is_valid()


def test_sub_quota_update_form_invalid(session_request_with_workbasket, sub_quota):
    """Test that the sub-quota update form is invalid when invalid data is
    passed in."""
    main_quota = factories.QuotaDefinitionFactory.create(
        volume=9999,
        initial_volume=9999,
        measurement_unit=sub_quota.measurement_unit,
    )
    factories.QuotaAssociationFactory.create(
        sub_quota=sub_quota,
        main_quota=main_quota,
        sub_quota_relation_type="EQ",
        coefficient=1.5,
    )

    data = {
        "start_date_0": sub_quota.valid_between.lower.day,
        "start_date_1": sub_quota.valid_between.lower.month,
        "start_date_2": sub_quota.valid_between.lower.year,
        "end_date_0": sub_quota.valid_between.upper.day,
        "end_date_1": sub_quota.valid_between.upper.month,
        "end_date_2": sub_quota.valid_between.upper.year,
        "measurement_unit": sub_quota.measurement_unit,
        "volume": 100,
        "initial_volume": 100,
        "coefficient": 1,
        "relationship_type": "EQ",
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionAssociationUpdateForm(
            request=session_request_with_workbasket,
            data=data,
            sid=sub_quota.sid,
            instance=sub_quota,
        )
        assert not form.is_valid()
        assert (
            "QA5: Where the relationship type is Equivalent, the coefficient value must be something other than 1"
            in form.errors["__all__"]
        )


def test_only_end_date_editable_for_active_definitions(
    date_ranges,
    session_request_with_workbasket,
):
    """Test that it is not possible for a user to edit any field other than the
    end-date for a sub-quota which has already begun."""
    active_sub_quota = factories.QuotaDefinitionFactory.create(
        order_number=factories.QuotaOrderNumberFactory.create(),
        valid_between=date_ranges.normal,
        is_physical=True,
        initial_volume=1234,
        volume=1234,
        measurement_unit=factories.MeasurementUnitFactory(),
    )
    main_quota = factories.QuotaDefinitionFactory.create(
        volume=9999,
        initial_volume=9999,
        measurement_unit=active_sub_quota.measurement_unit,
    )
    factories.QuotaAssociationFactory.create(
        sub_quota=active_sub_quota,
        main_quota=main_quota,
        sub_quota_relation_type="EQ",
        coefficient=1.5,
    )

    new_measurement_unit = factories.MeasurementUnitFactory.create()

    data = {
        "end_date_0": 1,
        "end_date_1": 1,
        "end_date_2": 2035,
        "measurement_unit": new_measurement_unit,
        "volume": 100,
        "coefficient": 1,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.SubQuotaDefinitionAssociationUpdateForm(
            request=session_request_with_workbasket,
            data=data,
            sid=active_sub_quota.sid,
            instance=active_sub_quota,
        )
        assert form.is_valid()
        cleaned_data = form.cleaned_data
        assert not cleaned_data["coefficient"] == 1
        assert not cleaned_data["volume"] == 100
        assert not cleaned_data["measurement_unit"] == new_measurement_unit
        assert cleaned_data["valid_between"].upper == datetime.date(2035, 1, 1)


def test_quota_association_edit_form_valid():
    "Test that the quota association edit form is valid when valid data is passed in."
    association = factories.QuotaAssociationFactory.create(
        coefficient=1.67,
        sub_quota_relation_type="EQ",
    )

    data = {
        "coefficient": 1.5,
        "sub_quota_relation_type": "EQ",
        "main_quota": association.main_quota,
        "sub_quota": association.sub_quota,
    }
    form = forms.QuotaAssociationUpdateForm(data=data, instance=association)

    assert form.is_valid()


def test_quota_association_edit_form_invalid():
    "Test that the quota association edit form is invalid when invalid data is passed in."
    association = factories.QuotaAssociationFactory.create(
        coefficient=1.67,
        sub_quota_relation_type="EQ",
    )

    data = {
        "coefficient": "String",
        "sub_quota_relation_type": "Equivalent",
        "main_quota": association.main_quota,
        "sub_quota": association.sub_quota,
    }
    form = forms.QuotaAssociationUpdateForm(data=data, instance=association)
    assert (
        "Select a valid choice. Equivalent is not one of the available choices."
        in form.errors["sub_quota_relation_type"]
    )
    assert "Enter a number." in form.errors["coefficient"]
    assert not form.is_valid()


def test_quota_suspension_update_form_valid(date_ranges):
    "Test that the quota suspension update form is valid when correct data is passed in"
    suspension = factories.QuotaSuspensionFactory.create(
        valid_between=date_ranges.normal,
    )
    current_validity = suspension.valid_between
    data = {
        "start_date_0": current_validity.lower.day,
        "start_date_1": current_validity.lower.month,
        "start_date_2": current_validity.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "description": "New description",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaSuspensionUpdateForm(
            data=data,
            instance=suspension,
        )
        assert form.is_valid()


def test_quota_suspension_update_form_invalid(date_ranges):
    "Test that the quota suspension update form is invalid when the validity period does not span the validity of the definition"
    definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.normal,
    )
    suspension = factories.QuotaSuspensionFactory.create(
        quota_definition=definition,
        valid_between=date_ranges.normal,
    )
    data = {
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaSuspensionUpdateForm(
            data=data,
            instance=suspension,
        )
        assert not form.is_valid()
        assert (
            f"The start and end date must sit within the selected quota definition's start and end date ({definition.valid_between.lower} - {definition.valid_between.upper})"
            in form.errors["__all__"]
        )


def test_quota_blocking_update_form_valid(date_ranges):
    "Test that the quota blocking update form is valid when correct data is passed in"
    blocking = factories.QuotaBlockingFactory.create(
        valid_between=date_ranges.future,
    )
    current_validity = blocking.valid_between
    data = {
        "start_date_0": current_validity.lower.day,
        "start_date_1": current_validity.lower.month,
        "start_date_2": current_validity.lower.year,
        "blocking_period_type": blocking.blocking_period_type,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "description": "New description",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaBlockingUpdateForm(
            data=data,
            instance=blocking,
        )
        assert form.is_valid()


def test_quota_blocking_update_form_invalid(date_ranges):
    "Test that the quota blocking update form is invalid when the validity period does not span the validity of the definition"
    definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.future,
    )
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition=definition,
        valid_between=date_ranges.future,
    )
    data = {
        "start_date_0": date_ranges.earlier.lower.day,
        "start_date_1": date_ranges.earlier.lower.month,
        "start_date_2": date_ranges.earlier.lower.year,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.QuotaBlockingUpdateForm(
            data=data,
            instance=blocking,
        )
        assert not form.is_valid()
        assert (
            f"The start and end date must sit within the selected quota definition's start and end date ({definition.valid_between.lower} - {definition.valid_between.upper})"
            in form.errors["__all__"]
        )


@pytest.fixture
def quota() -> models.QuotaOrderNumber:
    """Provides a main quota order number for use across the fixtures and
    following tests."""
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def bulk_create_start_form(
    session_request,
) -> forms.BulkQuotaDefinitionCreateStartForm:
    return forms.BulkQuotaDefinitionCreateStartForm(
        request=session_request,
        prefix="definition_period_info",
    )


@pytest.fixture
def bulk_create_definition_form(
    session_request,
) -> forms.QuotaDefinitionBulkCreateDefinitionInformation:
    return forms.QuotaDefinitionBulkCreateDefinitionInformation(
        request=session_request,
        prefix="definition_period_info",
    )


def test_quota_definition_bulk_create_definition_start_form(
    session_request,
    quota,
    bulk_create_start_form,
):

    initial_data = {
        "quota_order_number": quota,
    }
    with override_current_transaction(Transaction.objects.last()):
        bulk_create_start_form.save_quota_order_number_to_session(initial_data)

    assert session_request.session["quota_order_number_pk"] == quota.pk
    assert session_request.session["quota_order_number"] == quota.order_number


def test_quota_definition_bulk_create_start_is_valid(
    quota,
    session_request_with_workbasket,
):
    initial_data = {"quota_order_number": quota}
    form = forms.BulkQuotaDefinitionCreateStartForm(
        data=initial_data,
        request=session_request_with_workbasket,
    )
    assert form.is_valid()

    initial_data = {}

    form = forms.BulkQuotaDefinitionCreateStartForm(
        data=initial_data,
        request=session_request_with_workbasket,
    )
    assert not form.is_valid()
    assert f"A quota order number must be selected" in form.errors["__all__"]


def test_quota_definition_bulk_create_definition_info_frequencies(
    quota,
    session_request,
    bulk_create_start_form,
    bulk_create_definition_form,
):
    measurement_unit = factories.MeasurementUnitFactory()
    measurement_unit_qualifier = factories.MeasurementUnitQualifierFactory.create()
    initial_data = {
        "quota_order_number": quota,
    }
    form_data = {
        "maximum_precision": 3,
        "valid_between": TaricDateRange(
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        ),
        "volume": 600.000,
        "initial_volume": 500.000,
        "volume-change": "no_change",
        "volume_change_type": "no_change",
        "volume_change_value": None,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 90,
        "quota_critical": "False",
        "instance_count": 3,
        "frequency": 1,
        "description": "This is a description",
        "measurement_unit_qualifier": measurement_unit_qualifier,
    }

    # tests with annual recurrance
    with override_current_transaction(Transaction.objects.last()):
        bulk_create_start_form.save_quota_order_number_to_session(initial_data)
        bulk_create_definition_form.save_definition_data_to_session(form_data)
        assert session_request.session["quota_order_number"] == quota.order_number
        # check that the length staged_definitions matches the initial_info['instance_count']
        assert (
            len(session_request.session["staged_definition_data"])
            == form_data["instance_count"]
        )
        assert (
            session_request.session["staged_definition_data"][1]["start_date"]
            == "2026-01-01"
        )
        assert (
            session_request.session["staged_definition_data"][1]["end_date"]
            == "2026-12-31"
        )
        assert (
            session_request.session["staged_definition_data"][2]["start_date"]
            == "2027-01-01"
        )
        assert (
            session_request.session["staged_definition_data"][2]["end_date"]
            == "2027-12-31"
        )
    # tests bi-annual recurrance
    form_data["frequency"] = 2
    with override_current_transaction(Transaction.objects.last()):
        bulk_create_definition_form.save_definition_data_to_session(form_data)
        # check that the length staged_definitions still matches the initial_info['instance_count']
        assert (
            len(session_request.session["staged_definition_data"])
            == form_data["instance_count"]
        )
        # check that the frequency is now biannual
        assert (
            session_request.session["staged_definition_data"][1]["start_date"]
            == "2026-01-01"
        )
        assert (
            session_request.session["staged_definition_data"][1]["end_date"]
            == "2026-06-30"
        )
        assert (
            session_request.session["staged_definition_data"][2]["start_date"]
            == "2026-07-01"
        )
        assert (
            session_request.session["staged_definition_data"][2]["end_date"]
            == "2026-12-31"
        )

    # check quarterly recurrance
    form_data["frequency"] = 3
    with override_current_transaction(Transaction.objects.last()):
        bulk_create_definition_form.save_definition_data_to_session(form_data)
        # check that the length staged_definitions still matches the initial_info['instance_count']
        assert (
            len(session_request.session["staged_definition_data"])
            == form_data["instance_count"]
        )
        assert (
            session_request.session["staged_definition_data"][1]["start_date"]
            == "2026-01-01"
        )
        assert (
            session_request.session["staged_definition_data"][1]["end_date"]
            == "2026-03-31"
        )
        assert (
            session_request.session["staged_definition_data"][2]["start_date"]
            == "2026-04-01"
        )
        assert (
            session_request.session["staged_definition_data"][2]["end_date"]
            == "2026-06-30"
        )


@pytest.mark.parametrize(
    "change_type, change_value, result_1, result_2",
    [
        ("no_change", None, "100.00", "100.00"),
        ("increase_percentage", 4.5, "104.50", "109.20"),
        ("decrease_percentage", 7.7, "92.30", "85.19"),
        ("increase_quantity", 10, "110.00", "120.00"),
        ("decrease_quantity", 5, "95.00", "90.00"),
    ],
)
def test_quota_definition_bulk_create_volume_changes_saves_to_session(
    quota,
    session_request,
    bulk_create_start_form,
    bulk_create_definition_form,
    change_type,
    change_value,
    result_1,
    result_2,
):
    measurement_unit = factories.MeasurementUnitFactory()
    measurement_unit_qualifier = factories.MeasurementUnitQualifierFactory.create()
    initial_data = {
        "quota_order_number": quota,
    }
    form_data = {
        "maximum_precision": 3,
        "valid_between": TaricDateRange(
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        ),
        "volume": 100.000,
        "initial_volume": 100.000,
        "volume_change_type": change_type,
        "volume_change_value": change_value,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 90,
        "quota_critical": "False",
        "instance_count": 3,
        "frequency": 1,
        "description": "This is a description",
        "measurement_unit_qualifier": measurement_unit_qualifier,
    }

    with override_current_transaction(Transaction.objects.last()):
        bulk_create_start_form.save_quota_order_number_to_session(initial_data)
        bulk_create_definition_form.save_definition_data_to_session(form_data)
        assert (
            len(session_request.session["staged_definition_data"])
            == form_data["instance_count"]
        )
        assert (
            session_request.session["staged_definition_data"][1]["volume"] == result_1
        )
        assert (
            session_request.session["staged_definition_data"][2]["volume"] == result_2
        )


@pytest.mark.parametrize(
    "change_type",
    [
        "increase_percentage",
        "decrease_percentage",
        "increase_quantity",
        "decrease_quantity",
    ],
)
def test_quota_definition_bulk_create_volume_changes_no_values(
    session_request_with_workbasket,
    change_type,
    date_ranges,
):
    measurement_unit = factories.MeasurementUnitFactory()
    measurement_unit_qualifier = factories.MeasurementUnitQualifierFactory.create()

    form_data = {
        "maximum_precision": 3,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "volume": 100.000,
        "initial_volume": 100.000,
        "volume-change": change_type,
        "volume_change_type": change_type,
        "increase_percentage": None,
        "decrease_percentage": None,
        "increase_quantity": None,
        "decrease_quantity": None,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 90,
        "quota_critical": "False",
        "instance_count": 3,
        "frequency": 1,
        "description": "This is a description",
        "measurement_unit_qualifier": measurement_unit_qualifier,
    }

    form = forms.QuotaDefinitionBulkCreateDefinitionInformation(
        data=form_data,
        request=session_request_with_workbasket,
    )
    with override_current_transaction(Transaction.objects.last()):
        assert not form.is_valid()
        assert (
            "A value must be provided for the volume change option you have selected"
            in form.errors["__all__"]
        )


@pytest.mark.parametrize(
    "change_type, change_value",
    [
        ("increase_percentage", 4.5),
        ("decrease_percentage", 7.7),
        ("increase_quantity", 10),
        ("decrease_quantity", 5),
    ],
)
def test_quota_definition_bulk_create_volume_changes_not_annually_recurring(
    session_request_with_workbasket,
    change_type,
    change_value,
    date_ranges,
):
    measurement_unit = factories.MeasurementUnitFactory()
    measurement_unit_qualifier = factories.MeasurementUnitQualifierFactory.create()
    form_data = {
        "maximum_precision": 3,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "volume": 100.000,
        "initial_volume": 100.000,
        "volume-change": change_type,
        "volume_change_type": change_type,
        "increase_percentage": change_value,
        "decrease_percentage": change_value,
        "increase_quantity": change_value,
        "decrease_quantity": change_value,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 90,
        "quota_critical": "False",
        "instance_count": 3,
        "frequency": 2,
        "description": "This is a description",
        "measurement_unit_qualifier": measurement_unit_qualifier,
    }

    form = forms.QuotaDefinitionBulkCreateDefinitionInformation(
        data=form_data,
        request=session_request_with_workbasket,
    )
    with override_current_transaction(Transaction.objects.last()):
        assert not form.is_valid()
        assert (
            "Automatically increasing or decreasing the volume between definition periods is only available for definition periods that span the entire year or if there is only one definition period in the year."
            in form.errors["__all__"]
        )


def test_bulk_create_update_definition_data_populates_parent_data(
    quota,
    session_request,
    bulk_create_start_form,
):
    definition_form = forms.QuotaDefinitionBulkCreateDefinitionInformation(
        request=session_request,
        prefix="review",
    )
    # Set up the main definition, saving additional data to session
    measurement_unit = factories.MeasurementUnitFactory()
    initial_data = {
        "quota_order_number": quota,
    }
    form_data = {
        "maximum_precision": 3,
        "valid_between": TaricDateRange(
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        ),
        "volume": "600.000",
        "initial_volume": "500.000",
        "volume_change_type": "no_change",
        "volume_change_value": None,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": "90",
        "quota_critical": "False",
        "description": "This is a description",
        "instance_count": 3,
        "frequency": 1,
    }

    bulk_create_start_form.save_quota_order_number_to_session(initial_data)
    definition_form.save_definition_data_to_session(form_data)
    update_form = forms.BulkDefinitionUpdateData(
        request=session_request,
        pk=2,
        buttons={
            "submit": "Save and continue",
            "link_text": "Discard changes",
            "link": "/quotas/quota_definitions/bulk_create/review",
        },
    )

    assert update_form.fields["volume"].initial == decimal.Decimal(form_data["volume"])
    assert update_form.fields["initial_volume"].initial == decimal.Decimal(
        form_data["initial_volume"],
    )
    assert (
        update_form.fields["measurement_unit"].initial == form_data["measurement_unit"]
    )
    assert update_form.fields["description"].initial == form_data["description"]


def test_bulk_create_update_definition_data_updates_data(
    quota,
    session_request,
    bulk_create_start_form,
    bulk_create_definition_form,
):
    measurement_unit = factories.MeasurementUnitFactory()
    initial_data = {
        "quota_order_number": quota,
    }
    definition_data = {
        "maximum_precision": 3,
        "valid_between": TaricDateRange(
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        ),
        "volume": 600.000,
        "initial_volume": 500.000,
        "volume_change_type": "no_change",
        "volume_change_value": None,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 90,
        "quota_critical": "False",
        "instance_count": 3,
        "frequency": 1,
        "description": "This is a description",
    }

    bulk_create_start_form.save_quota_order_number_to_session(initial_data)
    bulk_create_definition_form.save_definition_data_to_session(definition_data)

    update_form_data = {
        "id": 1,
        "maximum_precision": 3,
        "valid_between": TaricDateRange(
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        ),
        "volume": 500,
        "initial_volume": 400,
        "measurement_unit": measurement_unit,
        "quota_critical_threshold": 91,
        "quota_critical": "False",
        "description": "This is a new description",
    }

    update_form = forms.BulkDefinitionUpdateData(
        request=session_request,
        pk=2,
        buttons={
            "submit": "Save and continue",
            "link_text": "Discard changes",
            "link": "/quotas/quota_definitions/bulk_create/review",
        },
    )
    update_form.update_definition_data_in_session(cleaned_data=update_form_data)

    assert session_request.session["staged_definition_data"][1]["volume"] == str(
        update_form_data["volume"],
    )
    assert session_request.session["staged_definition_data"][1][
        "initial_volume"
    ] == str(update_form_data["initial_volume"])
    assert (
        session_request.session["staged_definition_data"][1]["description"]
        == update_form_data["description"]
    )


def test_quota_definition_bulk_create_definition_is_valid(
    session_request_with_workbasket,
    date_ranges,
):
    measurement_unit = factories.MeasurementUnitFactory()
    measurement_unit_qualifier = factories.MeasurementUnitQualifierFactory()

    form_data = {
        "maximum_precision": 3,
        "start_date_0": date_ranges.normal.lower.day,
        "start_date_1": date_ranges.normal.lower.month,
        "start_date_2": date_ranges.normal.lower.year,
        "end_date_0": date_ranges.normal.upper.day,
        "end_date_1": date_ranges.normal.upper.month,
        "end_date_2": date_ranges.normal.upper.year,
        "volume": "600.000",
        "initial_volume": "500.000",
        "volume-change": "increase_percentage",
        "volume_change_type": "increase_percentage",
        "increase_percentage": 10,
        "decrease_percentage": None,
        "increase_quantity": None,
        "decrease_quantity": None,
        "measurement_unit": measurement_unit,
        "measurement_unit_qualifier": measurement_unit_qualifier,
        "quota_critical_threshold": "90",
        "quota_critical": "False",
        "frequency": 1,
    }

    form = forms.QuotaDefinitionBulkCreateDefinitionInformation(
        data=form_data,
        request=session_request_with_workbasket,
    )
    with override_current_transaction(Transaction.objects.last()):
        assert not form.is_valid()
        assert (
            form.errors["instance_count"][0]
            == "Enter the number of definition periods to create"
        )

    form_data["instance_count"] = 3

    form = forms.QuotaDefinitionBulkCreateDefinitionInformation(
        data=form_data,
        request=session_request_with_workbasket,
    )

    with override_current_transaction(Transaction.objects.last()):
        assert form.is_valid()
