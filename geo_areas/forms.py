from crispy_forms_gds.layout import Field
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.formsets import formset_factory

from common.forms import CreateDescriptionForm
from common.forms import FormSet
from common.forms import delete_form_for
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.util import with_latest_description_string
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


GeographicalAreaDeleteForm = delete_form_for(GeographicalArea)


GeographicalAreaDescriptionDeleteForm = delete_form_for(GeographicalAreaDescription)
