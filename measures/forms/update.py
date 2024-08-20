from django import forms
from django.core.exceptions import ValidationError

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import BindNestedFormMixin
from common.forms import RadioNested
from common.forms import ValidityPeriodForm
from common.forms import unprefix_formset_data
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas import constants
from geo_areas.forms import CountryRegionForm
from geo_areas.forms import ErgaOmnesExclusionsFormSet
from geo_areas.forms import GeoGroupExclusionsFormSet
from geo_areas.forms import GeoGroupForm
from geo_areas.models import GeographicalArea
from geo_areas.utils import get_all_members_of_geo_groups
from measures import models
from measures.duty_sentence_parser import DutySentenceParser as LarkDutySentenceParser
from measures.models import MeasureExcludedGeographicalArea
from measures.util import diff_components
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

from . import MeasureConditionsBaseFormSet
from . import MeasureConditionsFormMixin
from . import MeasureValidityForm
from . import mixins


class MeasureConditionsForm(MeasureConditionsFormMixin):
    # override action queryset for edit form, gets all actions
    action = forms.ModelChoiceField(
        label="Action code",
        queryset=models.MeasureAction.objects.latest_approved(),
        empty_label="-- Please select an action code --",
        error_messages={"required": "An action code is required."},
    )

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
        measure_start_date = self.get_start_date(self.data)

        if applicable_duty and measure_start_date is not None:
            duty_sentence_parser = LarkDutySentenceParser(date=measure_start_date)
            try:
                duty_sentence_parser.transform(applicable_duty)
            except (SyntaxError, ValidationError) as e:
                self.add_error("applicable_duty", e)

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

        # Check if the action code set for the form is
        is_negative_action_code = models.MeasureActionPair.objects.filter(
            negative_action=cleaned_data.get("action"),
        ).exists()
        return self.conditions_clean(
            cleaned_data,
            measure_start_date,
            is_negative_action_code=is_negative_action_code,
        )


class MeasureConditionsFormSet(MeasureConditionsBaseFormSet):
    form = MeasureConditionsForm


class MeasureForm(
    mixins.MeasureGeoAreaInitialDataMixin,
    ValidityPeriodForm,
    BindNestedFormMixin,
    forms.ModelForm,
):
    """Form used for editing individual Measures."""

    class Meta:
        model = models.Measure
        fields = (
            "valid_between",
            "measure_type",
            "generating_regulation",
            "goods_nomenclature",
            "additional_code",
            "order_number",
        )

    geo_area_field_name = "geo_area"

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
        help_text=(
            "Search for an additional code by typing in the code's number or a keyword. "
            "A dropdown list will appear after a few seconds. You can then select the correct code from the dropdown list."
        ),
        queryset=AdditionalCode.objects.all(),
        required=False,
    )
    order_number = AutoCompleteField(
        label="Order number",
        help_text="Enter the quota order number if a quota measure type has been selected. Leave this field blank if the measure is not a quota.",
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )
    geo_area = RadioNested(
        label="Geographical area",
        choices=constants.GeoAreaType.choices,
        nested_forms={
            constants.GeoAreaType.ERGA_OMNES.value: [ErgaOmnesExclusionsFormSet],
            constants.GeoAreaType.GROUP.value: [
                GeoGroupForm,
                GeoGroupExclusionsFormSet,
            ],
            constants.GeoAreaType.COUNTRY.value: [CountryRegionForm],
        },
        error_messages={"required": "A Geographical area must be selected"},
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        tx = WorkBasket.get_current_transaction(self.request)

        self.initial["duty_sentence"] = self.instance.duty_sentence
        self.request.session[f"instance_duty_sentence_{self.instance.sid}"] = (
            self.instance.duty_sentence
        )

        if self.instance.geographical_area.is_all_countries():
            self.initial["geo_area"] = constants.GeoAreaType.ERGA_OMNES.value

        elif self.instance.geographical_area.is_group():
            self.initial["geo_area"] = constants.GeoAreaType.GROUP.value

        else:
            self.initial["geo_area"] = constants.GeoAreaType.COUNTRY.value

        # If no footnote keys are stored in the session for a measure,
        # store all the pks of a measure's footnotes on the session, using the measure sid as key
        if f"instance_footnotes_{self.instance.sid}" not in self.request.session.keys():
            tx = WorkBasket.get_current_transaction(self.request)
            associations = (
                models.FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                    tx,
                ).filter(
                    footnoted_measure__sid=self.instance.sid,
                )
            )
            self.request.session[f"instance_footnotes_{self.instance.sid}"] = [
                a.associated_footnote.pk for a in associations
            ]

        nested_forms_initial = {**self.initial}
        nested_forms_initial["geographical_area"] = self.instance.geographical_area
        geo_area_initial_data = self.get_geo_area_initial()
        nested_forms_initial.update(geo_area_initial_data)
        kwargs.pop("initial")
        self.bind_nested_forms(*args, initial=nested_forms_initial, **kwargs)

    def clean_duty_sentence(self):
        duty_sentence = self.cleaned_data["duty_sentence"]
        valid_between = self.initial.get("valid_between")
        if duty_sentence and valid_between is not None:
            duty_sentence_parser = LarkDutySentenceParser(date=valid_between.lower)
            try:
                duty_sentence_parser.transform(duty_sentence)
            except (SyntaxError, ValidationError) as e:
                raise ValidationError(e)

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
            constants.GeoAreaType.ERGA_OMNES: erga_omnes_instance,
            constants.GeoAreaType.GROUP: cleaned_data.get("geographical_area_group"),
            constants.GeoAreaType.COUNTRY: cleaned_data.get(
                "geographical_area_country_or_region",
            ),
        }

        if self.data.get("geo_area"):
            geo_area_choice = self.data.get("geo_area")
            cleaned_data["geographical_area"] = geographical_area_fields[
                geo_area_choice
            ]
            exclusions = cleaned_data.get(
                constants.FORMSET_PREFIX_MAPPING[geo_area_choice],
            )
            if exclusions:
                cleaned_data["exclusions"] = [
                    exclusion[constants.FIELD_NAME_MAPPING[geo_area_choice]]
                    for exclusion in exclusions
                ]

        cleaned_data["sid"] = self.instance.sid

        return cleaned_data

    def save(self, commit=True):
        """Updates a measure instance's geographical area and exclusions,
        duties, and footnote associations following form submission."""
        instance = super().save(commit=False)
        if commit:
            instance.save()

        sid = instance.sid

        geo_area = self.cleaned_data.get("geographical_area")
        if geo_area and geo_area != instance.geographical_area:
            instance.geographical_area = geo_area
            instance.save(update_fields=["geographical_area"])

        if self.cleaned_data.get("exclusions"):
            exclusions = self.cleaned_data.get("exclusions")

            all_exclusions = get_all_members_of_geo_groups(
                instance.valid_between,
                exclusions,
            )

            for geo_area in all_exclusions:
                existing_exclusion = (
                    instance.exclusions.filter(excluded_geographical_area=geo_area)
                    .current()
                    .first()
                )

                if existing_exclusion:
                    existing_exclusion.new_version(
                        workbasket=WorkBasket.current(self.request),
                        transaction=instance.transaction,
                        modified_measure=instance,
                    )
                else:
                    MeasureExcludedGeographicalArea.objects.create(
                        modified_measure=instance,
                        excluded_geographical_area=geo_area,
                        update_type=UpdateType.CREATE,
                        transaction=instance.transaction,
                    )

            removed_excluded_areas = {
                e.excluded_geographical_area for e in instance.exclusions.current()
            }.difference(set(self.cleaned_data["exclusions"]))

            removed_exclusions = [
                instance.exclusions.current().get(excluded_geographical_area__id=e.id)
                for e in removed_excluded_areas
            ]

            for removed in removed_exclusions:
                removed.new_version(
                    update_type=UpdateType.DELETE,
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                    modified_measure=instance,
                )

        if (
            self.request.session[f"instance_duty_sentence_{self.instance.sid}"]
            != self.cleaned_data["duty_sentence"]
        ):
            diff_components(
                instance,
                self.cleaned_data["duty_sentence"],
                self.cleaned_data["valid_between"].lower,
                WorkBasket.current(self.request),
                # Creating components in the same transaction as the new version
                # of the measure minimises number of transaction and groups the
                # creation of measure and related objects in the same
                # transaction.
                instance.transaction,
                models.MeasureComponent,
                "component_measure",
            )

        # Footnotes added via "Add another footnote" button
        footnote_pks = [
            form["footnote"]
            for form in self.request.session.get(f"formset_initial_{sid}", [])
        ]

        # Footnote submitted directly via "Save" button
        form_footnote = self.request.POST.get(
            f"form-{len(footnote_pks)}-footnote",
            None,
        )
        if form_footnote:
            footnote_pks.append(form_footnote)

        # Footnotes already on measure
        footnote_pks.extend(self.request.session.get(f"instance_footnotes_{sid}", []))

        self.request.session.pop(f"formset_initial_{sid}", None)
        self.request.session.pop(f"instance_footnotes_{sid}", None)

        removed_associations = (
            instance.footnoteassociationmeasure_set.current().exclude(
                associated_footnote__pk__in=footnote_pks,
            )
        )
        for association in removed_associations:
            association.new_version(
                workbasket=WorkBasket.current(self.request),
                transaction=instance.transaction,
                footnoted_measure=instance,
                update_type=UpdateType.DELETE,
            )

        for pk in footnote_pks:
            footnote = (
                Footnote.objects.filter(pk=pk)
                .approved_up_to_transaction(instance.transaction)
                .first()
            )

            existing_association = (
                models.FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                    instance.transaction,
                )
                .filter(
                    footnoted_measure__sid=instance.sid,
                    associated_footnote__footnote_id=footnote.footnote_id,
                    associated_footnote__footnote_type__footnote_type_id=footnote.footnote_type.footnote_type_id,
                )
                .first()
            )
            if existing_association:
                existing_association.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                    footnoted_measure=instance,
                )
            else:
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
        initial = unprefix_formset_data(
            MeasureConditionsFormSet.prefix,
            self.data.copy(),
        )
        conditions_formset = MeasureConditionsFormSet(
            self.data,
            initial=initial,
        )
        if not conditions_formset.is_valid():
            return False

        return super().is_valid()
