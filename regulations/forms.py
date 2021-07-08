from django import forms
from django.template import loader
from django.utils.safestring import SafeString


from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.forms import ChoiceField

from common.forms import DateInputFieldFixed
from common.forms import ValidityPeriodForm
from regulations.models import Group, Regulation
from regulations.validators import RegulationUsage


class RegulationCreateForm(ValidityPeriodForm):

    # TODO:
    #
    # Form manipulaton
    # --
    # * title - coerce and munge (with what?).
    # * valid_between - manage ValidityPeriodForm cleaned data
    #       cleaned_data = super().clean()
    # * sequence_number - coerce and munge (with what?).

    class Meta:
        model = Regulation
        fields = [
            "regulation_usage",
            "public_identifier",
            "url",
            "regulation_group",
            "valid_between",
            "approved",
        ]

    regulation_usage = ChoiceField(
        choices=[("", "")] + RegulationUsage.choices
    )
    url = forms.CharField(
        label="URL",
        widget=forms.TextInput(attrs={"type": "url"}),
    )
    regulation_group_proxy = ChoiceField(
        label="Regulation group",
        choices= [("", "")] + [
            (group.pk, f"{group.group_id}: {group.description}")
                for group in Group.objects.all().order_by("group_id")
        ],
        help_text=Regulation._meta.get_field("regulation_group").help_text
    )
    title = forms.CharField()
    published_at = DateInputFieldFixed(
        label="Published date",
        disabled=False,
        help_text=Regulation._meta.get_field("published_at").help_text
    )
    sequence_number = forms.CharField(
        label="Sequence number",
        help_text="The sequence number published by the source of this regulation.",
    )
    approved = ChoiceField(
        choices=(
            ("", ""),
            ("0", "Approved"),
            ("1", "Not approved (draft)"),
        ),
        label="Status of the legislation",
        help_text=Regulation._meta.get_field("approved").help_text,
    )

    def _load_details_from_template(self, title, template_path):
        public_identifier_details_content = loader.render_to_string(
            template_path
        )
        return HTML.details(
            title,
            SafeString(public_identifier_details_content)
        )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tweak to default end_date help text.
        self.fields["end_date"].help_text = (
            "Leave the end date empty if the regulation is required for an "
            "unlimited amount of time."
        )

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "regulation_usage",
                "public_identifier",
                self._load_details_from_template(
                    "Help with public identifiers",
                    "regulations/help_public_identifiers.html"
                ),
                "url",
                "regulation_group_proxy",
                self._load_details_from_template(
                    "Help with regulation group",
                    "regulations/help_regulation_group.html"
                ),
                "title",
                "start_date",
                "end_date",
                "published_at",
                Field.text(
                    "sequence_number",
                    field_width=Fixed.FIVE,
                ),
                self._load_details_from_template(
                    "Help with sequence number",
                    "regulations/help_sequence_number.html"
                ),
                "approved",
            ),
            Submit("submit", "Save"),
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["regulation_group"] = Group.objects.get(
            pk=cleaned_data["regulation_group_proxy"]
        )
        return cleaned_data
