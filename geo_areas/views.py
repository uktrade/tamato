from typing import Type

from django.shortcuts import redirect
from django.urls import reverse
from rest_framework import permissions
from rest_framework import viewsets

from common.models.trackedmodel import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.util import TaricDateRange
from common.validators import UpdateType
from common.views import DescriptionDeleteMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas import business_rules
from geo_areas import forms
from geo_areas.filters import GeographicalAreaFilter
from geo_areas.forms import GeographicalAreaCreateDescriptionForm
from geo_areas.forms import GeographicalAreaEditForm
from geo_areas.forms import GeoMembershipAction
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class GeoAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows geographical areas to be viewed."""

    queryset = (
        GeographicalArea.objects.latest_approved()
        .with_latest_description()
        .prefetch_related(
            "descriptions",
        )
    )

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "area_code"]


class GeoAreaMixin:
    model: Type[TrackedModel] = GeographicalArea

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return GeographicalArea.objects.approved_up_to_transaction(tx)


class GeoAreaDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return GeographicalAreaDescription.objects.approved_up_to_transaction(tx)


class GeoAreaCreateDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = GeographicalArea.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return context


class GeoAreaList(
    GeoAreaMixin,
    TamatoListView,
):
    template_name = "geo_areas/list.jinja"
    filterset_class = GeographicalAreaFilter
    filterset_class.search_fields = ["area_id", "description"]

    def get_queryset(self):
        return GeographicalArea.objects.current().with_current_descriptions()


class GeoAreaDetail(
    GeoAreaMixin,
    TrackedModelDetailView,
):
    template_name = "geo_areas/detail.jinja"


class GeoAreaDelete(
    GeoAreaMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.GeographicalAreaDeleteForm
    success_path = "list"

    validate_business_rules = (
        business_rules.GA21,
        business_rules.GA22,
    )


class GeoAreaDescriptionCreate(
    GeoAreaCreateDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricCreateView,
):
    def get_initial(self):
        initial = super().get_initial()
        initial["described_geographicalarea"] = GeographicalArea.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return initial

    form_class = GeographicalAreaCreateDescriptionForm
    template_name = "common/create_description_no_description_help.jinja"


class GeoAreaDescriptionConfirmCreate(
    GeoAreaDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class GeoAreaDescriptionDelete(
    GeoAreaDescriptionMixin,
    DescriptionDeleteMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.GeographicalAreaDescriptionDeleteForm
    success_path = "detail"


class GeoAreaUpdateMixin(GeoAreaMixin, TrackedModelDetailMixin):
    form_class = GeographicalAreaEditForm

    validate_business_rules = (
        business_rules.GA5,
        business_rules.GA6,
        business_rules.GA7,
        business_rules.GA10,
        business_rules.GA11,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def create_membership(self, form):
        if form.cleaned_data["geo_group"]:
            geo_group = form.cleaned_data["geo_group"]
            member = form.instance
        elif form.cleaned_data["member"]:
            geo_group = form.instance
            member = form.cleaned_data["member"]
        else:
            return

        tx = WorkBasket.get_current_transaction(self.request)
        valid_between = form.cleaned_data["new_membership_valid_between"]
        membership = GeographicalMembership(
            geo_group=geo_group,
            member=member,
            valid_between=valid_between,
            transaction=tx,
            update_type=UpdateType.CREATE,
        )
        membership.save()

    def edit_membership(self, form):
        if (
            form.cleaned_data["membership"]
            and form.cleaned_data["action"] == GeoMembershipAction.DELETE
        ):
            membership = form.cleaned_data["membership"]
            membership.new_version(
                workbasket=self.workbasket,
                update_type=UpdateType.DELETE,
            )

        elif (
            form.cleaned_data["membership"]
            and form.cleaned_data["action"] == GeoMembershipAction.END_DATE
        ):
            membership = form.cleaned_data["membership"]
            end_date = form.cleaned_data["membership_end_date"]
            valid_between = TaricDateRange(membership.valid_between.lower, end_date)

            membership.new_version(
                workbasket=self.workbasket,
                valid_between=valid_between,
                update_type=UpdateType.UPDATE,
            )

        else:
            return

    def get_result_object(self, form):
        geo_area = super().get_result_object(form)
        form.instance = geo_area
        self.create_membership(form)
        self.edit_membership(form)
        return geo_area


class GeoAreaUpdate(GeoAreaUpdateMixin, CreateTaricUpdateView):
    """UI endpoint to create geo area UPDATE instances."""


class GeoAreaConfirmUpdate(GeoAreaMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class GeoAreaEditUpdate(
    GeoAreaUpdateMixin,
    EditTaricView,
):
    """UI endpoint to edit geo area UPDATE instances."""


class GeoAreaCreate(GeoAreaMixin, CreateTaricCreateView):
    """UI endpoint for creating Geographical Area CREATE instances."""

    template_name = "geo_areas/create.jinja"
    form_class = forms.GeographicalAreaCreateForm

    validate_business_rules = (
        business_rules.GA1,
        business_rules.GA7,
    )

    def get_result_object(self, form):
        geo_area = super().get_result_object(form)
        description = form.cleaned_data["geographical_area_description"]
        description.described_geographicalarea = geo_area
        description.update_type = UpdateType.CREATE
        description.transaction = geo_area.transaction
        description.save()

        return geo_area


class GeoAreaEditCreate(
    GeoAreaMixin,
    TrackedModelDetailMixin,
    EditTaricView,
):
    """UI endpoint for editing Geographical Area CREATE instances."""

    template_name = "layouts/create.jinja"
    form_class = forms.GeographicalAreaEditCreateForm

    validate_business_rules = (
        business_rules.GA1,
        business_rules.GA3,
        business_rules.GA7,
    )


class GeoAreaConfirmCreate(
    GeoAreaMixin,
    TrackedModelDetailView,
):
    template_name = "geo_areas/confirm-create.jinja"


class GeographicalMembershipsCreate(
    TrackedModelDetailMixin,
    CreateTaricCreateView,
):
    template_name = "geo_areas/create-membership-formset.jinja"

    @property
    def instance(self):
        return GeographicalArea.objects.current().get(sid=self.kwargs.get("sid"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        geo_area = self.instance
        context.update({"geo_area": geo_area})
        return context

    def get_form(self):
        if self.instance.is_group():
            return super().get_form(forms.GeographicalMembershipMemberFormSet)
        else:
            return super().get_form(forms.GeographicalMembershipGroupFormSet)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["form_kwargs"] = {"geo_area": self.instance}
        return kwargs

    def create_memberships(self, form):
        geo_area = self.instance

        validity_periods = [
            d["valid_between"] for d in form.cleaned_data if "valid_between" in d
        ]
        members = [d["member"] for d in form.cleaned_data if "member" in d]
        geo_groups = [d["geo_group"] for d in form.cleaned_data if "geo_group" in d]

        tx = WorkBasket.get_current_transaction(self.request)

        if members:
            for member, valid_between in zip(members, validity_periods):
                membership = GeographicalMembership(
                    geo_group=geo_area,
                    member=member,
                    valid_between=valid_between,
                    transaction=tx,
                    update_type=UpdateType.CREATE,
                )
                membership.save()

        if geo_groups:
            for geo_group, valid_between in zip(geo_groups, validity_periods):
                membership = GeographicalMembership(
                    geo_group=geo_group,
                    member=geo_area,
                    valid_between=valid_between,
                    transaction=tx,
                    update_type=UpdateType.CREATE,
                )
                membership.save()

        return geo_area

    def form_valid(self, form):
        self.create_memberships(form)
        return redirect(
            reverse(
                "geo_area-ui-membership-confirm-create",
                kwargs={"sid": self.instance.sid},
            ),
        )


class GeographicalMembershipConfirmCreate(
    GeoAreaMixin,
    TrackedModelDetailView,
):
    template_name = "geo_areas/confirm-create-membership.jinja"
