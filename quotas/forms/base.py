from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from common.forms import BindNestedFormMixin
from common.forms import ExtraErrorFormMixin
from common.forms import FormSet
from common.forms import FormSetField
from common.forms import FormSetSubmitMixin
from common.forms import RadioNested
from common.forms import ValidityPeriodBaseForm
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.forms import formset_factory
from common.forms import unprefix_formset_data
from common.util import validity_range_contains_range
from common.validators import SymbolValidator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from quotas import models
from quotas import validators
from quotas.constants import QUOTA_EXCLUSIONS_FORMSET_PREFIX
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX
from quotas.constants import QUOTA_ORIGINS_FORMSET_PREFIX

CATEGORY_HELP_TEXT = "Categories are required for the TAP database but will not appear as a TARIC3 object in your workbasket"
SAFEGUARD_HELP_TEXT = (
    "Once the quota category has been set as ‘Safeguard’, this cannot be changed"
)
START_DATE_HELP_TEXT = "If possible, avoid putting a start date in the past as this may cause issues with CDS downstream"
ORDER_NUMBER_HELP_TEXT = "The order number must begin with 05 and be 6 digits long. Licensed quotas must begin 054 and safeguards must begin 058"


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


class QuotaFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Field.text("order_number", label_size=Size.SMALL),
            Field.text("origin", label_size=Size.SMALL),
            Field.radios("mechanism", legend_size=Size.SMALL),
            Field.radios("category", legend_size=Size.SMALL),
            Field.radios("active_state", legend_size=Size.SMALL),
            Field.text("current_work_basket", label_size=Size.SMALL),
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )


QuotaDeleteForm = delete_form_for(models.QuotaOrderNumber)


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
            Accordion(
                AccordionSection(
                    "Order number",
                    Field("order_number", css_class="govuk-input--width-20"),
                ),
                AccordionSection(
                    "Validity",
                    "start_date",
                    "end_date",
                ),
                AccordionSection(
                    "Category and mechanism",
                    "category",
                    "mechanism",
                ),
                AccordionSection(
                    "Quota origins",
                    Div(
                        HTML(origins_html),
                    ),
                ),
                css_class="govuk-width-!-two-thirds",
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


class QuotaOriginExclusionsForm(forms.Form):
    exclusion = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),  # modified in __init__
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["exclusion"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields["exclusion"].label_from_instance = (
            lambda obj: f"{obj.area_id} - {obj.description}"
        )


QuotaOriginExclusionsFormSet = formset_factory(
    QuotaOriginExclusionsForm,
    prefix=QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX,
    formset=FormSet,
    min_num=0,
    max_num=100,
    extra=0,
    validate_min=True,
    validate_max=True,
)


class QuotaOrderNumberOriginForm(
    FormSetSubmitMixin,
    ValidityPeriodForm,
    BindNestedFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumberOrigin
        fields = [
            "valid_between",
            "geographical_area",
        ]

    geographical_area = forms.ModelChoiceField(
        label="Geographical area",
        help_text="Add a geographical area",
        queryset=GeographicalArea.objects.all(),
    )

    exclusions = FormSetField(
        label="Geographical area exclusions",
        nested_forms=[QuotaOriginExclusionsFormSet],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.set_initial_data(*args, **kwargs)
        self.init_layout()

    def set_initial_data(self, *args, **kwargs):
        kwargs.pop("instance")
        self.bind_nested_forms(*args, **kwargs)

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                "start_date",
                "end_date",
                "geographical_area",
                "exclusions",
                css_class="govuk-!-width-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def init_fields(self):
        self.fields["geographical_area"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .prefetch_related("descriptions")
            .order_by("description")
        )
        self.fields["geographical_area"].label_from_instance = (
            lambda obj: f"{obj.area_id} - {obj.description}"
        )


class QuotaOrderNumberOriginUpdateForm(
    QuotaOrderNumberOriginForm,
):
    def set_initial_data(self, *args, **kwargs):
        nested_forms_initial = {**self.initial}
        nested_forms_initial.update(self.get_geo_area_initial())
        kwargs.pop("initial")
        self.bind_nested_forms(*args, initial=nested_forms_initial, **kwargs)

    def get_geo_area_initial(self):
        field_name = "exclusion"
        initial = {}
        initial_exclusions = []
        if self.instance.pk:
            initial_exclusions = [
                {field_name: exclusion.excluded_geographical_area}
                for exclusion in self.instance.quotaordernumberoriginexclusion_set.current()
            ]
        # if we just submitted the form, add the new data to initial
        if self.formset_submitted or self.whole_form_submit:
            new_data = unprefix_formset_data(
                QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX,
                self.data.copy(),
            )
            for g in new_data:
                if g[field_name]:
                    id = int(g[field_name])
                    g[field_name] = GeographicalArea.objects.get(id=id)
            initial_exclusions = new_data

        initial[QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX] = initial_exclusions

        return initial


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


class QuotaSuspensionType(TextChoices):
    SUSPENSION = "SUSPENSION", "Suspension period"
    BLOCKING = "BLOCKING", "Blocking period"


class BlockingPeriodTypeForm(forms.Form):
    blocking_period_type = forms.ChoiceField(
        help_text="Select a blocking period type.",
        choices=validators.BlockingPeriodType.choices,
        error_messages={
            "required": "Select a blocking period type",
        },
    )


class QuotaSuspensionOrBlockingCreateForm(
    ValidityPeriodBaseForm,
    BindNestedFormMixin,
    forms.Form,
):
    quota_definition = forms.ModelChoiceField(
        label="Quota definition SID",
        empty_label="Select a quota definition SID",
        queryset=models.QuotaDefinition.objects.all(),
        error_messages={
            "required": "Select a quota definition SID",
        },
    )

    suspension_type = RadioNested(
        label="Do you want to create a suspension or blocking period?",
        help_text="Select one option.",
        choices=QuotaSuspensionType.choices,
        nested_forms={
            QuotaSuspensionType.SUSPENSION.value: [],
            QuotaSuspensionType.BLOCKING.value: [BlockingPeriodTypeForm],
        },
        error_messages={
            "required": "Select if you want to create a suspension or blocking period",
        },
    )

    description = forms.CharField(
        label="Description",
        validators=[SymbolValidator],
        widget=forms.Textarea(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.quota_order_number = kwargs.pop("quota_order_number")
        super().__init__(*args, **kwargs)
        self.bind_nested_forms(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["quota_definition"].queryset = (
            models.QuotaDefinition.objects.current()
            .as_at_today_and_beyond()
            .filter(order_number=self.quota_order_number)
            .order_by("-sid")
        )
        self.fields["quota_definition"].label_from_instance = (
            lambda obj: f"{obj.sid} ({obj.valid_between.lower} - {obj.valid_between.upper})"
        )

    def init_layout(self):
        cancel_url = reverse_lazy(
            "quota-ui-detail",
            kwargs={"sid": self.quota_order_number.sid},
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "quota_definition",
            "suspension_type",
            Field.textarea("description", rows=5),
            "start_date",
            "end_date",
            Div(
                Submit(
                    "submit",
                    "Save",
                    css_class="govuk-button--primary",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={cancel_url}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        definition_period = (
            cleaned_data["quota_definition"].valid_between
            if cleaned_data.get("quota_definition")
            else None
        )
        validity_period = cleaned_data.get("valid_between")
        if (
            definition_period
            and validity_period
            and not validity_range_contains_range(definition_period, validity_period)
        ):
            raise ValidationError(
                f"The start and end date must sit within the selected quota definition's start and end date ({definition_period.lower} - {definition_period.upper})",
            )

        return cleaned_data

    def save(self, workbasket):
        type_to_create_map = {
            QuotaSuspensionType.SUSPENSION: self.create_suspension_period,
            QuotaSuspensionType.BLOCKING: self.create_blocking_period,
        }
        create_object = type_to_create_map.get(self.cleaned_data["suspension_type"])
        return create_object(workbasket=workbasket)

    def create_suspension_period(self, workbasket):
        return models.QuotaSuspension.objects.create(
            quota_definition=self.cleaned_data["quota_definition"],
            description=self.cleaned_data["description"],
            valid_between=self.cleaned_data["valid_between"],
            update_type=UpdateType.CREATE,
            transaction=workbasket.new_transaction(),
        )

    def create_blocking_period(self, workbasket):
        return models.QuotaBlocking.objects.create(
            quota_definition=self.cleaned_data["quota_definition"],
            blocking_period_type=self.cleaned_data["blocking_period_type"],
            description=self.cleaned_data["description"],
            valid_between=self.cleaned_data["valid_between"],
            update_type=UpdateType.CREATE,
            transaction=workbasket.new_transaction(),
        )


class QuotaSuspensionUpdateForm(ValidityPeriodForm, forms.ModelForm):

    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()

    def init_layout(self):
        cancel_url = reverse_lazy(
            "quota-ui-detail",
            kwargs={"sid": self.instance.quota_definition.order_number.sid},
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "start_date",
            "end_date",
            Field.textarea("description", rows=5),
            Div(
                Submit(
                    "submit",
                    "Save",
                    css_class="govuk-button--primary",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={cancel_url}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        definition_period = self.instance.quota_definition.valid_between
        validity_period = cleaned_data.get("valid_between")
        if (
            definition_period
            and validity_period
            and not validity_range_contains_range(definition_period, validity_period)
        ):
            raise ValidationError(
                f"The start and end date must sit within the selected quota definition's start and end date ({definition_period.lower} - {definition_period.upper})",
            )

        return cleaned_data

    class Meta:
        model = models.QuotaSuspension
        fields = [
            "valid_between",
            "description",
        ]


QuotaSuspensionDeleteForm = delete_form_for(models.QuotaSuspension)
