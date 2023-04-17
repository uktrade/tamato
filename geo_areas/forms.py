from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.db.models import TextChoices

from common.forms import BindNestedFormMixin
from common.forms import CreateDescriptionForm
from common.forms import DateInputFieldFixed
from common.forms import GovukDateRangeField
from common.forms import RadioNested
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.util import TaricDateRange
from common.validators import SymbolValidator
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode
from geo_areas.validators import validate_dates
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
            .as_at_today()
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
            .as_at_today()
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
            .as_at_today()
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

        if area_group and member:
            # Check if membership already exists
            is_member = GeographicalMembership.objects.filter(
                geo_group=self.instance,
                member=member,
            )
            has_member = GeographicalMembership.objects.filter(
                geo_group=area_group,
                member=self.instance,
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

            if not start_date:
                self.add_error(
                    "new_membership_start_date",
                    "A start date is required.",
                )
            validate_dates(
                form=self,
                field="new_membership_start_date",
                start_date=start_date,
                group_start_date=area_group.valid_between.lower,
            )
            validate_dates(
                form=self,
                field="new_membership_end_date",
                start_date=start_date,
                end_date=end_date,
                group_end_date=area_group.valid_between.upper,
            )

        return cleaned_data

    class Meta:
        model = GeographicalMembership
        fields = ["geo_group", "member"]


class GeographicalMembershipEditForm(BindNestedFormMixin, forms.Form):
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

        self.fields["membership"].label_from_instance = (
            lambda obj: f"{obj.member.area_id} - {obj.member.structure_description}"
            if self.instance.is_group()
            else f"{obj.geo_group.area_id} - {obj.geo_group.structure_description}"
        )

        self.fields["membership"].help_text = (
            "Select a country or region from the dropdown to edit the membership of this area group."
            if self.instance.is_group()
            else "Select an area group from the dropdown to edit the membership of this country or region."
        )

    def clean(self):
        cleaned_data = super().clean()

        membership = cleaned_data.get("membership")
        action = cleaned_data.get("action")
        end_date = cleaned_data.get("membership_end_date")

        if membership and action == GeoMembershipAction.END_DATE:
            validate_dates(
                form=self.fields["action"].nested_forms["END DATE"][0],
                field="membership_end_date",
                end_date=end_date,
                group_end_date=membership.geo_group.valid_between.upper,
            )
            validate_dates(
                form=self,
                field="",
                end_date=end_date,
                group_end_date=membership.geo_group.valid_between.upper,
            )
            validate_dates(
                form=self.fields["action"].nested_forms["END DATE"][0],
                field="membership_end_date",
                end_date=end_date,
                group_start_date=membership.geo_group.valid_between.lower,
            )
            validate_dates(
                form=self,
                field="",
                end_date=end_date,
                group_start_date=membership.geo_group.valid_between.lower,
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
                    self.add_error(
                        "end_date",
                        "The end date must span the validity period of the quota order number origin that specifies this geographical area.",
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
