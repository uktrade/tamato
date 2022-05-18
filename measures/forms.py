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
from django.db.models import TextChoices
from django.forms.formsets import formset_factory
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
from geo_areas.models import GeographicalArea
from geo_areas.util import with_latest_description_string
from geo_areas.validators import AreaCode
from measures import models
from measures.parsers import DutySentenceParser
from measures.util import diff_components
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
        queryset=with_latest_description_string(
            GeographicalArea.objects.filter(
                area_code=1,
            ),
        ),
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
        empty_label=None,
    )
    geographical_area_country_or_region = forms.ModelChoiceField(
        queryset=with_latest_description_string(
            GeographicalArea.objects.exclude(
                area_code=1,
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
                .order_by("descriptions__description")
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
            diff_components(
                instance,
                self.cleaned_data["duty_sentence"],
                self.cleaned_data["valid_between"].lower,
                WorkBasket.current(self.request),
                models.MeasureComponent,
                "component_measure",
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


class GeoAreaForm(forms.Form):
    geo_area = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country or region.",
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )

    def __init__(self, *args, **kwargs):
        tx = kwargs.pop("transaction", None)
        self.transaction = tx
        super().__init__(*args, **kwargs)
        self.fields["geo_area"].queryset = with_latest_description_string(
            GeographicalArea.objects.exclude(
                area_code=AreaCode.GROUP,
                descriptions__description__isnull=True,
            )
            .as_at_today()
            .approved_up_to_transaction(tx)
            .with_latest_links("descriptions")
            .prefetch_related("descriptions")
            .order_by("descriptions__description"),
            # descriptions__description" should make this implicitly distinct()
        )
        self.fields["geo_area"].label_from_instance = lambda obj: obj.description


class ErgaOmnesExclusionsForm(forms.Form):
    erga_omnes_exclusion = forms.ModelChoiceField(
        label="Select a country to be excluded",
        queryset=GeographicalArea.objects.all(),
        help_text="To exclude countries, enter them below.",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        tx = kwargs.pop("transaction", None)
        self.transaction = tx
        super().__init__(*args, **kwargs)
        self.fields["erga_omnes_exclusion"].queryset = with_latest_description_string(
            GeographicalArea.objects.exclude(
                descriptions__description__isnull=True,
            )
            .as_at_today()
            .approved_up_to_transaction(tx)
            .with_latest_links("descriptions")
            .prefetch_related("descriptions")
            .order_by("descriptions__description"),
            # descriptions__description" should make this implicitly distinct()
        )
        self.fields[
            "erga_omnes_exclusion"
        ].label_from_instance = lambda obj: obj.description


GeoAreaFormSet = formset_factory(
    GeoAreaForm,
    formset=FormSet,
    min_num=1,
    max_num=2,
    extra=1,
    validate_min=True,
    validate_max=True,
)

ErgaOmnesExclusionsFormSet = formset_factory(
    ErgaOmnesExclusionsForm,
    formset=FormSet,
    min_num=1,
    max_num=10,
    extra=1,
    validate_min=True,
    validate_max=True,
)


class MeasureGeographicalAreaForm(forms.ModelForm):
    class Meta:
        model = models.Measure
        fields = [
            "geographical_area",
        ]

    class GeoAreaType(TextChoices):
        ERGA_OMNES = "ERGA_OMNES", "All countries (erga omnes)"
        GROUP = "GROUP", "A group of countries"
        COUNTRY = "COUNTRY", "Specific countries or regions"

    geo_area_type = forms.ChoiceField(choices=GeoAreaType.choices, required=False)
    geo_group = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country group.",
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )
    geo_group_exclusions = forms.ModelMultipleChoiceField(
        queryset=GeographicalArea.objects.all(),
        help_text="Select country exclusions.",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        tx = kwargs.pop("transaction", None)
        self.transaction = tx
        super().__init__(*args, **kwargs)
        self.geo_area_subform_prefix = "geo_area_formset"
        self.geo_area_subform = GeoAreaFormSet(
            data=self.data, prefix=self.geo_area_subform_prefix
        )
        self.erga_omnes_exclusions_subform_prefix = "erga_omnes_exclusions_formset"
        self.erga_omnes_exclusions_subform = ErgaOmnesExclusionsFormSet(
            data=self.data, prefix=self.erga_omnes_exclusions_subform_prefix
        )

        self.fields["geographical_area"].required = False

        self.fields["geo_group"].queryset = with_latest_description_string(
            GeographicalArea.objects.filter(
                area_code=AreaCode.GROUP,
            )
            .exclude(descriptions__description__isnull=True)
            .as_at_today()
            .approved_up_to_transaction(tx)
            .with_latest_links("descriptions")
            .prefetch_related("descriptions")
            .order_by("descriptions__description"),
            # descriptions__description" should make this implicitly distinct()
        )
        # self.fields[
        #     "geo_group_exclusions"
        # ].queryset = GeographicalArea.objects.approved_up_to_transaction(tx)

        for field in ["geo_group"]:
            self.fields[field].label_from_instance = lambda obj: obj.description

    def clean(self):
        cleaned_data = super().clean()
        geo_area_list = None
        if self.geo_area_subform.is_valid():
            geo_area_list = [
                item["geo_area"] for item in self.geo_area_subform.cleaned_data
            ]

        erga_omnes_exclusions = None
        if self.erga_omnes_exclusions_subform.is_valid():
            erga_omnes_exclusions = [
                item["erga_omnes_exclusion"]
                for item in self.erga_omnes_exclusions_subform.cleaned_data
            ]

        geo_area_type = cleaned_data.pop("geo_area_type", None)
        # erga_omnes_exclusions = cleaned_data.pop("erga_omnes_exclusions", None)
        geo_group = cleaned_data.pop("geo_group", None)
        geo_group_exclusions = cleaned_data.pop("geo_group_exclusions", None)

        if geo_area_type == self.GeoAreaType.ERGA_OMNES:
            cleaned_data["geo_area_list"] = [
                (
                    GeographicalArea.objects.approved_up_to_transaction(
                        self.transaction
                    )
                    .erga_omnes()
                    .get()
                )
            ]
            cleaned_data["geo_area_exclusions"] = erga_omnes_exclusions

        self.fields["geo_area_type"].initial = geo_area_type

        # Don't try to validate the whole form when user clicks add or delete on the country geo_area_subform
        geo_area_subform_submit = self.geo_area_subform.formset_action in [
            "ADD",
            "DELETE",
        ]

        if geo_area_type == self.GeoAreaType.ERGA_OMNES:
            cleaned_data["geo_area_exclusions"] = erga_omnes_exclusions

        if geo_area_type == self.GeoAreaType.GROUP:
            if not geo_group and not geo_area_subform_submit:
                raise ValidationError({"geo_group": "A country group is required."})
            cleaned_data["geo_area_list"] = [geo_group]
            cleaned_data["geo_area_exclusions"] = geo_group_exclusions

        if geo_area_type == self.GeoAreaType.COUNTRY:
            if not geo_area_list and not geo_area_subform_submit:
                raise ValidationError("One or more countries or regions is required.")
            cleaned_data["geo_area_list"] = geo_area_list

        self.fields["geo_group"].initial = geo_group.pk if geo_group else None

        if not cleaned_data.get("geo_area_list") and not geo_area_subform_submit:
            raise ValidationError("A Geographical area must be selected")

        return cleaned_data

    def is_valid(self):
        geo_area_type = self.data.get(f"{self.prefix}-geo_area_type", None)
        if geo_area_type == self.GeoAreaType.COUNTRY:
            return super().is_valid() and self.geo_area_subform.is_valid()
        elif geo_area_type == self.GeoAreaType.ERGA_OMNES:
            if self.erga_omnes_exclusions_subform.formset_action in [
                "ADD",
                "DELETE",
            ]:
                return (
                    super().is_valid() and self.erga_omnes_exclusions_subform.is_valid()
                )
        return super().is_valid()


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
