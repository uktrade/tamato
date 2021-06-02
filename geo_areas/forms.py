from crispy_forms_gds.layout import Field

from common.forms import CreateDescriptionForm
from geo_areas import models


class GeographicalAreaCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["described_geographicalarea"].disabled = True
            self.fields["described_geographicalarea"].help_text = "You can't edit this"
            self.fields[
                "described_geographicalarea"
            ].label = "Described geographical area"

        self.helper.layout.insert(
            0,
            Field(
                "described_geographicalarea",
                context={"label_size": "govuk-label--s"},
            ),
        )

    class Meta:
        model = models.GeographicalAreaDescription
        fields = ("described_geographicalarea", "description", "validity_start")
