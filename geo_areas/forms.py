from crispy_forms_gds.layout import Field
from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from common.forms import CreateDescriptionForm
from common.forms import delete_form_for
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.validators import AreaCode


class GeographicalAreaCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            0,
            Field(
                "described_geographicalarea",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Geographical area description"

    class Meta:
        model = GeographicalAreaDescription
        fields = ("described_geographicalarea", "description", "validity_start")


class GeographicalAreaFormMixin(forms.Form):
    """
    Adds a geographical area selection field.

    Consists of a radio group of 3 sections:
      1. Erga Omnes (all countries), containing a subfield allowing the selection of
         multiple geographical areas to exclude,
      2. A group of countries, containing an autocomplete field for the primary group, and
         another subfield for exclusions from that group,
      3. A single country or region, containing an autocomplete field for the country or
         region
    """

    class GeoAreaType(models.TextChoices):
        ERGA_OMNES = "ERGA_OMNES", "All countries (erga omnes)"
        GROUP = "GROUP", "A group of countries"
        COUNTRY = "COUNTRY", "A single country or region"

    geo_area_type = forms.ChoiceField(choices=GeoAreaType.choices, required=False)
    erga_omnes_exclusions = forms.ModelMultipleChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="To exclude countries, enter them below.",
        required=False,
    )
    geo_group = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country group.",
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )
    geo_group_exclusions = forms.ModelMultipleChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="Select country exclusions.",
        required=False,
    )
    geo_area = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country or region.",
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )

    def __init__(self, *args, **kwargs):
        tx = kwargs.pop("transaction", None)
        self.transaction = tx
        super().__init__(*args, **kwargs)

        self.fields["geo_group"].queryset = (
            GeographicalArea.objects.filter(
                area_code=AreaCode.GROUP,
            )
            .as_at_today()
            .approved_up_to_transaction(tx)
            .with_latest_links("descriptions")
            .prefetch_related("descriptions")
            .order_by("descriptions__description")
            # descriptions__description" should make this implicitly distinct()
        )
        # self.fields[
        #     "geo_group_exclusions"
        # ].queryset = GeographicalArea.objects.approved_up_to_transaction(tx)
        self.fields["geo_area"].queryset = (
            GeographicalArea.objects.exclude(
                area_code=AreaCode.GROUP,
            )
            .as_at_today()
            .approved_up_to_transaction(tx)
            .with_latest_links("descriptions")
            .prefetch_related("descriptions")
            .order_by("descriptions__description")
            # descriptions__description" should make this implicitly distinct()
        )

        for field in ["geo_group", "geo_area"]:
            self.fields[
                field
            ].label_from_instance = lambda obj: obj.structure_description

    def clean(self):
        cleaned_data = super().clean()

        geo_area_type = cleaned_data.pop("geo_area_type")
        erga_omnes_exclusions = cleaned_data.pop("erga_omnes_exclusions", None)
        geo_group = cleaned_data.pop("geo_group", None)
        geo_group_exclusions = cleaned_data.pop("geo_group_exclusions", None)
        geo_area = cleaned_data.pop("geo_area", None)

        if geo_area_type == self.GeoAreaType.ERGA_OMNES:
            cleaned_data["geographical_area"] = (
                GeographicalArea.objects.approved_up_to_transaction(self.transaction)
                .erga_omnes()
                .get()
            )
            cleaned_data["geo_area_exclusions"] = erga_omnes_exclusions

        self.fields["geo_area_type"].initial = geo_area_type

        if geo_area_type == self.GeoAreaType.GROUP:
            if not geo_group:
                raise ValidationError({"geo_group": "A country group is required."})
            cleaned_data["geographical_area"] = geo_group
            cleaned_data["geo_area_exclusions"] = geo_group_exclusions

        if geo_area_type == self.GeoAreaType.COUNTRY:
            if not geo_area:
                raise ValidationError({"geo_area": "A country or region is required."})
            cleaned_data["geographical_area"] = geo_area

        self.fields["geo_group"].initial = geo_group.pk if geo_group else None
        self.fields["geo_area"].initial = geo_area.pk if geo_area else None

        return cleaned_data


class GeographicalAreaSelect(Field):
    template = "components/geographical_area_select/template.jinja"


GeographicalAreaDeleteForm = delete_form_for(GeographicalArea)


GeographicalAreaDescriptionDeleteForm = delete_form_for(GeographicalAreaDescription)
