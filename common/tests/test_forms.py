from django import forms

from common.forms import BindNestedFormMixin
from common.forms import FormSet
from common.forms import RadioNested
from common.forms import formset_factory


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


def test_radio_nested_form_validation():
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
            "other_field": "thing",
            "geo_area": RadioNestedForm.ERGA_OMNES,
        },
    )
    assert form.is_valid()

    form = RadioNestedForm(
        {
            "other_field": "",
            "geo_area": RadioNestedForm.GROUP,
        },
    )
    assert form.is_valid() is False
    assert "other_field" in form.errors
    assert "geo_area" in form.errors

    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.GROUP,
            "field": "France",
        },
    )
    assert form.is_valid()

    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.COUNTRY,
            "geo_group_formset-0-field": "France",
            "geo_group_formset-1-field": "Germany",
        },
    )
    assert form.is_valid()

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

    form = RadioNestedForm(
        {
            "other_field": "thing",
            "geo_area": RadioNestedForm.GROUP,
            "field": "",
        },
    )
    assert form.is_valid() is False
    assert "geo_area" in form.errors
    assert (
        "field" in form.fields["geo_area"].nested_forms[RadioNestedForm.GROUP][0].errors
    )

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
        "Please submit 1 or more forms."
        in form.fields["geo_area"]
        .nested_forms[RadioNestedForm.COUNTRY][0]
        .non_form_errors()
    )

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
