from logging import disable
from django import forms

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fixed
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
    # * published_date - apply this form field to Regulation.published_at when
    #   saving.
    # * sequence_number - coerce and munge (with what?).
    #
    # Help messages
    # --
    # * Add public_identifiers help messages.
    # * Add regulation_group help messages.
    # * Add sequence_number help messages.

    class Meta:
        model = Regulation
        fields = [
            "regulation_usage",
            "public_identifier",
            "url",
            "regulation_group",
            #"title",
            "valid_between",
            #"published_at",
            #"sequence_number",
            "approved",
        ]

    regulation_usage = ChoiceField(
        choices=[("", "")] + RegulationUsage.choices
    )
    url = forms.CharField(
        label="URL",
        widget=forms.TextInput(attrs={"type": "url"}),
    )
    regulation_group = ChoiceField(
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "regulation_usage",
                "public_identifier",
                "url",
                "regulation_group",
                "title",
                "start_date",
                "end_date",
                "published_at",
                Field.text(
                    "sequence_number",
                    field_width=Fixed.FIVE,
                ),
                "approved",
            ),
            Submit("submit", "Save"),
        )
