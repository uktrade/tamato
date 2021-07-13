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

class RegulationCreateForm(ValidityPeriodForm):

    class Meta:
        model = Regulation
        fields = [
            "public_identifier",
            "url",
            "regulation_group",
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
        self.request = kwargs.pop("request", None)
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
                "title", # <-- ### save how?
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

    def save(self, commit=True):
        # TODO:
        # * title - coerce and munge (with what?).

        instance = super().save(commit=False)

        #workbasket = WorkBasket.current(self.request)
        #tx = None
        #if workbasket:
        #    tx = workbasket.transactions.order_by("order").last()
        #with WorkBasket.new_transaction():
        #    pass

        # Get the last role_type and regulation_id via
        # .approved_up_to_transaction().
        # AdditionalCode example, which doesn't translate so well to our case.
        #
        # highest_sid = (
        #     models.AdditionalCode.objects.filter(type__sid=instance.type.sid)
        #     .approved_up_to_transaction(tx)
        #     .aggregate(Max("sid"))["sid__max"]
        # )
        # instance.sid = highest_sid + 1


        instance.role_type = 1
        instance.published_at = self.cleaned_data["published_at"]

        publication_year = str(self.cleaned_data["published_at"].year)[-2:]
        sequence_number = "{:0>4}".format(self.cleaned_data["sequence_number"])
        part_number = 1
        instance.regulation_id = (
            "{regulation_usage}"
            "{publication_year}"
            "{sequence_number}"
            "{part_number}".format(
                regulation_usage=self.cleaned_data["regulation_usage"],
                publication_year=publication_year,
                sequence_number=sequence_number,
                part_number=part_number,
            )
        )

        if commit:
            instance.save()

        return instance

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["regulation_group"] = Group.objects.get(
            pk=cleaned_data["regulation_group_proxy"]
        )
        return cleaned_data
