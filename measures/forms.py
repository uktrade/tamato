import logging

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.template import loader

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import FormSet
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.util import validity_range_contains_range
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.forms import GeographicalAreaFormMixin
from geo_areas.forms import GeographicalAreaSelect
from geo_areas.models import GeographicalArea
from geo_areas.util import with_description_string
from measures import models
from measures.parsers import DutySentenceParser
from measures.validators import validate_duties
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


class MeasureConditionComponentDuty(Field):
    template = "components/measure_condition_component_duty/template.jinja"


class MeasureValidityForm(ValidityPeriodForm):
    """A form for working with `start_date` and `end_date` logic where the
    `valid_between` field does not already exist on the form."""

    class Meta:
        model = models.Measure
        fields = [
            "valid_between",
        ]


class MeasureConditionsFormMixin(forms.ModelForm):
    class Meta:
        model = models.MeasureCondition
        fields = [
            "condition_code",
            "duty_amount",
            "monetary_unit",
            "condition_measurement",
            "required_certificate",
            "action",
            "applicable_duty",
            "condition_sid",
        ]

    condition_code = forms.ModelChoiceField(
        label="",
        queryset=models.MeasureConditionCode.objects.latest_approved(),
        empty_label="-- Please select a condition code --",
    )
    # This field used to be called duty_amount, but forms.ModelForm expects a decimal value when it sees that duty_amount is a DecimalField on the MeasureCondition model.
    # reference_price expects a non-compound duty string (e.g. "11 GBP / 100 kg".
    # Using DutySentenceParser we validate this string and get the decimal value to pass to the model field, duty_amount)
    reference_price = forms.CharField(
        label="Reference price or quantity",
        required=False,
    )
    required_certificate = AutoCompleteField(
        label="Certificate, licence or document",
        queryset=Certificate.objects.all(),
        required=False,
    )
    action = forms.ModelChoiceField(
        label="Action code",
        queryset=models.MeasureAction.objects.latest_approved(),
        empty_label="-- Please select an action code --",
    )
    applicable_duty = forms.CharField(
        label="Duty",
        required=False,
    )
    condition_sid = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Fieldset(
                Div(
                    Field(
                        "condition_code",
                        template="components/measure_condition_code/template.jinja",
                    ),
                    "condition_sid",
                ),
                Div(
                    Field("reference_price", css_class="govuk-input"),
                    "required_certificate",
                    css_class="govuk-radios__conditional",
                ),
                Field(
                    "action",
                    template="components/measure_condition_action_code/template.jinja",
                ),
                Div(
                    MeasureConditionComponentDuty("applicable_duty"),
                ),
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
                legend="Condition code",
                legend_size=Size.SMALL,
                data_field="condition_code",
            ),
        )

    def conditions_clean(self, cleaned_data, measure_start_date):
        """
        We get the reference_price from cleaned_data and the measure_start_date
        from the form's initial data.

        If both are present, we call validate_duties with measure_start_date.
        Then, if reference_price is provided, we use DutySentenceParser with
        measure_start_date, if present, or the current_date, to check that we
        are dealing with a simple duty (i.e. only one component). We then update
        cleaned_data with key-value pairs created from this single, unsaved
        component.
        """
        price = cleaned_data.get("reference_price")

        if price and measure_start_date is not None:
            validate_duties(price, measure_start_date)

        if price:
            parser = DutySentenceParser.get(measure_start_date)
            components = parser.parse(price)
            if len(components) > 1:
                raise ValidationError(
                    "A MeasureCondition cannot be created with a compound reference price (e.g. 3.5% + 11 GBP / 100 kg)",
                )
            cleaned_data["duty_amount"] = components[0].duty_amount
            cleaned_data["monetary_unit"] = components[0].monetary_unit
            cleaned_data["condition_measurement"] = components[0].component_measurement

        # The JS autocomplete does not allow for clearing unnecessary certificates
        # In case of a user changing data, the information is cleared here.
        condition_code = cleaned_data.get("condition_code")
        if condition_code and not condition_code.accepts_certificate:
            cleaned_data["required_certificate"] = None

        return cleaned_data


class MeasureConditionsForm(MeasureConditionsFormMixin):
    # condition_sid = forms.CharField(required=False)

    # class Meta:
    #     model = models.MeasureCondition
    #     fields = MeasureConditionsFormMixin.Meta.fields + ["condition_sid"]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     breakpoint()

    def get_start_date(self, data):
        """Validates that the day, month, and year start_date fields are present
        in data and then returns the start_date datetime object."""
        validity_form = MeasureValidityForm(data=data)
        validity_form.is_valid()

        return validity_form.cleaned_data["valid_between"].lower

    def clean_applicable_duty(self):
        """
        Gets applicable_duty from cleaned data.

        We get start date from other data in the measure edit form. Uses
        `DutySentenceParser` to check that applicable_duty is a valid duty
        string.
        """
        applicable_duty = self.cleaned_data["applicable_duty"]

        if applicable_duty and self.get_start_date(self.data) is not None:
            validate_duties(applicable_duty, self.get_start_date(self.data))

        return applicable_duty

    def clean(self):
        """
        We get the reference_price from cleaned_data and the measure_start_date
        from the form's initial data.

        If both are present, we call validate_duties with measure_start_date.
        Then, if reference_price is provided, we use DutySentenceParser with
        measure_start_date, if present, or the current_date, to check that we
        are dealing with a simple duty (i.e. only one component). We then update
        cleaned_data with key-value pairs created from this single, unsaved
        component.
        """
        cleaned_data = super().clean()
        measure_start_date = self.get_start_date(self.data)

        return self.conditions_clean(cleaned_data, measure_start_date)


class MeasureConditionsFormSet(FormSet):
    form = MeasureConditionsForm


class MeasureConditionsWizardStepForm(MeasureConditionsFormMixin):
    # override methods that use form kwargs
    def __init__(self, *args, **kwargs):
        self.measure_start_date = kwargs.pop("measure_start_date")
        super().__init__(*args, **kwargs)

    def clean_applicable_duty(self):
        """
        Gets applicable_duty from cleaned data.

        We expect `measure_start_date` to be passed in. Uses
        `DutySentenceParser` to check that applicable_duty is a valid duty
        string.
        """
        applicable_duty = self.cleaned_data["applicable_duty"]

        if applicable_duty and self.measure_start_date is not None:
            validate_duties(applicable_duty, self.measure_start_date)

        return applicable_duty

    def clean(self):
        """
        We get the reference_price from cleaned_data and the measure_start_date
        from form kwargs.

        If reference_price is provided, we use DutySentenceParser with
        measure_start_date to check that we are dealing with a simple duty (i.e.
        only one component). We then update cleaned_data with key-value pairs
        created from this single, unsaved component.
        """
        cleaned_data = super().clean()

        return self.conditions_clean(cleaned_data, self.measure_start_date)


class MeasureConditionsWizardStepFormSet(FormSet):
    form = MeasureConditionsWizardStepForm


class MeasureForm(ValidityPeriodForm):
    measure_type = AutoCompleteField(
        label="Measure type",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=models.MeasureType.objects.all(),
    )
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=Regulation.objects.all(),
    )
    goods_nomenclature = AutoCompleteField(
        label="Code and description",
        help_text="Select the 10 digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
        required=False,
        attrs={"min_length": 3},
    )
    duty_sentence = forms.CharField(
        label="Duties",
        widget=forms.TextInput,
        required=False,
    )
    additional_code = AutoCompleteField(
        label="Code and description",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.all(),
        required=False,
    )
    order_number = AutoCompleteField(
        label="Order number",
        help_text="Enter the quota order number if a quota measure type has been selected. Leave this field blank if the measure is not a quota.",
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )
    geographical_area = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.all(),
        required=False,
    )
    geographical_area_group = forms.ModelChoiceField(
        queryset=with_description_string(
            GeographicalArea.objects.filter(
                area_code=1,
            ).exclude(descriptions__description__isnull=True),
        ),
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
        empty_label=None,
    )
    geographical_area_country_or_region = forms.ModelChoiceField(
        queryset=with_description_string(
            GeographicalArea.objects.exclude(
                area_code=1,
                descriptions__description__isnull=True,
            ),
        ),
        widget=forms.Select(attrs={"class": "govuk-select"}),
        required=False,
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        tx = WorkBasket.get_current_transaction(self.request)

        if not hasattr(self.instance, "duty_sentence"):
            raise AttributeError(
                "Measure instance is missing `duty_sentence` attribute. Try calling `with_duty_sentence` queryset method",
            )

        self.initial["duty_sentence"] = self.instance.duty_sentence
        self.request.session[
            f"instance_duty_sentence_{self.instance.sid}"
        ] = self.instance.duty_sentence

        self.initial_geographical_area = self.instance.geographical_area

        for field in ["geographical_area_group", "geographical_area_country_or_region"]:
            self.fields[field].queryset = (
                self.fields[field]
                .queryset.as_at_today()
                .approved_up_to_transaction(tx)
                .with_latest_links("descriptions")
                .prefetch_related("descriptions")
                .order_by("description")
            )
            self.fields[field].label_from_instance = lambda obj: obj.description

        if self.instance.geographical_area.is_group():
            self.fields[
                "geographical_area_group"
            ].initial = self.instance.geographical_area

        if self.instance.geographical_area.is_single_region_or_country():
            self.fields[
                "geographical_area_country_or_region"
            ].initial = self.instance.geographical_area

        # If no footnote keys are stored in the session for a measure,
        # store all the pks of a measure's footnotes on the session, using the measure sid as key
        if f"instance_footnotes_{self.instance.sid}" not in self.request.session.keys():
            tx = WorkBasket.get_current_transaction(self.request)
            associations = (
                models.FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                    tx,
                ).filter(
                    footnoted_measure=self.instance,
                )
            )
            self.request.session[f"instance_footnotes_{self.instance.sid}"] = [
                a.associated_footnote.pk for a in associations
            ]

    def clean_duty_sentence(self):
        duty_sentence = self.cleaned_data["duty_sentence"]
        valid_between = self.initial.get("valid_between")
        if duty_sentence and valid_between is not None:
            validate_duties(duty_sentence, valid_between.lower)

        return duty_sentence

    def clean(self):
        cleaned_data = super().clean()

        erga_omnes_instance = (
            GeographicalArea.objects.latest_approved()
            .as_at(self.instance.valid_between.lower)
            .get(
                area_code=1,
                area_id=1011,
            )
        )

        geographical_area_fields = {
            "all": erga_omnes_instance,
            "group": cleaned_data.get("geographical_area_group"),
            "single": cleaned_data.get("geographical_area_country_or_region"),
        }

        if self.data.get("geographical_area_choice"):
            cleaned_data["geographical_area"] = geographical_area_fields[
                self.data.get("geographical_area_choice")
            ]

        cleaned_data["sid"] = self.instance.sid

        return cleaned_data

    def save(self, commit=True):
        """Get the measure instance after form submission, get from session
        storage any footnote pks created via the Footnote formset and any pks
        not removed from the measure after editing and create footnotes via
        FootnoteAssociationMeasure."""
        instance = super().save(commit=False)
        if commit:
            instance.save()

        sid = instance.sid

        if (
            self.request.session[f"instance_duty_sentence_{self.instance.sid}"]
            != self.cleaned_data["duty_sentence"]
        ):
            self.instance.diff_components(
                self.cleaned_data["duty_sentence"],
                self.cleaned_data["valid_between"].lower,
                WorkBasket.current(self.request),
            )

        footnote_pks = [
            dct["footnote"]
            for dct in self.request.session.get(f"formset_initial_{sid}", [])
        ]
        footnote_pks.extend(self.request.session.get(f"instance_footnotes_{sid}", []))

        self.request.session.pop(f"formset_initial_{sid}", None)
        self.request.session.pop(f"instance_footnotes_{sid}", None)

        for pk in footnote_pks:
            footnote = (
                Footnote.objects.filter(pk=pk)
                .approved_up_to_transaction(instance.transaction)
                .first()
            )
            models.FootnoteAssociationMeasure.objects.create(
                footnoted_measure=instance,
                associated_footnote=footnote,
                update_type=UpdateType.CREATE,
                transaction=instance.transaction,
            )

        # Extract conditions data from MeasureForm data
        # formset = MeasureConditionsFormSet(self.data)

        # conditions_data = formset.cleaned_data /PS-IGNORE
        # workbasket = WorkBasket.current(self.request)

        # # Delete all existing conditions from the measure instance
        # for condition in instance.conditions.all():
        #     condition.new_version(workbasket=workbasket, update_type=UpdateType.DELETE)

        # if conditions_data:
        #     measure_creation_pattern = MeasureCreationPattern(
        #         workbasket=workbasket,
        #         base_date=instance.valid_between.lower,
        #     )
        #     parser = DutySentenceParser.get(
        #         instance.valid_between.lower,
        #         component_output=models.MeasureConditionComponent,
        #     )

        #     # Loop over conditions_data, starting at 1 because component_sequence_number has to start at 1 /PS-IGNORE
        #     for component_sequence_number, condition_data in enumerate(
        #         conditions_data, /PS-IGNORE
        #         start=1,
        #     ):
        #         # Create conditions and measure condition components, using instance as `dependent_measure`
        #         measure_creation_pattern.create_condition_and_components(
        #             condition_data,
        #             component_sequence_number,
        #             instance,
        #             parser,
        #         )

        return instance

    def is_valid(self) -> bool:
        """Check that measure conditions data is valid before calling super() on
        the rest of the form data."""
        conditions_formset = MeasureConditionsFormSet(self.data)

        if not conditions_formset.is_valid():
            return False

        return super().is_valid()

    class Meta:
        model = models.Measure
        fields = (
            "valid_between",
            "measure_type",
            "generating_regulation",
            "goods_nomenclature",
            "additional_code",
            "order_number",
            "geographical_area",
        )


class MeasureFilterForm(forms.Form):
    """Generic Filtering form which adds submit and clear buttons, and adds GDS
    formatting to field types."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Field.text("sid", field_width=Fluid.TWO_THIRDS),
                "goods_nomenclature",
                "additional_code",
                "order_number",
                "measure_type",
                "regulation",
                "geographical_area",
                "footnote",
                css_class="govuk-grid-row quarters",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                Div(
                    Field.radios(
                        "start_date_modifier",
                        inline=True,
                    ),
                    "start_date",
                    css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                ),
                Div(
                    Field.radios(
                        "end_date_modifier",
                        inline=True,
                    ),
                    "end_date",
                    css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                ),
                css_class="govuk-grid-row govuk-!-margin-top-6",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )


class MeasureCreateStartForm(forms.Form):
    pass


class MeasureDetailsForm(
    ValidityPeriodForm,
    forms.Form,
):
    class Meta:
        model = models.Measure
        fields = [
            "measure_type",
            "generating_regulation",
            "order_number",
            "valid_between",
        ]

    measure_type = AutoCompleteField(
        label="Measure type",
        help_text="Select the appropriate measure type.",
        queryset=models.MeasureType.objects.all(),
    )
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=Regulation.objects.all(),
    )
    order_number = AutoCompleteField(
        label="Quota order number",
        help_text=(
            "Select the quota order number if a quota measure type has been selected. "
            "Leave this field blank if the measure is not a quota."
        ),
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "measure_type",
            "generating_regulation",
            "order_number",
            "start_date",
            "end_date",
            Submit("submit", "Continue"),
        )

    def clean(self):
        cleaned_data = super().clean()

        if "measure_type" in cleaned_data and "valid_between" in cleaned_data:
            measure_type = cleaned_data["measure_type"]
            if not validity_range_contains_range(
                measure_type.valid_between,
                cleaned_data["valid_between"],
            ):
                raise ValidationError(
                    f"The date range of the measure can't be outside that of the measure type: "
                    f"{measure_type.valid_between} does not contain {cleaned_data['valid_between']}",
                )

        return cleaned_data


class MeasureGeographicalAreaForm(
    GeographicalAreaFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = models.Measure
        fields = [
            "geographical_area",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["geographical_area"].required = False

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            GeographicalAreaSelect("geographical_area"),
            Submit("submit", "Continue"),
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data[self.prefix + "geographical_area"] = cleaned_data.pop(
            self.prefix + "geo_area",
            None,
        )
        return cleaned_data


class MeasureAdditionalCodeForm(forms.ModelForm):
    class Meta:
        model = models.Measure
        fields = [
            "additional_code",
        ]

    additional_code = AutoCompleteField(
        label="Additional code",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "additional_code",
            Submit("submit", "Continue"),
        )


class MeasureCommodityAndDutiesForm(forms.Form):
    commodity = AutoCompleteField(
        label="Commodity code",
        help_text="Select the 10-digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
        attrs={"min_length": 3},
    )

    duties = forms.CharField(
        label="Duties",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        # remove measure_start_date from kwargs here because superclass will not be expecting it
        self.measure_start_date = kwargs.pop("measure_start_date")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.label_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "commodity",
                "duties",
                HTML(
                    loader.render_to_string(
                        "components/duty_help.jinja",
                        context={"component": "measure"},
                    ),
                ),
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        duties = cleaned_data.get("duties", "")
        validate_duties(duties, self.measure_start_date)

        return cleaned_data


class MeasureCommodityAndDutiesFormSet(FormSet):
    form = MeasureCommodityAndDutiesForm


class MeasureFootnotesForm(forms.Form):
    footnote = AutoCompleteField(
        label="",
        queryset=Footnote.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "footnote",
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
                legend="Footnote",
                legend_size=Size.SMALL,
            ),
        )


class MeasureFootnotesFormSet(FormSet):
    form = MeasureFootnotesForm


class MeasureUpdateFootnotesForm(MeasureFootnotesForm):
    """
    Used with edit measure, this form has two buttons each submitting to
    different routes: one for submitting to the edit measure view
    (MeasureUpdate) and the other for submitting to the edit measure footnote
    view (MeasureFootnotesUpdate).

    This is done by setting the submit button's "formaction" attribute. This
    requires that the path is passed here on kwargs, allowing it to be accessed
    and used when rendering the edit forms' submit buttons.
    """

    def __init__(self, *args, **kwargs):
        path = kwargs.pop("path")
        if "edit" in path:
            self.path = path[:-1] + "-footnotes/"

        super().__init__(*args, **kwargs)


class MeasureUpdateFootnotesFormSet(FormSet):
    form = MeasureUpdateFootnotesForm


class MeasureReviewForm(forms.Form):
    pass


MeasureDeleteForm = delete_form_for(models.Measure)
