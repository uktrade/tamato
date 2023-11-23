from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import ValidationError

from common.forms import BindNestedFormMixin
from common.forms import CreateDescriptionForm
from common.forms import DateInputFieldFixed
from common.forms import FormSet
from common.forms import GovukDateRangeField
from common.forms import RadioNested
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.forms import formset_factory
from common.util import TaricDateRange
from common.validators import SymbolValidator
from geo_areas import constants
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode
from geo_areas.validators import DateValidationMixin
from geo_areas.validators import area_id_validator
from quotas.models import QuotaOrderNumberOrigin
from workbaskets.models import WorkBasket


class GeographicalAreaCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            0,
            Field(
                "described_geographicalarea",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Geographical area description"
        self.fields["description"].validators = [SymbolValidator]

    class Meta:
        model = GeographicalAreaDescription
        fields = ("described_geographicalarea", "description", "validity_start")


GeographicalAreaDeleteForm = delete_form_for(GeographicalArea)


GeographicalAreaDescriptionDeleteForm = delete_form_for(GeographicalAreaDescription)


class GeoMembershipAction(TextChoices):
    END_DATE = "END DATE", "End date"
    DELETE = "DELETE", "Delete"


class GeoAreaType(TextChoices):
    COUNTRY = "COUNTRY", "Add a country"
    REGION = "REGION", "Add a region"


class GeoAreaCountryForm(forms.Form):
    country = forms.ModelChoiceField(
        label="Country",
        queryset=None,  # populated in __init__
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["country"].queryset = (
            GeographicalArea.objects.filter(area_code=AreaCode.COUNTRY)
            .current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "country"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


class GeoAreaRegionForm(forms.Form):
    region = forms.ModelChoiceField(
        label="Region",
        queryset=None,  # populated in __init__
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["region"].queryset = (
            GeographicalArea.objects.filter(area_code=AreaCode.REGION)
            .current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "region"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


class GeographicalMembershipEndDateForm(forms.Form):
    membership_end_date = DateInputFieldFixed(
        label="",
        help_text="Leave empty if the membership is needed for an unlimited time.",
        required=False,
    )


class GeographicalMembershipValidityPeriodForm(forms.ModelForm):
    new_membership_start_date = DateInputFieldFixed(
        label="Start date",
        required=False,
    )
    new_membership_end_date = DateInputFieldFixed(
        label="End date",
        help_text="Leave empty if the membership is needed for an unlimited time.",
        required=False,
    )
    new_membership_valid_between = GovukDateRangeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.pop("new_membership_start_date", None)
        end_date = cleaned_data.pop("new_membership_end_date", None)

        cleaned_data["new_membership_valid_between"] = TaricDateRange(
            start_date,
            end_date,
        )

        if start_date:
            day, month, year = (start_date.day, start_date.month, start_date.year)
            self.fields["new_membership_start_date"].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        if end_date:
            day, month, year = (end_date.day, end_date.month, end_date.year)
            self.fields["new_membership_end_date"].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        return cleaned_data


class GeographicalMembershipAddForm(
    BindNestedFormMixin,
    DateValidationMixin,
    GeographicalMembershipValidityPeriodForm,
):
    geo_group = forms.ModelChoiceField(
        help_text="Select the area group to add this country or region to from the dropdown.",
        queryset=None,  # populated in __init__
        required=False,
    )

    member = RadioNested(
        help_text="Select a country or region to add to this area group.",
        choices=GeoAreaType.choices,
        nested_forms={
            GeoAreaType.COUNTRY.value: [GeoAreaCountryForm],
            GeoAreaType.REGION.value: [GeoAreaRegionForm],
        },
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["geo_group"].queryset = (
            GeographicalArea.objects.filter(area_code=AreaCode.GROUP)
            .current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "geo_group"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"

        self.fields["geo_group"].label = ""
        self.fields["member"].label = ""

    def clean(self):
        cleaned_data = super().clean()

        # Get the selected country or region from nested forms
        geo_area_choice = cleaned_data.get("member", "")
        if geo_area_choice == GeoAreaType.COUNTRY:
            cleaned_data["member"] = cleaned_data.get("country")
        else:
            cleaned_data["member"] = cleaned_data.get("region")

        area_group = (
            self.instance if self.instance.is_group() else cleaned_data["geo_group"]
        )
        member = (
            self.instance if not self.instance.is_group() else cleaned_data["member"]
        )
        start_date = cleaned_data["new_membership_valid_between"].lower
        end_date = cleaned_data["new_membership_valid_between"].upper

        if not start_date and area_group and member:
            self.add_error(
                "new_membership_start_date",
                "A start date is required.",
            )

        if area_group and member and start_date:
            # Check if membership already exists
            is_member = (
                GeographicalMembership.objects.filter(
                    geo_group=self.instance,
                    member=member,
                )
                .current()
                .as_at_and_beyond(start_date)
            )
            has_member = (
                GeographicalMembership.objects.filter(
                    geo_group=area_group,
                    member=self.instance,
                )
                .current()
                .as_at_and_beyond(start_date)
            )
            if is_member:
                self.add_error(
                    "member",
                    "The selected country or region is already a member of this area group.",
                )
            if has_member:
                self.add_error(
                    "geo_group",
                    "The selected area group already has this country or region as a member.",
                )

            self.validate_dates(
                field="new_membership_start_date",
                start_date=start_date,
                container_start_date=area_group.valid_between.lower,
            )
            self.validate_dates(
                field="new_membership_end_date",
                start_date=start_date,
                end_date=end_date,
                container_end_date=area_group.valid_between.upper,
            )

        return cleaned_data

    class Meta:
        model = GeographicalMembership
        fields = ["geo_group", "member"]


class GeographicalMembershipEditForm(
    BindNestedFormMixin,
    DateValidationMixin,
    forms.Form,
):
    membership = forms.ModelChoiceField(
        label="",
        queryset=None,  # populated in __init__
        required=False,
    )

    action = RadioNested(
        label="",
        choices=GeoMembershipAction.choices,
        nested_forms={
            GeoMembershipAction.END_DATE.value: [GeographicalMembershipEndDateForm],
            GeoMembershipAction.DELETE.value: [],
        },
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["membership"].queryset = self.instance.get_current_memberships()

        self.fields["membership"].label_from_instance = self.label_from_instance

        self.fields["membership"].help_text = (
            "Select a country or region from the dropdown to edit the membership of this area group."
            if self.instance.is_group()
            else "Select an area group from the dropdown to edit the membership of this country or region."
        )

    def label_from_instance(self, obj):
        validity_period = f" ({obj.valid_between.lower} - {obj.valid_between.upper})"
        if self.instance.is_group():
            return (
                f"{obj.member.area_id} - {obj.member.structure_description}"
                + validity_period
            )
        else:
            return (
                f"{obj.geo_group.area_id} - {obj.geo_group.structure_description}"
                + validity_period
            )

    def clean(self):
        cleaned_data = super().clean()

        membership = cleaned_data.get("membership")
        action = cleaned_data.get("action")
        end_date = cleaned_data.get("membership_end_date")

        if membership and action == GeoMembershipAction.END_DATE:
            self.validate_dates(
                field="",
                end_date=end_date,
                container_end_date=membership.geo_group.valid_between.upper,
            )
            self.validate_dates(
                field="",
                end_date=end_date,
                container_start_date=membership.geo_group.valid_between.lower,
            )

        if membership and action == GeoMembershipAction.DELETE:
            tx = WorkBasket.get_current_transaction(self.request)
            if membership.member_used_in_measure_exclusion(transaction=tx):
                self.add_error(
                    "membership",
                    f"{membership.member.structure_description} is referenced as an excluded geographical area in a measure and cannot be deleted as a member of the area group.",
                )

        return cleaned_data


class GeographicalAreaEndDateForm(ValidityPeriodForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["start_date"].required = False
        self.fields["end_date"].label = ""
        self.fields[
            "end_date"
        ].help_text = "End date this geographical area. Leave empty if the geographical area is needed for an unlimited time."

    def clean(self):
        self.cleaned_data["start_date"] = self.instance.valid_between.lower
        end_date = self.cleaned_data.get("end_date")
        if end_date:
            origins = QuotaOrderNumberOrigin.objects.current().filter(
                geographical_area__sid=self.instance.sid,
            )
            for origin in origins:
                if (
                    not origin.valid_between.upper
                    or origin.valid_between.upper < end_date
                ):
                    raise ValidationError(
                        {
                            "end_date": "The end date must span the validity period of the quota order number origin that specifies this geographical area.",
                        },
                    )
        return super().clean()

    class Meta:
        model = GeographicalArea
        fields = ("valid_between",)


class GeographicalAreaEditForm(
    GeographicalAreaEndDateForm,
    GeographicalMembershipAddForm,
    GeographicalMembershipEditForm,
):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Which geographical membership form field is shown depends
        # on the type of geographical area being edited
        if self.instance.is_group():
            form_field = "member"
        else:
            form_field = "geo_group"

        self.bind_nested_forms(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Add membership",
                    form_field,
                    "new_membership_start_date",
                    "new_membership_end_date",
                ),
                AccordionSection(
                    "Edit membership",
                    "membership",
                    "action",
                    HTML.warning(
                        "Deleting a country or region from an area group will make it as though it was never a member, "
                        "which may have implications for users of the tariff data. "
                        "You should only delete a member if end dating the membership is not appropriate.",
                    ),
                ),
                AccordionSection("End date", "end_date"),
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class GeographicalAreaCreateForm(ValidityPeriodForm):
    area_code = forms.ChoiceField(
        label="Area code",
        help_text="Select if the new geographical area is a country, area group or region from the dropdown.",
        choices=AreaCode.choices,
        error_messages={"required": "Select an area code from the dropdown."},
    )

    area_id = forms.CharField(
        label="Area ID",
        help_text="For a country or region, the area ID is 2 upper-case letters, like AZ. For an area group, the area ID is 4 digits, like 1234.",
        widget=forms.TextInput,
        validators=[area_id_validator],
        error_messages={
            "required": "Enter a geographical area ID.",
            "invalid": "Enter a geographical area ID in the correct format.",
        },
    )

    description = forms.CharField(
        label="Description",
        help_text="The name of the country, area group or region.",
        widget=forms.Textarea,
        validators=[SymbolValidator],
        error_messages={"required": "Enter a geographical area description."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "end_date"
        ].help_text = (
            "Leave empty if the geographical area is needed for an unlimited time."
        )

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "area_code",
            Field(
                "area_id",
                css_class="govuk-input govuk-input--width-4",
                maxlength="4",
            ),
            "start_date",
            "end_date",
            Field.textarea("description", label_size=Size.SMALL, rows=3),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        cleaned_data["geographical_area_description"] = GeographicalAreaDescription(
            description=cleaned_data.get("description"),
            validity_start=cleaned_data["valid_between"].lower,
        )

        return cleaned_data

    class Meta:
        model = GeographicalArea
        fields = ["valid_between", "area_id", "area_code"]


class GeographicalAreaEditCreateForm(GeographicalAreaCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["description"].required = False

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "area_code",
            Field(
                "area_id",
                css_class="govuk-input govuk-input--width-4",
                maxlength="4",
            ),
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class GeographicalMembershipGroupForm(DateValidationMixin, ValidityPeriodForm):
    geo_group = forms.ModelChoiceField(
        label="Area group",
        help_text="Select an area group to add this country or region to from the dropdown.",
        queryset=None,  # populated in __init__
    )

    def __init__(self, *args, **kwargs):
        self.geo_area = kwargs.pop("geo_area", None)
        super().__init__(*args, **kwargs)

        current_memberships = self.geo_area.groups.values_list("geo_group", flat=True)

        self.fields["geo_group"].queryset = (
            GeographicalArea.objects.filter(area_code=AreaCode.GROUP)
            .exclude(pk__in=current_memberships)
            .current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "geo_group"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"

        self.fields["end_date"].help_text = ""

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Fieldset(
                Div(
                    Field("geo_group"),
                    css_class="govuk-grid-column-one-half error-align",
                ),
                Div(
                    Field("start_date"),
                    css_class="govuk-grid-column-one-quarter error-align",
                ),
                Div(
                    Field("end_date"),
                    css_class="govuk-grid-column-one-quarter error-align",
                ),
                css_class="membership-inline",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        geo_group = cleaned_data.get("geo_group")
        if geo_group:
            start_date = cleaned_data["valid_between"].lower
            end_date = cleaned_data["valid_between"].upper
            self.validate_dates(
                field="start_date",
                start_date=start_date,
                container_start_date=geo_group.valid_between.lower,
            )
            self.validate_dates(
                field="start_date",
                start_date=start_date,
                container="country or region",
                container_start_date=self.geo_area.valid_between.lower,
            )
            self.validate_dates(
                field="end_date",
                end_date=end_date,
                container_end_date=geo_group.valid_between.upper,
            )
            self.validate_dates(
                field="end_date",
                end_date=end_date,
                container="country or region",
                container_end_date=self.geo_area.valid_between.upper,
            )

        return cleaned_data

    class Meta:
        model = GeographicalMembership
        fields = ["valid_between", "geo_group"]


class GeographicalMembershipMemberForm(DateValidationMixin, ValidityPeriodForm):
    member = forms.ModelChoiceField(
        label="Country or region",
        help_text="Select a country or region to add to this area group from the dropdown.",
        queryset=None,  # populated in __init__
    )

    def __init__(self, *args, **kwargs):
        self.geo_area = kwargs.pop("geo_area", None)
        super().__init__(*args, **kwargs)

        current_memberships = self.geo_area.memberships.all()

        self.fields["member"].queryset = (
            GeographicalArea.objects.exclude(area_code=AreaCode.GROUP)
            .exclude(
                pk__in=current_memberships,
            )
            .current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "member"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"

        self.fields["end_date"].help_text = ""

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Fieldset(
                Div(
                    Field("member"),
                    css_class="govuk-grid-column-one-half error-align",
                ),
                Div(
                    Field("start_date"),
                    css_class="govuk-grid-column-one-quarter error-align",
                ),
                Div(
                    Field("end_date"),
                    css_class="govuk-grid-column-one-quarter error-align",
                ),
                css_class="membership-inline",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        member = self.cleaned_data.get("member")
        if member:
            start_date = cleaned_data["valid_between"].lower
            end_date = cleaned_data["valid_between"].upper
            self.validate_dates(
                field="start_date",
                start_date=start_date,
                container_start_date=self.geo_area.valid_between.lower,
            )
            self.validate_dates(
                field="start_date",
                start_date=start_date,
                container="country or region",
                container_start_date=member.valid_between.lower,
            )
            self.validate_dates(
                field="end_date",
                end_date=end_date,
                container_end_date=self.geo_area.valid_between.upper,
            )
            self.validate_dates(
                field="end_date",
                end_date=end_date,
                container="country or region",
                container_end_date=member.valid_between.upper,
            )

        return cleaned_data

    class Meta:
        model = GeographicalMembership
        fields = ["valid_between", "member"]


class GeographicalMembershipBaseFormSet(FormSet):
    extra = 0
    min_num = 1
    validate_min = True
    validate_max = True

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)


class GeographicalMembershipGroupFormSet(GeographicalMembershipBaseFormSet):
    prefix = "geo_membership-group-formset"
    form = GeographicalMembershipGroupForm

    def clean(self):
        if any(self.errors):
            return

        cleaned_data = super().cleaned_data

        geo_groups = [d["geo_group"] for d in cleaned_data if "geo_group" in d]
        num_unique = len(set(geo_groups))
        if len(geo_groups) != num_unique:
            raise ValidationError(
                "The same area group cannot be selected more than once.",
            )
        cleaned_data[0]["geo_groups"] = geo_groups

        return cleaned_data


class GeographicalMembershipMemberFormSet(GeographicalMembershipBaseFormSet):
    prefix = "geo_membership-member-formset"
    form = GeographicalMembershipMemberForm

    def clean(self):
        if any(self.errors):
            return

        cleaned_data = super().cleaned_data

        members = [d["member"] for d in cleaned_data if "member" in d]
        num_unique = len(set(members))
        if len(members) != num_unique:
            raise ValidationError(
                "The same country or region cannot be selected more than once.",
            )
        cleaned_data[0]["members"] = members

        return cleaned_data


class ErgaOmnesExclusionsForm(forms.Form):
    prefix = constants.ERGA_OMNES_EXCLUSIONS_PREFIX

    erga_omnes_exclusion = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["erga_omnes_exclusion"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "erga_omnes_exclusion"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


ErgaOmnesExclusionsFormSet = formset_factory(
    ErgaOmnesExclusionsForm,
    prefix=constants.ERGA_OMNES_EXCLUSIONS_FORMSET_PREFIX,
    formset=FormSet,
    min_num=0,
    max_num=100,
    extra=0,
    validate_min=True,
    validate_max=True,
)


class GeoGroupForm(forms.Form):
    prefix = constants.GEO_GROUP_PREFIX

    geographical_area_group = forms.ModelChoiceField(
        label="",
        queryset=None,  # populated in __init__
        error_messages={"required": "A country group is required."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geographical_area_group"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .filter(area_code=AreaCode.GROUP)
            .as_at_today_and_beyond()
            .order_by("description")
        )
        # descriptions__description" should make this implicitly distinct()
        self.fields[
            "geographical_area_group"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"

        if self.initial.get("geo_area") == constants.GeoAreaType.GROUP.value:
            self.initial["geographical_area_group"] = self.initial["geographical_area"]


class GeoGroupExclusionsForm(forms.Form):
    prefix = constants.GROUP_EXCLUSIONS_PREFIX

    geo_group_exclusion = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geo_group_exclusion"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields[
            "geo_group_exclusion"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


GeoGroupFormSet = formset_factory(
    GeoGroupForm,
    prefix=constants.GEO_GROUP_FORMSET_PREFIX,
    formset=FormSet,
    min_num=1,
    max_num=2,
    extra=0,
    validate_min=True,
    validate_max=True,
)


GeoGroupExclusionsFormSet = formset_factory(
    GeoGroupExclusionsForm,
    prefix=constants.GROUP_EXCLUSIONS_FORMSET_PREFIX,
    formset=FormSet,
    min_num=0,
    max_num=100,
    extra=0,
    validate_min=True,
    validate_max=True,
)


class CountryRegionForm(forms.Form):
    prefix = constants.COUNTRY_REGION_PREFIX

    geographical_area_country_or_region = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.exclude(
            area_code=AreaCode.GROUP,
            descriptions__description__isnull=True,
        ),
        error_messages={"required": "A country or region is required."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geographical_area_country_or_region"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .exclude(area_code=AreaCode.GROUP)
            .as_at_today_and_beyond()
            .order_by("description")
        )

        self.fields[
            "geographical_area_country_or_region"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"

        if self.initial.get("geo_area") == constants.GeoAreaType.COUNTRY.value:
            self.initial["geographical_area_country_or_region"] = self.initial[
                "geographical_area"
            ]


CountryRegionFormSet = formset_factory(
    CountryRegionForm,
    prefix=constants.COUNTRY_REGION_FORMSET_PREFIX,
    formset=FormSet,
    min_num=1,
    max_num=2,
    extra=0,
    validate_min=True,
    validate_max=True,
)

QuotaCountryRegionFormSet = formset_factory(
    CountryRegionForm,
    prefix=constants.COUNTRY_REGION_FORMSET_PREFIX,
    formset=FormSet,
    min_num=1,
    max_num=100,
    extra=0,
    validate_min=True,
    validate_max=True,
)
