import pytest
from django import forms

from common.forms import BindNestedFormMixin
from common.forms import FormSet
from common.forms import RadioNested
from common.forms import formset_add_or_delete
from common.forms import formset_factory
from common.forms import unprefix_formset_data


class GeoGroupTestForm(forms.Form):
    field = forms.CharField(required=True)


GeoGroupTestFormset = formset_factory(
    GeoGroupTestForm,
    prefix="geo_group_formset",
    formset=FormSet,
    min_num=1,
    max_num=10,
    extra=1,
    validate_min=True,
    validate_max=True,
)


class RadioNestedForm(BindNestedFormMixin, forms.Form):
    ERGA_OMNES = "erga_omnes"
    GROUP = "geo_group"
    COUNTRY = "country"
    geo_area = RadioNested(
        choices=[
            (ERGA_OMNES, "Erga omnes (all countries)"),  # /PS-IGNORE
            (GROUP, "A group of countries"),
            (COUNTRY, "Specific countries or regions"),
        ],
        nested_forms={
            ERGA_OMNES: [],
            GROUP: [GeoGroupTestForm],
            COUNTRY: [GeoGroupTestFormset],
        },
    )
    other_field = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_nested_forms(*args, **kwargs)


def test_radio_nested_form_required_field():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": "",
        },
    )
    assert not form.is_valid()
    assert "geo_area" in form.errors

    form = RadioNestedForm(
        {
            "other_field": "",
            "geo_area": RadioNestedForm.GROUP,
        },
    )
    assert not form.is_valid()
    assert "other_field" in form.errors
    assert "geo_area" in form.errors


def test_radio_nested_form_valid():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.ERGA_OMNES,
        },
    )
    assert form.is_valid()

    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.GROUP,
            "field": "EU",
        },
    )
    assert form.is_valid()


def test_radio_nested_form_nested_formset_valid_initial_data():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.COUNTRY,
            "geo_group_formset-0-field": "France",
            "geo_group_formset-1-field": "Germany",
        },
        initial={
            "geo_group_formset": [
                {
                    "field": "France",
                },
                {
                    "field": "Germany",
                },
            ],
        },
    )
    assert form.is_valid()


def test_radio_nested_form_nested_formset_invalid_add():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.COUNTRY,
            "geo_group_formset-0-field": "France",
            "geo_group_formset-1-field": "Germany",
            "geo_group_formset-ADD": "1",
        },
    )
    assert not form.is_valid()


def test_radio_nested_form_nested_formset_required_field():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.GROUP,
            "field": "",
        },
    )
    assert not form.is_valid()
    assert "geo_area" in form.errors
    assert (
        "field" in form.fields["geo_area"].nested_forms[RadioNestedForm.GROUP][0].errors
    )


def test_radio_nested_form_nested_formset_min_forms():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.COUNTRY,
            "geo_group_formset-0-field": "",
            "geo_group_formset-TOTAL_FORMS": "1",
            "geo_group_formset-INITIAL_FORMS": "0",
        },
    )
    assert form.is_valid() is False
    assert "geo_area" in form.errors
    assert (
        "Please submit at least 1 form."
        in form.fields["geo_area"]
        .nested_forms[RadioNestedForm.COUNTRY][0]
        .non_form_errors()
    )


def test_radio_nested_form_nested_formset_cleaned_data():
    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.GROUP,
            "field": "fooooo",
        },
    )
    assert form.is_valid() is True
    assert form.cleaned_data == {
        "other_field": "thing",
        "geo_area": RadioNestedForm.GROUP,
        "field": "fooooo",
    }


@pytest.mark.parametrize(
    "data,exp",
    [
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-1-applicable_duty": "test2",
                "measure-conditions-formset-2-applicable_duty": "test3",
                "measure-conditions-formset-3-applicable_duty": "test4",
            },
            [
                {
                    "applicable_duty": "test1",
                },
                {
                    "applicable_duty": "test2",
                },
                {
                    "applicable_duty": "test3",
                },
                {
                    "applicable_duty": "test4",
                },
            ],
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
            },
            [
                {
                    "applicable_duty": "test1",
                },
            ],
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-__prefix__-applicable_duty": "test2",
                "measure-conditions-formset-ADD": "1",
            },
            [
                {
                    "applicable_duty": "test1",
                },
                {
                    "applicable_duty": "test2",
                },
            ],
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-__prefix__-applicable_duty": "test2",
                "measure-conditions-formset-0-DELETE": "1",
            },
            [
                {
                    "applicable_duty": "test1",
                },
                {
                    "applicable_duty": "test2",
                },
            ],
        ),
    ],
)
def test_unprefix_formset_data(data, exp):
    base_data = {
        "id": 12,
        "update_type": 3,
        "version_group": 1,
        "trackedmodel_ptr": 12,
        "measure_type": 9,
        "geographical_area": 1,
        "goods_nomenclature": 3,
        "additional_code": None,
        "dead_additional_code": None,
        "order_number": None,
        "dead_order_number": None,
        "reduction": 1,
        "generating_regulation": 11,
        "terminating_regulation": None,
        "stopped": False,
        "footnotes": [],
        "geo_area": "COUNTRY",
        "country_region-geographical_area_country_or_region": 1,
        "start_date_0": 12,
        "start_date_1": 4,
        "start_date_2": 2023,
        "measure-conditions-formset-TOTAL_FORMS": 1,
        "measure-conditions-formset-INITIAL_FORMS": 0,
        "measure-conditions-formset-MIN_NUM_FORMS": 0,
        "measure-conditions-formset-MAX_NUM_FORMS": 1000,
    }

    assert (
        unprefix_formset_data("measure-conditions-formset", {**base_data, **data})
        == exp
    )


@pytest.mark.parametrize(
    "data,exp",
    [
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-1-applicable_duty": "test2",
                "measure-conditions-formset-2-applicable_duty": "test3",
                "measure-conditions-formset-3-applicable_duty": "test4",
            },
            False,
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
            },
            False,
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-__prefix__-applicable_duty": "test2",
                "measure-conditions-formset-ADD": "1",
            },
            True,
        ),
        (
            {
                "measure-conditions-formset-0-applicable_duty": "test1",
                "measure-conditions-formset-__prefix__-applicable_duty": "test2",
                "measure-conditions-formset-0-DELETE": "1",
            },
            True,
        ),
    ],
)
def test_formset_add_or_delete(data, exp):
    assert formset_add_or_delete(["measure-conditions-formset"], data) == exp
