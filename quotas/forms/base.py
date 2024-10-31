from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.urls import reverse_lazy

from common.forms import BindNestedFormMixin
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
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX


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
            "quota_definition-ui-list-filter",
            kwargs={
                "sid": self.instance.quota_definition.order_number.sid,
                "quota_type": "suspension_periods",
            },
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


class QuotaBlockingUpdateForm(ValidityPeriodForm, forms.ModelForm):

    blocking_period_type = forms.ChoiceField(
        choices=validators.BlockingPeriodType.choices,
    )

    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_layout(self):
        cancel_url = reverse_lazy(
            "quota_definition-ui-list-filter",
            kwargs={
                "sid": self.instance.quota_definition.order_number.sid,
                "quota_type": "blocking_periods",
            },
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "blocking_period_type",
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

    def init_fields(self):
        if self.instance.valid_between.lower <= date.today():
            self.fields["description"].disabled = True
            self.fields["blocking_period_type"].disabled = True
            self.fields["start_date"].disabled = True

    class Meta:
        model = models.QuotaBlocking
        fields = [
            "valid_between",
            "description",
            "blocking_period_type",
        ]


QuotaBlockingDeleteForm = delete_form_for(models.QuotaBlocking)
