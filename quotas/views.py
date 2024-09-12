import datetime
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.views.generic import FormView
from django.views.generic.list import ListView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework import permissions
from rest_framework import viewsets

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.forms import delete_form_for
from common.serializers import AutoCompleteSerializer
from common.serializers import serialize_date
from common.tariffs_api import URLs
from common.tariffs_api import get_quota_data
from common.tariffs_api import get_quota_definitions_data
from common.validators import UpdateType
from common.views import BusinessRulesMixin
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode
from measures.models import Measure
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas import serializers
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX
from quotas.filters import OrderNumberFilterBackend
from quotas.filters import QuotaFilter
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaSuspension
from quotas.serializers import deserialize_definition_data
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class QuotaOrderNumberViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows quota order numbers to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderNumberFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaOrderNumberOriginViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOrigin.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberOriginExclusionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOriginExclusion.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaDefinitionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaDefinition.objects.has_approved_state()
    serializer_class = serializers.QuotaDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number__order_number", "description"]


class QuotaAssociationViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaAssociation.objects.has_approved_state()
    serializer_class = serializers.QuotaAssociationSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaSuspensionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaSuspension.objects.has_approved_state()
    serializer_class = serializers.QuotaSuspensionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaBlockingViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaBlocking.objects.has_approved_state()
    serializer_class = serializers.QuotaBlockingSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaEventViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaEvent.objects.has_approved_state()
    serializer_class = serializers.QuotaEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberMixin:
    model = models.QuotaOrderNumber

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaCreate(QuotaOrderNumberMixin, CreateTaricCreateView):
    form_class = forms.QuotaOrderNumberCreateForm
    template_name = "layouts/create.jinja"

    permission_required = ["common.add_trackedmodel"]

    validate_business_rules = (
        business_rules.ON1,
        business_rules.ON2,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            page_title="Create a new quota order number",
            **kwargs,
        )


class QuotaConfirmCreate(QuotaOrderNumberMixin, TrackedModelDetailView):
    template_name = "quotas/confirm-create.jinja"


class QuotaList(QuotaOrderNumberMixin, TamatoListView):
    """Returns a list of QuotaOrderNumber objects."""

    template_name = "quotas/list.jinja"
    filterset_class = QuotaFilter


class QuotaDetail(QuotaOrderNumberMixin, TrackedModelDetailView, SortingMixin):
    template_name = "quotas/detail.jinja"
    sort_by_fields = ["goods_nomenclature"]

    @property
    def quota_data(self):
        data = get_quota_data({"order_number": self.object.order_number})
        if not data or data["meta"]["pagination"]["total_count"] == 0:
            return None
        return data.get("data")[0]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        definitions = self.object.definitions.current()

        current_definition = definitions.as_at_and_beyond(date.today()).first()
        context["current_definition"] = current_definition
        context["uk_tariff_url"] = (
            f"{URLs.BASE_URL.value}quota_search?order_number={self.object.order_number}"
        )

        context[
            "quota_associations"
        ] = QuotaAssociation.objects.latest_approved().filter(
            main_quota=current_definition,
        )

        context["blocking_period"] = (
            QuotaBlocking.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["suspension_period"] = (
            QuotaSuspension.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["quota_data"] = self.quota_data

        order = self.get_ordering()
        if not order:
            order = "goods_nomenclature"

        context["measures"] = (
            Measure.objects.latest_approved()
            .filter(order_number=self.object)
            .as_at(date.today())
            .order_by(order)
        )
        url_params = urlencode({"order_number": self.object.pk})
        context["measures_url"] = f"{reverse('measure-ui-list')}?{url_params}"

        return context


class QuotaDefinitionList(SortingMixin, ListView):
    template_name = "quotas/definitions.jinja"
    model = models.QuotaDefinition
    sort_by_fields = ["sid", "valid_between"]

    def get_queryset(self):
        queryset = (
            models.QuotaDefinition.objects.filter(
                order_number__sid=self.quota.sid,
            )
            .current()
            .order_by("pk")
        )

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    @property
    def blocking_periods(self):
        return QuotaBlocking.objects.filter(quota_definition__order_number=self.quota)

    @property
    def suspension_periods(self):
        return QuotaSuspension.objects.filter(quota_definition__order_number=self.quota)

    @property
    def associations(self):
        return QuotaAssociation.objects.filter(main_quota__order_number=self.quota)

    @cached_property
    def quota_data(self):
        if not self.kwargs.get("quota_type"):
            return get_quota_definitions_data(self.quota.order_number, self.object_list)
        return None

    @property
    def quota(self):
        return models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            quota=self.quota,
            quota_type=self.kwargs.get("quota_type"),
            quota_data=self.quota_data,
            blocking_periods=self.blocking_periods,
            suspension_periods=self.suspension_periods,
            associations=self.associations,
            *args,
            **kwargs,
        )


class QuotaDelete(
    QuotaOrderNumberMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.QuotaDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.ON11,)


class QuotaUpdateMixin(
    QuotaOrderNumberMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaUpdateForm
    permission_required = ["common.change_trackedmodel"]

    validate_business_rules = (
        business_rules.ON1,
        business_rules.ON2,
        business_rules.ON4,
        business_rules.ON9,
        business_rules.ON11,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        geo_area_options = (
            GeographicalArea.objects.current()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        groups_options = geo_area_options.filter(area_code=AreaCode.GROUP)
        geo_group_pks = [group.pk for group in groups_options]
        memberships = GeographicalMembership.objects.filter(
            geo_group__pk__in=geo_group_pks,
        ).prefetch_related("geo_group", "member")

        groups_with_members = {}
        for group_pk in geo_group_pks:
            members = memberships.filter(geo_group__pk=group_pk)
            groups_with_members[group_pk] = [m.member.pk for m in members]

        kwargs["geo_area_options"] = geo_area_options
        kwargs["exclusions_options"] = geo_area_options.exclude(
            area_code=AreaCode.GROUP,
        )
        kwargs["groups_with_members"] = groups_with_members
        kwargs["existing_origins"] = (
            self.object.get_current_origins().with_latest_geo_area_description()
        )
        return kwargs

    def update_origins(self, instance, form_origins):
        existing_origin_pks = {origin.pk for origin in instance.get_current_origins()}

        if form_origins:
            submitted_origin_pks = {o["pk"] for o in form_origins}
            deleted_origin_pks = existing_origin_pks.difference(submitted_origin_pks)

            for origin_pk in deleted_origin_pks:
                origin = models.QuotaOrderNumberOrigin.objects.get(
                    pk=origin_pk,
                )
                origin.new_version(
                    update_type=UpdateType.DELETE,
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                )
                # Delete the exclusions as well
                exclusions = models.QuotaOrderNumberOriginExclusion.objects.filter(
                    origin__pk=origin_pk,
                )
                for exclusion in exclusions:
                    exclusion.new_version(
                        update_type=UpdateType.DELETE,
                        workbasket=WorkBasket.current(self.request),
                        transaction=instance.transaction,
                    )

            for origin in form_origins:
                # If origin exists
                if origin.get("pk"):
                    existing_origin = models.QuotaOrderNumberOrigin.objects.get(
                        pk=origin.get("pk"),
                    )
                    updated_origin = existing_origin.new_version(
                        workbasket=WorkBasket.current(self.request),
                        transaction=instance.transaction,
                        order_number=instance,
                        valid_between=origin["valid_between"],
                        geographical_area=origin["geographical_area"],
                    )

                # It's a newly created origin
                else:
                    updated_origin = models.QuotaOrderNumberOrigin.objects.create(
                        order_number=instance,
                        valid_between=origin["valid_between"],
                        geographical_area=origin["geographical_area"],
                        update_type=UpdateType.CREATE,
                        transaction=instance.transaction,
                    )

                # whether it's edited or new we need to add/update exclusions
                self.update_exclusions(
                    instance,
                    updated_origin,
                    origin.get("exclusions"),
                )
        else:
            # even if no changes were made we must update the existing
            # origins to link to the updated order number
            existing_origins = (
                models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(
                    instance.transaction,
                ).filter(
                    order_number__sid=instance.sid,
                )
            )
            for origin in existing_origins:
                origin.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                    order_number=instance,
                )

    def update_exclusions(self, quota, updated_origin, exclusions):
        existing_exclusions = (
            models.QuotaOrderNumberOriginExclusion.objects.current().filter(
                origin__sid=updated_origin.sid,
            )
        )
        existing_exclusions_geo_area_ids = set(
            existing_exclusions.values_list("excluded_geographical_area_id", flat=True),
        )
        submitted_exclusions_geo_area_ids = {
            e["geographical_area"].id for e in exclusions
        }
        deleted_exclusion_geo_area_ids = existing_exclusions_geo_area_ids.difference(
            submitted_exclusions_geo_area_ids,
        )

        for geo_area_id in deleted_exclusion_geo_area_ids:
            exclusion = existing_exclusions.get(
                excluded_geographical_area=geo_area_id,
            )
            exclusion.new_version(
                update_type=UpdateType.DELETE,
                workbasket=WorkBasket.current(self.request),
                transaction=quota.transaction,
            )

        for exclusion in exclusions:
            geo_area = GeographicalArea.objects.get(pk=exclusion["geographical_area"])
            if geo_area.pk in existing_exclusions_geo_area_ids:
                existing_exclusion = existing_exclusions.get(
                    excluded_geographical_area=geo_area,
                )
                existing_exclusion.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=quota.transaction,
                    origin=updated_origin,
                    excluded_geographical_area=geo_area,
                )

            else:
                models.QuotaOrderNumberOriginExclusion.objects.create(
                    origin=updated_origin,
                    excluded_geographical_area=geo_area,
                    update_type=UpdateType.CREATE,
                    transaction=quota.transaction,
                )

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        # if JS is enabled we get data from the React form which includes origins and exclusions
        form_origins = form.cleaned_data.get("origins")

        self.update_origins(instance, form_origins)

        return instance


class QuotaUpdate(
    QuotaUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaEditCreate(
    QuotaUpdateMixin,
    EditTaricView,
):
    pass


class QuotaEditUpdate(
    QuotaUpdateMixin,
    EditTaricView,
):
    pass


class QuotaConfirmUpdate(QuotaOrderNumberMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class QuotaOrderNumberOriginMixin:
    model = models.QuotaOrderNumberOrigin

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(tx)


class QuotaOrderNumberOriginUpdateMixin(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaOrderNumberOriginUpdateForm
    permission_required = ["common.change_trackedmodel"]
    template_name = "quota-origins/edit.jinja"

    validate_business_rules = (
        business_rules.ON5,
        business_rules.ON6,
        business_rules.ON7,
        business_rules.ON10,
        business_rules.ON12,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)

        geo_area = form.cleaned_data["geographical_area"]
        form_exclusions = [
            item["exclusion"]
            for item in form.cleaned_data[QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX]
        ]

        all_new_exclusions = get_all_members_of_geo_groups(
            object.valid_between,
            form_exclusions,
        )

        for geo_area in all_new_exclusions:
            existing_exclusion = (
                object.quotaordernumberoriginexclusion_set.filter(
                    excluded_geographical_area=geo_area,
                )
                .current()
                .first()
            )

            if existing_exclusion:
                existing_exclusion.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=object.transaction,
                    origin=object,
                )
            else:
                models.QuotaOrderNumberOriginExclusion.objects.create(
                    origin=object,
                    excluded_geographical_area=geo_area,
                    update_type=UpdateType.CREATE,
                    transaction=object.transaction,
                )

        removed_excluded_areas = {
            e.excluded_geographical_area
            for e in object.quotaordernumberoriginexclusion_set.current()
        }.difference(set(form_exclusions))

        removed_exclusions = [
            object.quotaordernumberoriginexclusion_set.current().get(
                excluded_geographical_area__id=e.id,
            )
            for e in removed_excluded_areas
        ]

        for removed in removed_exclusions:
            removed.new_version(
                update_type=UpdateType.DELETE,
                workbasket=WorkBasket.current(self.request),
                transaction=object.transaction,
                origin=object,
            )

        return object


class QuotaOrderNumberOriginUpdate(
    QuotaOrderNumberOriginUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaOrderNumberOriginCreate(
    QuotaOrderNumberOriginUpdateMixin,
    CreateTaricCreateView,
):
    form_class = forms.QuotaOrderNumberOriginForm
    template_name = "layouts/create.jinja"

    def form_valid(self, form):
        quota = models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])
        form.instance.order_number = quota
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["page_title"] = "Create a new quota origin"
        context["page_label"] = mark_safe(
            """Find out more about <a class="govuk-link" 
        href="https://data-services-help.trade.gov.uk/tariff-application-platform/tariff-policy/origin-quotas/">
        quota origins</a>.""",
        )

        return context


class QuotaOrderNumberOriginConfirmCreate(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailView,
):
    template_name = "quota-origins/confirm-create.jinja"


class QuotaOrderNumberOriginEditUpdate(
    QuotaOrderNumberOriginUpdateMixin,
    EditTaricView,
):
    pass


class QuotaOrderNumberOriginConfirmUpdate(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailView,
):
    template_name = "quota-origins/confirm-update.jinja"


class QuotaDefinitionMixin:
    model = models.QuotaDefinition

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaDefinition.objects.approved_up_to_transaction(tx)


class QuotaDefinitionUpdateMixin(
    QuotaDefinitionMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaDefinitionUpdateForm
    permission_required = ["common.change_trackedmodel"]
    template_name = "quota-definitions/edit.jinja"

    validate_business_rules = (
        business_rules.QD7,
        business_rules.QD8,
        business_rules.QD10,
        business_rules.QD11,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)
        return object


class QuotaDefinitionUpdate(
    QuotaDefinitionUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaDefinitionCreate(QuotaDefinitionUpdateMixin, CreateTaricCreateView):
    template_name = "quota-definitions/create.jinja"
    form_class = forms.QuotaDefinitionCreateForm

    def form_valid(self, form):
        quota = models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])
        form.instance.order_number = quota
        return super().form_valid(form)


class QuotaDefinitionConfirmCreate(
    QuotaDefinitionMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-create.jinja"


class QuotaDefinitionDelete(
    QuotaDefinitionUpdateMixin,
    CreateTaricDeleteView,
):
    form_class = delete_form_for(models.QuotaDefinition)
    template_name = "quota-definitions/delete.jinja"

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Quota definition period {self.object.sid} has been deleted",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "quota_definition-ui-confirm-delete",
            kwargs={"sid": self.object.order_number.sid},
        )


class QuotaDefinitionEditUpdate(
    QuotaDefinitionUpdateMixin,
    EditTaricView,
):
    pass


class QuotaDefinitionConfirmUpdate(
    QuotaDefinitionMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-update.jinja"


class QuotaDefinitionConfirmDelete(
    QuotaOrderNumberMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-delete.jinja"


class DuplicateDefinitionsWizard(
    PermissionRequiredMixin,
    NamedUrlSessionWizardView,
):
    """
    Multipart form wizard for duplicating QuotaDefinitionPeriods from a parent
    QuotaOrderNumber to a child QuotaOrderNumber.

    https://django-formtools.readthedocs.io/en/latest/wizard.html
    """

    storage_name = "quotas.wizard.QuotaDefinitionDuplicatorSessionStorage"
    permission_required = ["common.add_trackedmodel"]

    START = "start"
    QUOTA_ORDER_NUMBERS = "quota_order_numbers"
    SELECT_DEFINITION_PERIODS = "select_definition_periods"
    SELECTED_DEFINITIONS = "selected_definition_periods"
    COMPLETE = "complete"

    form_list = [
        (START, forms.DuplicateQuotaDefinitionPeriodStartForm),
        (QUOTA_ORDER_NUMBERS, forms.QuotaOrderNumbersSelectForm),
        (SELECT_DEFINITION_PERIODS, forms.SelectSubQuotaDefinitionsForm),
        (SELECTED_DEFINITIONS, forms.SelectedDefinitionsForm),
    ]

    templates = {
        START: "quota-definitions/sub-quota-duplicate-definitions-start.jinja",
        QUOTA_ORDER_NUMBERS: "quota-definitions/sub-quota-definitions-select-order-numbers.jinja",
        SELECT_DEFINITION_PERIODS: "quota-definitions/sub-quota-definitions-select-definition-period.jinja",
        SELECTED_DEFINITIONS: "quota-definitions/sub-quota-definitions-selected.jinja",
        COMPLETE: "quota-definitions/sub-quota-definitions-done.jinja",
    }

    step_metadata = {
        START: {
            "title": "Duplicate quota definitions",
            "link_text": "Start",
        },
        QUOTA_ORDER_NUMBERS: {
            "title": "Create associations",
            "link_text": "Order numbers",
        },
        SELECT_DEFINITION_PERIODS: {
            "title": "Select definition periods",
            "link_text": "Definition periods",
        },
        SELECTED_DEFINITIONS: {
            "title": "Provide updates and details for duplicated definitions",
            "link_text": "Selected definitions",
        },
        COMPLETE: {"title": "Finished", "link_text": "Success"},
    }

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        return context

    def get_template_names(self):
        template = self.templates.get(
            self.steps.current,
            "quota-definitions/sub-quota-duplicate-definitions-step.jinja",
        )
        return template

    def get_cleaned_data_for_step(self, step):
        """
        Returns cleaned data for a given `step`.

        Note: This patched version of `super().get_cleaned_data_for_step` temporarily saves the cleaned_data
        to provide quick retrieval should another call for it be made in the same request (as happens in
        `get_form_kwargs()`) to avoid revalidating forms unnecessarily.
        """
        self.cleaned_data = getattr(self, "cleaned_data", {})
        if step in self.cleaned_data:
            return self.cleaned_data[step]

        self.cleaned_data[step] = super().get_cleaned_data_for_step(step)
        return self.cleaned_data[step]

    def format_date(self, date_str):
        """Parses and converts a date string from that used for storing data to
        the one used in the TAP UI."""
        if date_str:
            date_object = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_object.strftime("%d %b %Y")
        return ""

    def get_staged_definition_data(self):
        return self.request.session["staged_definition_data"]

    def get_main_definition(self, main_definition_pk):
        return models.QuotaDefinition.objects.get(pk=main_definition_pk)

    def get_form_kwargs(self, step):
        kwargs = {}
        if step == self.SELECT_DEFINITION_PERIODS:
            main_quota_order_number_sid = self.get_cleaned_data_for_step(
                self.QUOTA_ORDER_NUMBERS,
            )["main_quota_order_number"].sid
            main_quota_definitions = (
                models.QuotaDefinition.objects.filter(
                    order_number__sid=main_quota_order_number_sid,
                )
                .current()
                .order_by("pk")
            )
            kwargs["request"] = self.request
            kwargs["objects"] = main_quota_definitions

        elif step == self.SELECTED_DEFINITIONS:
            kwargs["request"] = self.request

        return kwargs

    def status_tag_generator(self, definition) -> dict:
        """
        Based on the status_tag_generator() for the Measure create Process
        queue.

        Returns a dict with text and a CSS class for a label for a duplicated
        definition.
        """
        if definition["status"]:
            return {
                "text": "Edited",
                "tag_class": "tamato-badge-light-green",
            }
        else:
            return {
                "text": "Unedited",
                "tag_class": "tamato-badge-light-blue",
            }

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()
        for definition in cleaned_data["staged_definitions"]:
            self.create_definition(definition)
        sub_quota_view_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": cleaned_data["main_quota_order_number"].sid},
        )
        sub_quota_view_query_string = "quota_type=sub_quotas&submit="
        context = self.get_context_data(
            form=None,
            main_quota=cleaned_data["main_quota_order_number"],
            sub_quota=cleaned_data["sub_quota_order_number"],
            definition_view_url=(f"{sub_quota_view_url}?{sub_quota_view_query_string}"),
        )
        return render(
            self.request,
            "quota-definitions/sub-quota-definitions-done.jinja",
            context,
        )

    def create_definition(self, definition):
        staged_data = deserialize_definition_data(
            self,
            definition["sub_definition_staged_data"],
        )
        instance = models.QuotaDefinition.objects.create(
            **staged_data,
            transaction=WorkBasket.get_current_transaction(self.request),
        )
        association_data = {
            "main_quota": models.QuotaDefinition.objects.get(
                pk=definition["main_definition"],
            ),
            "sub_quota": instance,
            "coefficient": Decimal(
                definition["sub_definition_staged_data"]["coefficient"],
            ),
            "sub_quota_relation_type": definition["sub_definition_staged_data"][
                "relationship_type"
            ],
            "update_type": UpdateType.CREATE,
        }
        self.create_definition_association(association_data)

    def create_definition_association(self, association_data):
        models.QuotaAssociation.objects.create(
            **association_data,
            transaction=WorkBasket.get_current_transaction(self.request),
        )


class QuotaDefinitionDuplicateUpdates(
    FormView,
    BusinessRulesMixin,
):
    """UI endpoint for any updates to duplicated definitions."""

    template_name = "quota-definitions/sub-quota-definitions-updates.jinja"
    form_class = forms.SubQuotaDefinitionsUpdatesForm
    permission_required = "common.add_trackedmodel"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pk"] = self.kwargs["pk"]
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Update definition and association details"
        context["quota_order_number"] = self.kwargs["pk"]
        return context

    def get_main_definition(self):
        return models.QuotaDefinition.objects.current().get(
            trackedmodel_ptr_id=self.kwargs["pk"],
        )

    def form_valid(self, form):
        main_definition = self.get_main_definition()
        cleaned_data = form.cleaned_data
        updated_serialized_data = {
            "initial_volume": str(cleaned_data["initial_volume"]),
            "volume": str(cleaned_data["volume"]),
            "measurement_unit_code": cleaned_data["measurement_unit"].code,
            "start_date": serialize_date(cleaned_data["valid_between"].lower),
            "end_date": serialize_date(cleaned_data["valid_between"].upper),
            "status": True,
            "coefficient": str(cleaned_data["coefficient"]),
            "relationship_type": cleaned_data["relationship_type"],
        }
        staged_definition_data = self.request.session["staged_definition_data"]
        list(
            filter(
                lambda staged_definition_data: staged_definition_data["main_definition"]
                == main_definition.pk,
                staged_definition_data,
            ),
        )[0]["sub_definition_staged_data"] = updated_serialized_data

        return redirect(reverse("sub_quota_definitions-ui-create"))


@method_decorator(require_current_workbasket, name="dispatch")
class QuotaSuspensionOrBlockingCreate(
    PermissionRequiredMixin,
    FormView,
):
    """UI endpoint for creating a suspension period or a blocking period."""

    template_name = "quota-suspensions/create.jinja"
    form_class = forms.QuotaSuspensionOrBlockingCreateForm
    permission_required = "common.add_trackedmodel"

    @property
    def quota_order_number(self):
        return models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])

    @property
    def workbasket(self):
        return WorkBasket.current(self.request)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["quota_order_number"] = self.quota_order_number
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Create a suspension or blocking period"
        context["quota_order_number"] = self.quota_order_number
        return context

    def form_valid(self, form):
        self.object = form.save(workbasket=self.workbasket)
        return super().form_valid(form)

    def get_success_url(self):
        redirect_map = {
            QuotaSuspension: reverse(
                "quota_suspension-ui-confirm-create",
                kwargs={"sid": self.object.sid},
            ),
            QuotaBlocking: reverse(
                "quota_blocking-ui-confirm-create",
                kwargs={"sid": self.object.sid},
            ),
        }
        return redirect_map.get(type(self.object))


class QuotaSuspensionConfirmCreate(TrackedModelDetailView):
    model = models.QuotaSuspension
    template_name = "quota-suspensions/confirm-create.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        quota_order_number = self.object.quota_definition.order_number
        list_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": quota_order_number.sid},
        )
        url_param = urlencode({"quota_type": "suspension_periods"})
        context.update(
            {
                "quota_order_number": quota_order_number,
                "object_name": "Suspension period",
                "list_url": f"{list_url}?{url_param}",
            },
        )
        return context


class QuotaBlockingConfirmCreate(TrackedModelDetailView):
    model = models.QuotaBlocking
    template_name = "quota-suspensions/confirm-create.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        quota_order_number = self.object.quota_definition.order_number
        list_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": quota_order_number.sid},
        )
        url_param = urlencode({"quota_type": "blocking_periods"})
        context.update(
            {
                "quota_order_number": quota_order_number,
                "object_name": "Blocking period",
                "list_url": f"{list_url}?{url_param}",
            },
        )
        return context


class SubQuotaDefinitionAssociationMixin:
    template_name = "quota-definitions/sub-quota-definitions-updates.jinja"
    form_class = forms.SubQuotaDefinitionUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["sid"] = self.kwargs["sid"]
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        return reverse(
            "sub_quota_definition-confirm-update",
            kwargs={"sid": self.kwargs["sid"]},
        )

    @property
    def sub_quota(self):
        return (
            models.QuotaDefinition.objects.all()
            .latest_approved()
            .get(
                sid=self.kwargs["sid"],
            )
        )

    @property
    def association(self):
        "Get the main definition from the sub quota sid passed in"
        # Getting main quota from the sub quota - assuming that a subquota can't be a subquota of multiple different main quotas
        return (
            models.QuotaAssociation.objects.all()
            .filter(sub_quota_id=self.sub_quota)
            .last()
        )

    def get_main_definition(self):
        return self.association.main_quota


class SubQuotaDefinitionAssociationEditCreate(
    SubQuotaDefinitionAssociationMixin,
    QuotaDefinitionUpdate,
):

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        sub_quota_relation_type = form.cleaned_data.get("relationship_type")
        coefficient = form.cleaned_data.get("coefficient")

        self.update_association(instance, sub_quota_relation_type, coefficient)

        return instance

    def update_association(self, instance, sub_quota_relation_type, coefficient):
        "Update the association too if there is updated data submitted."  # Is this actually needed? Not sure any other object would prevent an identical update occuring
        if (
            self.association.sub_quota_relation_type == sub_quota_relation_type
            and self.association.coefficient == coefficient
        ):
            return
        form_data = {
            "main_quota": self.get_main_definition(),
            "sub_quota": self.sub_quota,
            "coefficient": coefficient,
            "sub_quota_relation_type": sub_quota_relation_type,
        }

        form = forms.QuotaAssociationEdit(data=form_data, instance=self.association)

        form.instance.new_version(
            workbasket=WorkBasket.current(self.request),
            transaction=instance.transaction,
            sub_quota=instance,
            main_quota=self.get_main_definition(),
            coefficient=coefficient,
            sub_quota_relation_type=sub_quota_relation_type,
        )


class SubQuotaDefinitionAssociationEditUpdate(
    SubQuotaDefinitionAssociationMixin,
    QuotaDefinitionEditUpdate,
):

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        sub_quota_relation_type = form.cleaned_data.get("relationship_type")
        coefficient = form.cleaned_data.get("coefficient")

        self.update_association(instance, sub_quota_relation_type, coefficient)

        return instance

    def update_association(self, instance, sub_quota_relation_type, coefficient):
        "Update the association too if there is updated data submitted."
        if (
            self.association.sub_quota_relation_type == sub_quota_relation_type
            and self.association.coefficient == coefficient
        ):
            return
        # If this association already has an edit in the workbasket - update that one
        current_instance = self.association.latest_version_up_to_workbasket(
            self.workbasket,
        )

        form_data = {
            "main_quota": self.get_main_definition(),
            "sub_quota": instance,
            "coefficient": coefficient,
            "sub_quota_relation_type": sub_quota_relation_type,
        }

        form = forms.QuotaAssociationEdit(data=form_data, instance=current_instance)
        form.save()


class SubQuotaConfirmUpdate(TrackedModelDetailView):
    model = models.QuotaDefinition
    template_name = "quota-definitions/sub-quota-definitions-confirm-update.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        association = (
            QuotaAssociation.objects.all()
            .latest_approved()
            .get(sub_quota__sid=self.object.sid)
        )
        context["association"] = association
        return context
