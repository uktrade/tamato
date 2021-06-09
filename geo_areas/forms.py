from crispy_forms_gds.layout import Field

from common.forms import CreateDescriptionForm
from geo_areas import models


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
        model = models.GeographicalAreaDescription
        fields = ("described_geographicalarea", "description", "validity_start")
