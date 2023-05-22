from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.urls import reverse_lazy

from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from quotas import models
from quotas import validators


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
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )


QuotaDeleteForm = delete_form_for(models.QuotaOrderNumber)


class QuotaDefinitionFilterForm(forms.Form):
    quota_type = forms.MultipleChoiceField(
        label="View by",
        choices=[
            ("sub_quotas", "Sub-quotas"),
            ("blocking_periods", "Blocking periods"),
            ("suspension_periods", "Suspension periods"),
        ],
        widget=forms.RadioSelect(),
    )

    def __init__(self, *args, **kwargs):
        quota_type_initial = kwargs.pop("form_initial")
        object_sid = kwargs.pop("object_sid")
        super().__init__(*args, **kwargs)
        self.fields["quota_type"].initial = quota_type_initial
        self.helper = FormHelper()

        clear_url = reverse_lazy("quota-definitions", kwargs={"sid": object_sid})

        self.helper.layout = Layout(
            Field.radios("quota_type", label_size=Size.SMALL),
            Button("submit", "Apply"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary" href="{clear_url}">Restore defaults</a>',
            ),
        )


class QuotaUpdateForm(ValidityPeriodForm, forms.ModelForm):
    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "valid_between",
            "category",
        ]

    category = forms.ChoiceField(
        label="Category",
        choices=[],  # set in __init__
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.category == validators.QuotaCategory.SAFEGUARD:
            self.fields["category"].widget = forms.Select(
                attrs={"disabled": True},
                choices=validators.QuotaCategory.choices,
            )
            self.fields[
                "category"
            ].help_text = "Once safeguard has been set and published as the quota category, this can’t be changed"
        else:
            self.fields["category"].choices = validators.QuotaCategoryEditing.choices
        self.fields["category"].initial = self.instance.category

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
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
                css_class="govuk-!-width-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )
