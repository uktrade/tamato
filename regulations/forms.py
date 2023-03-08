import re
import string

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.core.exceptions import ValidationError
from django.forms import ChoiceField
from django.forms import IntegerField
from django.forms import TypedChoiceField
from django.forms.models import ModelChoiceField
from django.template import loader
from django.utils.safestring import SafeString

from common.forms import DateInputFieldFixed
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import UK_ID
from regulations.validators import RegulationUsage
from regulations.validators import RoleType
from workbaskets.models import WorkBasket

# Regulation.role_type is currently always set to RoleType.BASE.
FIXED_ROLE_TYPE = RoleType.BASE


class RegulationFormBase(ValidityPeriodForm):
    class Meta:
        model = Regulation
        fields = [
            "public_identifier",
            "url",
            "regulation_group",
            "information_text",
            "valid_between",
            "published_at",
            "approved",
        ]
        labels = {
            "url": "URL",
        }

    PUBLISHED_AT_HELP_TEXT = (
        "The date that the source for this regulation was published. For a "
        "Statutory Instrument (S.I.) or other peice of UK legislation, "
        "this should be the “made date” as found in the introductory note "
        "of the legislative text."
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

    def _load_details_from_template(self, title, template_path):
        public_identifier_details_content = loader.render_to_string(
            template_path,
        )
        return HTML.details(
            title,
            SafeString(public_identifier_details_content),
        )


class RegulationCreateForm(RegulationFormBase):
    regulation_usage = ChoiceField(
        choices=RegulationUsage.choices,
    )
    regulation_group = ModelChoiceField(
        queryset=Group.objects.all().order_by("group_id"),
        empty_label="Select a regulation group",
        help_text=(
            "If the wrong regulation group is selected, a trader's declaration "
            "may be rejected."
        ),
    )
    published_at = DateInputFieldFixed(
        label="Published date",
        help_text=RegulationFormBase.PUBLISHED_AT_HELP_TEXT,
    )
    sequence_number = IntegerField(
        min_value=1,
        max_value=9999,
        help_text=("The sequence number published by the source of this regulation."),
    )
    approved = TypedChoiceField(
        choices=(
            (True, "Approved"),
            (False, "Not approved (draft)"),
        ),
        coerce=lambda val: val == "True",
        label="Status of the legislation",
        help_text=(
            "An unapproved status means none of the measures that link to "
            "this regulation will be active at the border."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Fieldset(
                "regulation_usage",
                "public_identifier",
                self._load_details_from_template(
                    "Help with public identifiers",
                    "regulations/help_public_identifiers.jinja",
                ),
                Field(
                    "url",
                    css_class="govuk-input",
                ),
                "regulation_group",
                self._load_details_from_template(
                    "Help with regulation group",
                    "regulations/help_regulation_group.jinja",
                ),
                "information_text",
                "start_date",
                "end_date",
                "published_at",
                Field(
                    "sequence_number",
                    css_class="govuk-input govuk-input--width-5",
                ),
                self._load_details_from_template(
                    "Help with sequence number",
                    "regulations/help_sequence_number.jinja",
                ),
                "approved",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def _make_partial_regulation_id(
        self,
        published_at,
        sequence_number,
        regulation_usage,
    ):
        """
        Make a partial regulation_id using bound form data.

        The result will not include the single digit at the last position of a
        valid regulation_id, which is only applied when the regulation instance
        is saved (the part number provides a uniqueness element among
        potentially more than 10 + 26 partial regulation_ids).
        """
        publication_year = str(published_at.year)[-2:]
        sequence_number = f"{sequence_number:0>4}"
        return f"{regulation_usage}{publication_year}{sequence_number}"

    def _get_next_part_value(self, partial_regulation_id):
        """Get the next available part value that can be appended to a partial
        regulation_id (see
        RegulationCreateForm._make_partial_regulation_id())."""
        tx = WorkBasket.get_current_transaction(self.request)
        last_matching_regulation = (
            Regulation.objects.filter(
                regulation_id__startswith=partial_regulation_id,
                role_type=FIXED_ROLE_TYPE,
            )
            .approved_up_to_transaction(tx)
            .order_by("-regulation_id")
            .first()
        )
        if last_matching_regulation:
            highest_part_value = last_matching_regulation.regulation_id[-1]
            alphanum = string.digits + string.ascii_uppercase
            return alphanum[int(highest_part_value, 36) + 1]
        return 0

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        # Using input from this form, regulation_id is composed, by position,
        # of the following elements:
        #   [0]   - RegulationUsage key (e.g. "C" for "C: Draft regulation").
        #   [1-2] - last two digits from published_at (publication date),
        #           e.g. 21 for year 2021.
        #   [3-6] - sequence number, left padded with zeros eg. 0002.
        #   [7]   - Part value, allows same regulation to be entered into the
        #           system several times, each instance referencing a specific
        #           part of a regulation by adding a unique trailing value.
        partial_regulation_id = self._make_partial_regulation_id(
            cleaned_data["published_at"],
            cleaned_data["sequence_number"],
            cleaned_data["regulation_usage"],
        )
        try:
            part_value = self._get_next_part_value(partial_regulation_id)
        except IndexError:
            raise ValidationError(
                "Exceeded maximum number of parts for this regulation.",
            )

        cleaned_data["regulation_id"] = f"{partial_regulation_id}{part_value}"

        # Sanity check against the UK flavour of Regulation ID.
        assert re.match(UK_ID, cleaned_data["regulation_id"])

        if (
            not cleaned_data["approved"]
            and cleaned_data["regulation_usage"] != RegulationUsage.DRAFT_REGULATION
        ):
            self.add_error(
                "approved",
                'Regulation status "Not approved" may only be applied '
                'when Regulation usage is "C: Draft regulation"',
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.role_type = FIXED_ROLE_TYPE
        instance.regulation_id = self.cleaned_data["regulation_id"]

        if commit:
            instance.save(commit)
        return instance


class RegulationEditForm(RegulationFormBase):
    regulation_group = ModelChoiceField(
        queryset=Group.objects.all().order_by("group_id"),
        empty_label="Select a regulation group",
        help_text=(
            "If the wrong regulation group is selected, a trader's declaration "
            "may be rejected."
        ),
    )
    published_at = DateInputFieldFixed(
        label="Published date",
        help_text="You can't edit this",
        disabled=True,
    )
    approved = TypedChoiceField(
        choices=(
            (True, "Approved"),
            (False, "Not approved (draft)"),
        ),
        coerce=lambda val: val == "True",
        label="Status of the legislation",
        help_text=(
            "An unapproved status means none of the measures that link to "
            "this regulation will be active at the border."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Fieldset(
                "public_identifier",
                self._load_details_from_template(
                    "Help with public identifiers",
                    "regulations/help_public_identifiers.jinja",
                ),
                Field(
                    "url",
                    css_class="govuk-input",
                ),
                "regulation_group",
                self._load_details_from_template(
                    "Help with regulation group",
                    "regulations/help_regulation_group.jinja",
                ),
                "information_text",
                "start_date",
                "end_date",
                "published_at",
                HTML.details(
                    "Help with Published date",
                    RegulationFormBase.PUBLISHED_AT_HELP_TEXT,
                ),
                "approved",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["regulation_id"] = self.instance.regulation_id

        if self.errors:
            return cleaned_data

        if (
            not cleaned_data["approved"]
            and self.instance.regulation_id[0] != RegulationUsage.DRAFT_REGULATION
        ):
            self.add_error(
                "approved",
                'Regulation status "Not approved" may only be applied '
                'when Regulation usage is "C: Draft regulation"',
            )

        return cleaned_data


RegulationDeleteForm = delete_form_for(Regulation)
