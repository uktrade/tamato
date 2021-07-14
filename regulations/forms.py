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
from workbaskets.models import WorkBasket


# Regulation.role_type is currently always set to a value of one (1).
FIXED_ROLE_TYPE = 1


class RegulationCreateForm(ValidityPeriodForm):
    class Meta:
        model = Regulation
        fields = [
            "public_identifier",
            "url",
            "regulation_group",
            "information_text",
            "valid_between",
            # published_at -- set at creation time, otherwise "cannot be
            #   specified for Regulation model form as it is a non-editable
            #   field.".
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
    published_at = DateInputFieldFixed(
        label="Published date",
        help_text=Regulation._meta.get_field("published_at").help_text,
    )
    sequence_number = forms.CharField(
        label="Sequence number",
        help_text="The sequence number published by the source of this regulation.",
        max_length=4,
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
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["end_date"].help_text = (
            "Leave the end date empty if the regulation is required for an "
            "unlimited amount of time."
        )
        self.fields["information_text"].label = "Title"

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
                "information_text",
                "start_date",
                "end_date",
                "published_at",
                Field.text(
                    "sequence_number",
                    field_width=Fixed.FIVE,
                    pattern="[0-9]{1,4}",
                ),
                self._load_details_from_template(
                    "Help with sequence number",
                    "regulations/help_sequence_number.html"
                ),
                "approved",
            ),
            Submit("submit", "Save"),
        )

    def _make_partial_regulation_id(self, cleaned_data):
        """ Make a partial regulation_id using bound form data. The result will
        not include the single digit at the last position of a valid
        regulation_id, which is only applied when the regulation instance is
        saved (the part number provides a uniqueness element among potentially
        <11 partial regulation_ids).
        """
        publication_year = str(cleaned_data["published_at"].year)[-2:]
        sequence_number = "{:0>4}".format(cleaned_data["sequence_number"])
        return (
            "{regulation_usage}"
            "{publication_year}"
            "{sequence_number}".format(
                regulation_usage=cleaned_data["regulation_usage"],
                publication_year=publication_year,
                sequence_number=sequence_number,
            )
        )

    def _get_next_part_number(self, partial_regulation_id):
        """ Get the next available part number that can be appended to a partial
        regulation_id (see RegulationCreateForm._make_partial_regulation_id()).
        """
        tx = WorkBasket.get_current_transaction(self.request)
        basket_regulations = (
            Regulation.objects.filter(
                regulation_id__startswith=partial_regulation_id,
                role_type=FIXED_ROLE_TYPE,
            )
            .approved_up_to_transaction(tx)
            .order_by("-regulation_id")
        )
        if basket_regulations:
            highest_part_number = basket_regulations[0].regulation_id[-1]
            return int(highest_part_number) + 1
        return 0

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.regulation_group = Group.objects.get(
            pk=self.cleaned_data["regulation_group_proxy"]
        )
        instance.role_type = FIXED_ROLE_TYPE
        instance.published_at = self.cleaned_data["published_at"]

        # Using input from this form, regulation_id is composed, by position,
        # of the following elements:
        #   [0]   - RegulationUsage key (e.g. "C" for "C: Draft regulation").
        #   [1-2] - last two digits from published_at (publication date),
        #           e.g. 21 for year 2021.
        #   [3-6] - sequence number, right padded with zeros eg. 0002.
        #   [7]   - Part number, allows same legislation to be in system several
        #           times by adding unique trailing value, all other values
        #           being equal.
        partial_regulation_id = self._make_partial_regulation_id(
            self.cleaned_data
        )
        part_number = self._get_next_part_number(partial_regulation_id)
        instance.regulation_id = "{partial_regulation_id}{part_number}".format(
            partial_regulation_id=partial_regulation_id,
            part_number=part_number,
        )

        if commit:
            instance.save(commit)
        return instance
