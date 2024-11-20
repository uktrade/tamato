from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from common.forms import ExtraErrorFormMixin
from common.forms import ValidityPeriodForm
from common.forms import unprefix_formset_data
from geo_areas.models import GeographicalArea
from quotas import models
from quotas import validators
from quotas.constants import CATEGORY_HELP_TEXT
from quotas.constants import MECHANISM_HELP_TEXT
from quotas.constants import ORDER_NUMBER_HELP_TEXT
from quotas.constants import QUOTA_EXCLUSIONS_FORMSET_PREFIX
from quotas.constants import QUOTA_ORIGINS_FORMSET_PREFIX
from quotas.constants import SAFEGUARD_HELP_TEXT
from quotas.constants import START_DATE_HELP_TEXT

from .base import QuotaOrderNumberOriginUpdateForm


class QuotaOriginsReactMixin(ExtraErrorFormMixin):
    """Custom cleaning and validation for QuotaUpdateForm and
    QuotaOrderNumberCreateForm."""

    def clean_quota_origins(self):
        # unprefix origins formset
        submitted_data = unprefix_formset_data(
            QUOTA_ORIGINS_FORMSET_PREFIX,
            self.data.copy(),
        )
        # for each origin, unprefix exclusions formset
        for i, origin_data in enumerate(submitted_data):
            exclusions = unprefix_formset_data(
                QUOTA_EXCLUSIONS_FORMSET_PREFIX,
                origin_data.copy(),
            )
            submitted_data[i]["exclusions"] = exclusions

        self.cleaned_data["origins"] = []

        for i, origin_data in enumerate(submitted_data):
            # instantiate a form per origin data to do validation
            origin_form = QuotaOrderNumberOriginUpdateReactForm(
                data=origin_data,
                initial=origin_data,
                instance=(
                    models.QuotaOrderNumberOrigin.objects.get(pk=origin_data["pk"])
                    if origin_data.get("pk")
                    else None
                ),
            )

            cleaned_exclusions = []

            for exclusion in origin_data["exclusions"]:
                exclusion_form = QuotaOriginExclusionsReactForm(
                    data=exclusion,
                    initial=exclusion,
                )
                if not exclusion_form.is_valid():
                    for j, item in enumerate(exclusion_form.errors.as_data().items()):
                        self.add_extra_error(
                            f"{QUOTA_ORIGINS_FORMSET_PREFIX}-{i}-exclusions-{j}-{item[0]}",
                            item[1],
                        )
                else:
                    cleaned_exclusions.append(exclusion_form.cleaned_data)

            if not origin_form.is_valid():
                for field, e in origin_form.errors.as_data().items():
                    self.add_extra_error(
                        f"{QUOTA_ORIGINS_FORMSET_PREFIX}-{i}-{field}",
                        e,
                    )
            else:
                origin_form.cleaned_data["exclusions"] = cleaned_exclusions
                self.cleaned_data["origins"].append(origin_form.cleaned_data)


class QuotaOrderNumberOriginUpdateReactForm(QuotaOrderNumberOriginUpdateForm):
    """Used only to validate data sent from the quota edit React form."""

    pk = forms.IntegerField(required=False)


class QuotaOriginExclusionsReactForm(forms.Form):
    """Used only to validate data sent from the quota edit React form."""

    pk = forms.IntegerField(required=False)
    # field name is different to match the react form
    geographical_area = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geographical_area"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )


class QuotaUpdateForm(
    QuotaOriginsReactMixin,
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "valid_between",
            "category",
        ]

    category = forms.ChoiceField(
        label="",
        choices=validators.QuotaCategory.choices,
        error_messages={"invalid_choice": "Please select a valid category"},
    )

    def clean_category(self):
        value = self.cleaned_data.get("category")
        # the widget is disabled and data is not submitted. fall back to instance value
        if not value:
            return self.instance.category
        if (
            self.instance.category == validators.QuotaCategory.SAFEGUARD
            and value != validators.QuotaCategory.SAFEGUARD
        ):
            raise ValidationError(SAFEGUARD_HELP_TEXT)
        return value

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.exclusions_options = kwargs.pop("exclusions_options")
        self.geo_area_options = kwargs.pop("geo_area_options")
        self.groups_with_members = kwargs.pop("groups_with_members")
        self.existing_origins = kwargs.pop("existing_origins")
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.set_initial_data(*args, **kwargs)
        self.init_layout(self.request)

    def set_initial_data(self, *args, **kwargs):
        self.fields["category"].initial = self.instance.category

    def init_fields(self):
        if self.instance.category == validators.QuotaCategory.SAFEGUARD:
            self.fields["category"].required = False
            self.fields["category"].widget = forms.Select(
                choices=[
                    (
                        validators.QuotaCategory.SAFEGUARD.value,
                        validators.QuotaCategory.SAFEGUARD.label,
                    ),
                ],
                attrs={"disabled": True},
            )
            self.fields["category"].help_text = SAFEGUARD_HELP_TEXT
        else:
            self.fields["category"].choices = validators.QuotaCategoryEditing.choices
            self.fields["category"].help_text = CATEGORY_HELP_TEXT

        self.fields["start_date"].help_text = START_DATE_HELP_TEXT

    def get_origins_initial(self):
        initial = [
            {
                "id": o.pk,  # unique identifier used by react
                "pk": o.pk,
                "exclusions": [
                    e.excluded_geographical_area.pk
                    for e in o.quotaordernumberoriginexclusion_set.current()
                ],
                "geographical_area": o.geographical_area.pk,
                "start_date_0": o.valid_between.lower.day,
                "start_date_1": o.valid_between.lower.month,
                "start_date_2": o.valid_between.lower.year,
                "end_date_0": (
                    o.valid_between.upper.day if o.valid_between.upper else ""
                ),
                "end_date_1": (
                    o.valid_between.upper.month if o.valid_between.upper else ""
                ),
                "end_date_2": (
                    o.valid_between.upper.year if o.valid_between.upper else ""
                ),
            }
            for o in self.existing_origins
        ]
        # if we just submitted the form, overwrite initial with submitted data
        # this prevents newly added origin data being cleared if the form does not pass validation
        if self.data.get("submit"):
            new_data = unprefix_formset_data(
                QUOTA_ORIGINS_FORMSET_PREFIX,
                self.data.copy(),
            )
            initial = new_data

        return initial

    def clean(self):
        self.clean_quota_origins()
        return super().clean()

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        origins_html = render_to_string(
            "includes/quotas/quota-edit-origins.jinja",
            {
                "object": self.instance,
                "request": request,
                "geo_area_options": self.geo_area_options,
                "groups_with_members": self.groups_with_members,
                "exclusions_options": self.exclusions_options,
                "origins_initial": self.get_origins_initial(),
                "errors": self.errors,
            },
        )

        self.helper.layout = Layout(
            Div(
                Accordion(
                    AccordionSection(
                        "Validity period",
                        "start_date",
                        "end_date",
                    ),
                    AccordionSection(
                        "Category",
                        "category",
                    ),
                    AccordionSection(
                        "Quota origins",
                        Div(
                            HTML(origins_html),
                        ),
                    ),
                ),
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class QuotaOrderNumberCreateForm(
    QuotaOriginsReactMixin,
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "order_number",
            "valid_between",
            "category",
            "mechanism",
        ]

    order_number = forms.CharField(
        help_text=ORDER_NUMBER_HELP_TEXT,
        validators=[validators.quota_order_number_validator],
        error_messages={
            "invalid": "Order number must be six digits long and begin with 05",
            "required": "Enter the order number",
        },
    )
    category = forms.ChoiceField(
        choices=validators.QuotaCategory.choices,
        help_text=CATEGORY_HELP_TEXT,
        error_messages={
            "invalid_choice": "Please select a valid category",
            "required": "Choose the category",
        },
    )
    mechanism = forms.ChoiceField(
        choices=validators.AdministrationMechanism.choices,
        help_text=MECHANISM_HELP_TEXT,
        error_messages={
            "invalid_choice": "Please select a valid mechanism",
            "required": "Choose the mechanism",
        },
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.exclusions_options = kwargs.pop("exclusions_options")
        self.geo_area_options = kwargs.pop("geo_area_options")
        self.groups_with_members = kwargs.pop("groups_with_members")
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout(self.request)

    def init_fields(self):
        self.fields["start_date"].help_text = START_DATE_HELP_TEXT

    def get_origins_initial(self):
        # if we just submitted the form, overwrite initial with submitted data
        # this prevents newly added origin data being cleared if the form does not pass validation
        initial = []
        if self.data.get("submit"):
            initial = unprefix_formset_data(
                QUOTA_ORIGINS_FORMSET_PREFIX,
                self.data.copy(),
            )
        return initial

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        origins_html = render_to_string(
            "includes/quotas/quota-create-origins.jinja",
            {
                "object": self.instance,
                "request": request,
                "geo_area_options": self.geo_area_options,
                "groups_with_members": self.groups_with_members,
                "exclusions_options": self.exclusions_options,
                "origins_initial": self.get_origins_initial(),
                "errors": self.errors,
            },
        )

        self.helper.layout = Layout(
            Field("order_number", css_class="govuk-input--width-20"),
            "start_date",
            "end_date",
            "category",
            "mechanism",
            Div(
                HTML(origins_html),
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        category = self.cleaned_data.get("category")
        mechanism = self.cleaned_data.get("mechanism")
        order_number = self.cleaned_data.get("order_number", "")

        if (
            mechanism is not None
            and int(mechanism) == validators.AdministrationMechanism.LICENSED
        ):
            if int(category) == validators.QuotaCategory.SAFEGUARD:
                raise ValidationError(
                    "Mechanism cannot be set to licensed for safeguard quotas",
                )
            if not order_number.startswith("054"):
                raise ValidationError(
                    "The order number for licensed quotas must begin with 054",
                )

        if (
            category is not None
            and int(
                category,
            )
            == validators.QuotaCategory.SAFEGUARD
            and not order_number.startswith("058")
        ):
            raise ValidationError(
                "The order number for safeguard quotas must begin with 058",
            )

        self.clean_quota_origins()

        return super().clean()
